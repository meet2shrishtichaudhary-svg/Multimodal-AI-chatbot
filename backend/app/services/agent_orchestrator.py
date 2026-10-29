import re
import time
import asyncio
import logging
from typing import List, Dict, Any, Optional, AsyncGenerator

from sqlalchemy.orm import Session
from app.schemas.chat import SourceCitation
from app.services.rag_service import retrieve_relevant_chunks, build_rag_context_and_citations
from app.services.web_search_service import get_search_service
from app.services.image_service import detect_image_prompt, generate_or_fetch_image

logger = logging.getLogger("mm_chatbot.agent")

# Supported validated tool identifiers
TOOL_RAG = "document_rag"
TOOL_WEB_SEARCH = "web_search"
TOOL_IMAGE_GEN = "image_generation"
TOOL_CALCULATOR = "calculator"

class ToolExecutionResult:
    def __init__(self, tool_name: str, success: bool, output: Any, error: Optional[str] = None, duration_ms: float = 0.0):
        self.tool_name = tool_name
        self.success = success
        self.output = output
        self.error = error
        self.duration_ms = duration_ms

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool": self.tool_name,
            "success": self.success,
            "duration_ms": round(self.duration_ms, 1),
            "error": self.error
        }

def classify_intents(prompt: str, has_kdocs: bool, has_attachments: bool, force_search: bool = False) -> List[str]:
    """
    Analyzes prompt semantics to orchestrate required tools.
    """
    intents = []
    lowered = prompt.lower().strip()

    # 1. Image Generation Intent
    if detect_image_prompt(prompt):
        intents.append(TOOL_IMAGE_GEN)

    # 2. Document RAG Intent (prioritized when documents exist or user asks about documents/files)
    doc_keywords = ["document", "file", "pdf", "docx", "report", "contract", "upload", "uploaded", "according to", "summary", "page", "section", "clause"]
    if has_attachments or (has_kdocs and any(k in lowered for k in doc_keywords)):
        intents.append(TOOL_RAG)

    # 3. Web Search Intent
    search_keywords = ["latest", "recent", "today", "news", "current", "weather", "stock", "price", "who won", "2026", "2025", "live", "search"]
    if force_search or any(k in lowered for k in search_keywords):
        if TOOL_WEB_SEARCH not in intents:
            intents.append(TOOL_WEB_SEARCH)

    # 4. Math / Calculation Intent
    math_patterns = [r"^\s*[\d\s+\-*/^().]+=\s*$", r"calculate\s+[\d\s+\-*/^().]+", r"what\s+is\s+[\d\s+\-*/^().]+\?"]
    if any(re.search(p, lowered) for p in math_patterns):
        intents.append(TOOL_CALCULATOR)

    return intents

async def execute_tool_with_timeout(tool_coroutine, tool_name: str, timeout_seconds: float = 8.0) -> ToolExecutionResult:
    """
    Executes a tool with strict execution timeouts and error boundaries.
    """
    start = time.perf_counter()
    try:
        output = await asyncio.wait_for(tool_coroutine, timeout=timeout_seconds)
        duration = (time.perf_counter() - start) * 1000
        return ToolExecutionResult(tool_name=tool_name, success=True, output=output, duration_ms=duration)
    except asyncio.TimeoutError:
        duration = (time.perf_counter() - start) * 1000
        logger.warning(f"Tool {tool_name} timed out after {timeout_seconds}s")
        return ToolExecutionResult(tool_name=tool_name, success=False, output=None, error=f"Tool timed out after {timeout_seconds}s", duration_ms=duration)
    except Exception as exc:
        duration = (time.perf_counter() - start) * 1000
        logger.error(f"Tool {tool_name} execution error: {exc}")
        return ToolExecutionResult(tool_name=tool_name, success=False, output=None, error=str(exc), duration_ms=duration)

async def orchestrate_agent_tools(
    prompt: str,
    auth_ctx: Dict[str, Any],
    db: Session,
    enable_web_search: bool = False,
    conversation_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Central orchestration coordinator: executes necessary tools concurrently,
    aggregates citations, and constructs combined grounding context.
    """
    session_id = auth_ctx["session_id"]
    from app.db.models import KnowledgeDocument
    has_kdocs = db.query(KnowledgeDocument.id).filter(KnowledgeDocument.session_id == session_id).first() is not None

    intents = classify_intents(prompt, has_kdocs=has_kdocs, has_attachments=False, force_search=enable_web_search)
    logger.info(f"Agent Orchestrator classified intents for query: {intents}")

    tool_results = []
    rag_context = ""
    search_context = ""
    generated_image_info = None
    citations: List[SourceCitation] = []

    # Execute tools
    for tool_name in intents:
        if tool_name == TOOL_IMAGE_GEN:
            img_prompt = detect_image_prompt(prompt)
            if img_prompt:
                res = await execute_tool_with_timeout(
                    generate_or_fetch_image(prompt=img_prompt, session_id=session_id, conv_id=conversation_id, db=db),
                    tool_name=TOOL_IMAGE_GEN,
                    timeout_seconds=12.0
                )
                tool_results.append(res.to_dict())
                if res.success:
                    generated_image_info = res.output

        elif tool_name == TOOL_WEB_SEARCH:
            search_service = get_search_service()
            res = await execute_tool_with_timeout(
                search_service.search(query=prompt, max_results=4),
                tool_name=TOOL_WEB_SEARCH,
                timeout_seconds=8.0
            )
            tool_results.append(res.to_dict())
            if res.success and res.output:
                search_lines = ["--- BEGIN WEB RESEARCH GROUNDING ---"]
                for i, r in enumerate(res.output):
                    search_lines.append(f"[{i+1}] {r.title}\nURL: {r.url}\nSummary: {r.snippet}\n")
                    citations.append(SourceCitation(
                        title=r.title,
                        url=r.url,
                        snippet=r.snippet,
                        source_type="web"
                    ))
                search_lines.append("--- END WEB RESEARCH GROUNDING ---")
                search_context = "\n".join(search_lines)

        elif tool_name == TOOL_RAG:
            res = await execute_tool_with_timeout(
                retrieve_relevant_chunks(db=db, session_id=session_id, query=prompt, top_k=4),
                tool_name=TOOL_RAG,
                timeout_seconds=6.0
            )
            tool_results.append(res.to_dict())
            if res.success and res.output:
                context_str, doc_citations = build_rag_context_and_citations(res.output)
                rag_context = context_str
                citations.extend(doc_citations)

    return {
        "intents": intents,
        "tool_results": tool_results,
        "rag_context": rag_context,
        "search_context": search_context,
        "generated_image_info": generated_image_info,
        "citations": citations
    }
