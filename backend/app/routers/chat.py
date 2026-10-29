import os
import json
import logging
from datetime import datetime
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.db.session import get_db, SessionLocal
from app.db.models import Conversation, Message, Attachment
from app.schemas.chat import ChatRequest, ChatResponse, MessageDTO, SourceCitation
from app.core.security import get_auth_context
from app.services.llm_service import get_llm_provider
from app.services.rag_service import retrieve_relevant_chunks, build_rag_context_and_citations
from app.services.web_search_service import get_search_service
from app.services.safety_service import process_safety_and_prompts
from app.utils.file_parsers import extract_text_from_file
from app.services.image_service import detect_image_prompt, generate_or_fetch_image
from app.services.memory_service import auto_extract_memories, store_memory, retrieve_user_memories, format_memory_context

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat"])

async def _prepare_chat_context(req: ChatRequest, auth_ctx: Dict[str, Any], db: Session) -> Dict[str, Any]:
    session_id = auth_ctx["session_id"]
    user = auth_ctx.get("user")
    user_id = auth_ctx.get("user_id")

    # 1. Resolve or create conversation
    if req.conversation_id:
        conv = db.query(Conversation).filter(Conversation.id == req.conversation_id).first()
        if not conv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found or access denied."
            )
        # Check permissions
        if user_id:
            if conv.user_id and conv.user_id != user_id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this conversation.")
            if not conv.user_id:
                conv.user_id = user_id
                db.commit()
        else:
            if conv.user_id is not None or conv.session_id != session_id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this conversation.")
    else:
        # Generate short title candidate
        title_candidate = " ".join(req.message.strip().split()[:6])
        if len(title_candidate) > 40:
            title_candidate = title_candidate[:40] + "..."
        conv = Conversation(
            session_id=session_id,
            user_id=user_id,
            title=title_candidate or "New Conversation"
        )
        db.add(conv)
        db.commit()
        db.refresh(conv)

    # 2. Link attachments and load images for vision
    images_payload: List[Dict[str, Any]] = []
    attached_records: List[Attachment] = []
    if req.attachment_ids:
        attached_records = (
            db.query(Attachment)
            .filter(Attachment.id.in_(req.attachment_ids))
            .all()
        )
        for att in attached_records:
            att.conversation_id = conv.id
            if att.attachment_type == "image" and os.path.exists(att.file_path):
                try:
                    with open(att.file_path, "rb") as f:
                        img_data = f.read()
                    images_payload.append({
                        "mime_type": att.mime_type,
                        "data": img_data
                    })
                except Exception as e:
                    logger.warning(f"Could not read image file {att.file_path}: {e}")

    # 3. Save User Message
    user_msg = Message(
        conversation_id=conv.id,
        role="user",
        content=req.message,
        msg_metadata={"attachment_count": len(attached_records)}
    )
    db.add(user_msg)
    db.commit()
    db.refresh(user_msg)

    # Associate attachments to message
    for att in attached_records:
        att.message_id = user_msg.id
    db.commit()

    # 4. Extract Text from Attached Documents (.pdf, .docx, .txt, .md)
    extracted_docs: List[Dict[str, Any]] = []
    candidate_attachments = list(attached_records)
    if conv.id:
        existing_conv_docs = (
            db.query(Attachment)
            .filter(
                Attachment.conversation_id == conv.id,
                Attachment.attachment_type == "document"
            )
            .all()
        )
        seen_ids = {a.id for a in candidate_attachments}
        for ed in existing_conv_docs:
            if ed.id not in seen_ids:
                candidate_attachments.append(ed)

    for att in candidate_attachments:
        if att.attachment_type == "document" and os.path.exists(att.file_path):
            try:
                full_text, sections = extract_text_from_file(att.file_path)
                if full_text and full_text.strip():
                    truncated_text = full_text[:45000]
                    if len(full_text) > 45000:
                        truncated_text += f"\n... [Document truncated for length; showing first 45,000 of {len(full_text)} characters]"
                    extracted_docs.append({
                        "file_name": att.file_name,
                        "content": truncated_text,
                        "pages": len(sections),
                        "total_chars": len(full_text)
                    })
            except Exception as e:
                logger.warning(f"Could not parse document attachment {att.file_path}: {e}")

    docs_context = ""
    if extracted_docs:
        doc_lines = [
            "=== ATTACHED DOCUMENTS IN THIS CONVERSATION ===",
            f"The user has uploaded {len(extracted_docs)} document(s) directly to this conversation.",
            "You have COMPLETE and FULL DIRECT ACCESS to their extracted text below.",
            "CRITICAL INSTRUCTIONS FOR ATTACHED DOCUMENTS:",
            "1. Read, analyze, summarize, extract data, and answer all questions using the document text below.",
            "2. NEVER state or claim that you cannot read, view, or access uploaded files or PDFs. You have the full text right here.",
            "3. Ground your responses accurately in the document content, quoting or referencing specific sections when appropriate.",
            ""
        ]
        for d in extracted_docs:
            doc_lines.append(f"--- START DOCUMENT: {d['file_name']} ({d['pages']} pages/sections, {d['total_chars']} chars) ---")
            doc_lines.append(d["content"])
            doc_lines.append(f"--- END DOCUMENT: {d['file_name']} ---\n")
        doc_lines.append("=== END ATTACHED DOCUMENTS ===")
        docs_context = "\n".join(doc_lines)

    # 5. Check for Image Generation Request
    image_prompt = detect_image_prompt(req.message)
    generated_image_info = None
    if image_prompt:
        try:
            generated_image_info = await generate_or_fetch_image(
                prompt=image_prompt,
                session_id=session_id,
                conv_id=conv.id,
                db=db
            )
        except Exception as e:
            logger.warning(f"Image generation execution encountered error: {e}")

    # 6. Context Grounding: RAG and Web Search
    all_citations: List[SourceCitation] = []
    rag_context = ""
    rag_used = False
    search_performed = False

    # Check for RAG matches from indexed documents
    try:
        rag_matches = await retrieve_relevant_chunks(db=db, session_id=session_id, query=req.message)
        if rag_matches:
            rag_context, rag_citations = build_rag_context_and_citations(rag_matches)
            all_citations.extend(rag_citations)
            rag_used = True
    except Exception as e:
        logger.warning(f"RAG retrieval encountered an error: {e}")

    # Check if web search should be performed
    search_context = ""
    if req.enable_web_search:
        search_service = get_search_service()
        try:
            search_results = await search_service.search(req.message, max_results=4)
            if search_results:
                search_lines = ["--- BEGIN RECENT WEB SEARCH FINDINGS ---"]
                for item in search_results:
                    search_lines.append(f"Title: {item.title}\nURL: {item.url}\nSummary: {item.snippet}\n")
                    all_citations.append(SourceCitation(
                        title=item.title,
                        url=item.url,
                        snippet=item.snippet,
                        source_type="web"
                    ))
                search_lines.append(
                    "--- END RECENT WEB SEARCH FINDINGS ---\n"
                    "Instructions for Web Sources:\n"
                    "1. Synthesize the findings accurately.\n"
                    "2. Cite your sources with markdown links [Title](URL) where applicable.\n"
                    "3. Clearly distinguish sourced facts from your own explanations."
                )
                search_context = "\n".join(search_lines)
                search_performed = True
        except Exception as e:
            logger.warning(f"Web search execution encountered error: {e}")

    # 7. Safety & System Prompt Processing
    base_system = ""
    if docs_context:
        base_system += f"\n\n{docs_context}"
    elif rag_context:
        base_system += f"\n\n{rag_context}"
    else:
        # Prevent hallucinated claims about platform file-upload capabilities
        base_system += (
            "\n\nNOTE REGARDING UPLOADED FILES & DOCUMENTS:\n"
            "If the user asks you to read, analyze, summarize, or inspect a PDF, document, or file, "
            "but no document text is provided above:\n"
            "1. NEVER claim that the platform or chat window does not support direct PDF or file uploads. "
            "Aura AI has full, native support for reading and analyzing PDF, DOCX, and TXT files!\n"
            "2. Clarify that no file is currently attached to this message.\n"
            "3. Helpfully guide the user to attach their document by clicking the paperclip icon (📎) at the bottom of the chat box "
            "or dragging and dropping the file into the message area.\n"
            "4. Assure them that as soon as the file is attached, you will immediately read, extract, and analyze the full content for them."
        )
    if search_context:
        base_system += f"\n\n{search_context}"
    if generated_image_info:
        base_system += (
            f"\n\nNOTE: An AI visual has already been generated for the user's prompt: '{generated_image_info['prompt']}'. "
            f"The image URL is already being presented to the user. Provide a brief, creative, positive description or caption "
            f"for the generated visual and ask if the user wants any variations, different styles, or modifications."
        )

    # Inject personal profile custom instructions if defined
    if user and user.custom_instructions:
        base_system += f"\n\n--- USER PERSONAL PREFERENCES & CUSTOM INSTRUCTIONS ---\n{user.custom_instructions}\n--- END USER PREFERENCES ---"

    # Smart Long-Term Memory Extraction & Injection
    try:
        new_facts = auto_extract_memories(req.message)
        for fact_text, cat in new_facts:
            store_memory(db, auth_ctx, fact_text, cat)
        user_memories = retrieve_user_memories(db, auth_ctx, active_only=True)
        memory_ctx_str = format_memory_context(user_memories)
        if memory_ctx_str:
            base_system += f"\n\n{memory_ctx_str}"
    except Exception as e:
        logger.warning(f"Error handling smart memory in chat: {e}")

    persona_to_use = getattr(req, "persona", "general") or "general"
    if persona_to_use == "general" and user and user.preferred_persona:
        persona_to_use = user.preferred_persona

    system_prompt, is_crisis, crisis_banner = process_safety_and_prompts(
        user_prompt=req.message,
        base_system_prompt=base_system,
        persona=persona_to_use
    )

    # Place document grounding at the top priority of system prompt
    if docs_context:
        system_prompt = f"{docs_context}\n\n{system_prompt}"

    # 8. Retrieve conversation history for context window
    previous_messages = (
        db.query(Message)
        .filter(Message.conversation_id == conv.id)
        .order_by(Message.created_at.asc())
        .limit(15)
        .all()
    )

    formatted_history = [
        {"role": m.role, "content": m.content}
        for m in previous_messages
    ]

    # Explicitly badge the active user message with attached document names
    if extracted_docs and formatted_history:
        for i in range(len(formatted_history) - 1, -1, -1):
            if formatted_history[i]["role"] == "user":
                doc_names = ", ".join(d["file_name"] for d in extracted_docs)
                orig = formatted_history[i]["content"]
                if not orig.startswith("[Attached Document"):
                    formatted_history[i]["content"] = f"[Attached Document(s): {doc_names}]\n{orig}"
                break

    return {
        "conv": conv,
        "user_msg": user_msg,
        "images_payload": images_payload,
        "all_citations": all_citations,
        "system_prompt": system_prompt,
        "formatted_history": formatted_history,
        "is_crisis": is_crisis,
        "crisis_banner": crisis_banner,
        "search_performed": search_performed,
        "rag_used": rag_used,
        "generated_image_info": generated_image_info,
        "has_documents": len(extracted_docs) > 0
    }

@router.post("", response_model=ChatResponse)
async def send_chat_message(
    req: ChatRequest,
    auth_ctx: Dict[str, Any] = Depends(get_auth_context),
    db: Session = Depends(get_db)
):
    """
    Standard synchronous multimodal conversational endpoint.
    Orchestrates conversation history, vision inputs, RAG document grounding,
    web search citations, emotional support persona, and crisis safeguards.
    """
    ctx = await _prepare_chat_context(req, auth_ctx, db)
    conv = ctx["conv"]
    user_msg = ctx["user_msg"]

    # Generate Response from LLM
    llm = get_llm_provider()
    try:
        assistant_text = await llm.generate_response(
            messages=ctx["formatted_history"],
            system_prompt=ctx["system_prompt"],
            images=ctx["images_payload"] if ctx["images_payload"] else None
        )
    except Exception as e:
        logger.error(f"Error calling LLM provider: {e}")
        assistant_text = (
            "I apologize, but I encountered an issue generating a response with the configured AI service. "
            "Please check your API key configuration or try again in a moment."
        )

    # Append crisis resources if trigger occurred
    if ctx["is_crisis"] and ctx["crisis_banner"]:
        assistant_text = f"{assistant_text}\n\n{ctx['crisis_banner']}"

    # If image was generated, prepend image tag to response
    if ctx.get("generated_image_info"):
        gen_info = ctx["generated_image_info"]
        img_tag = f"![{gen_info['prompt']}]({gen_info['full_url']})"
        if img_tag not in assistant_text:
            assistant_text = f"Here is your generated visual for **{gen_info['prompt']}**:\n\n{img_tag}\n\n{assistant_text}"

    # Save Assistant Message
    assistant_msg = Message(
        conversation_id=conv.id,
        role="assistant",
        content=assistant_text,
        msg_metadata={
            "search_performed": ctx["search_performed"],
            "rag_used": ctx["rag_used"],
            "citation_count": len(ctx["all_citations"]),
            "is_crisis": ctx["is_crisis"],
            "generated_image": ctx.get("generated_image_info")
        }
    )
    db.add(assistant_msg)
    conv.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(assistant_msg)

    return ChatResponse(
        conversation_id=conv.id,
        user_message=MessageDTO.model_validate(user_msg),
        assistant_message=MessageDTO.model_validate(assistant_msg),
        citations=ctx["all_citations"],
        search_performed=ctx["search_performed"],
        rag_used=ctx["rag_used"]
    )

@router.post("/stream")
async def stream_chat_message(
    req: ChatRequest,
    auth_ctx: Dict[str, Any] = Depends(get_auth_context),
    db: Session = Depends(get_db)
):
    """
    Real-time streaming conversational endpoint (Server-Sent Events).
    Yields JSON packets for tokens, citations, and conversation metadata as generated.
    """
    ctx = await _prepare_chat_context(req, auth_ctx, db)
    conv_id = ctx["conv"].id

    async def event_generator():
        # 1. Emit metadata event
        meta_event = {
            "type": "metadata",
            "conversation_id": conv_id,
            "user_message_id": ctx["user_msg"].id,
            "citations": [c.model_dump() for c in ctx["all_citations"]],
            "search_performed": ctx["search_performed"],
            "rag_used": ctx["rag_used"],
            "is_crisis": ctx["is_crisis"],
            "generated_image": ctx.get("generated_image_info")
        }
        yield f"data: {json.dumps(meta_event)}\n\n"

        full_assistant_text = ""

        # 2. If an AI visual was generated, stream the visual markdown chunk first
        if ctx.get("generated_image_info"):
            gen_info = ctx["generated_image_info"]
            img_chunk = f"Here is your generated visual for **{gen_info['prompt']}**:\n\n![{gen_info['prompt']}]({gen_info['full_url']})\n\n"
            full_assistant_text += img_chunk
            yield f"data: {json.dumps({'type': 'token', 'delta': img_chunk})}\n\n"

        # 3. If crisis banner triggered, stream it next
        if ctx["is_crisis"] and ctx["crisis_banner"]:
            banner_chunk = f"{ctx['crisis_banner']}\n\n"
            full_assistant_text += banner_chunk
            yield f"data: {json.dumps({'type': 'token', 'delta': banner_chunk})}\n\n"

        # 3. Stream from LLM provider
        llm = get_llm_provider()
        try:
            async for token_chunk in llm.stream_response(
                messages=ctx["formatted_history"],
                system_prompt=ctx["system_prompt"],
                images=ctx["images_payload"] if ctx["images_payload"] else None
            ):
                if token_chunk:
                    full_assistant_text += token_chunk
                    yield f"data: {json.dumps({'type': 'token', 'delta': token_chunk})}\n\n"
        except Exception as e:
            logger.error(f"Error streaming response from LLM: {e}")
            err_text = "\n\n*(An error occurred while generating the remaining response)*"
            full_assistant_text += err_text
            yield f"data: {json.dumps({'type': 'token', 'delta': err_text})}\n\n"

        # 4. Save completed message to DB
        conv = ctx["conv"]
        assistant_msg = Message(
            conversation_id=conv_id,
            role="assistant",
            content=full_assistant_text,
            msg_metadata={
                "search_performed": ctx["search_performed"],
                "rag_used": ctx["rag_used"],
                "citation_count": len(ctx["all_citations"]),
                "is_crisis": ctx["is_crisis"],
                "generated_image": ctx.get("generated_image_info")
            }
        )
        db.add(assistant_msg)
        conv.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(assistant_msg)
        final_asst_id = assistant_msg.id

        # 5. Emit done event
        done_event = {
            "type": "done",
            "assistant_message_id": final_asst_id,
            "conversation_id": conv_id
        }
        yield f"data: {json.dumps(done_event)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
