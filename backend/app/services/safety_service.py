import re
from typing import Tuple

CRISIS_PATTERNS = [
    r"\bsuicid",
    r"\bkill myself\b",
    r"\bend my life\b",
    r"\bwant to die\b",
    r"\bharm myself\b",
    r"\bself-harm\b",
    r"\bcut myself\b",
    r"\bno reason to live\b",
    r"\bbetter off dead\b",
    r"\boverdose\b",
    r"\bcan't live like this\b",
    r"\bdon't want to wake up\b"
]

TECHNICAL_NEGATORS = [
    r"kill\s+(?:-\d+|process|task|pid|port|container|job|server|daemon|thread|session)",
    r"terminate\s+(?:process|task|connection|loop|query|session)",
    r"cut\s+(?:video|audio|string|text|clip|css|image|substring|code)",
    r"die\(\)",
    r"exit\(\)",
    r"abort\(\)",
    r"kill\s+all\b"
]

CRISIS_RESOURCES = """
> [!IMPORTANT]
> ### 💛 You Are Not Alone. Immediate, Confidential Support Is Available 24/7.
> If you are experiencing overwhelming emotional pain or distress, please know that caring and confidential human support is available right now:
>
> - **India**:
>   - **KIRAN Mental Health Helpline**: **1800-599-0019** (Toll-free, 24/7, Government of India)
>   - **Vandrevala Foundation**: **+91 9999 666 555** (Free, confidential 24/7 crisis support)
>   - **AASRA Suicide Prevention**: **+91 98204 66726** (24/7 Helpline)
> - **United States & Canada**:
>   - **988 Suicide & Crisis Lifeline**: Call or text **988** (Free, confidential, available 24/7)
>   - **Crisis Text Line**: Text **HOME** to **741741**
> - **United Kingdom**:
>   - **NHS Mental Health**: Call **111**
>   - **Samaritans**: Call **116 123** (Free 24/7) or Text **85258**
> - **International**:
>   - Find free confidential crisis hotlines worldwide at [findahelpline.com](https://findahelpline.com/) or [befrienders.org](https://www.befrienders.org/)
>
> *I am an AI assistant, not a doctor or mental health professional. Please reach out to one of the helplines above or a trusted person in your life.*
"""

EMPATHETIC_SYSTEM_PROMPT = """
You are a thoughtful, compassionate, and supportive AI assistant.
Your conversational guidelines:
1. Always acknowledge and validate the user's feelings first before offering perspectives or gentle suggestions.
2. Maintain a warm, respectful, and non-judgmental tone.
3. Offer practical, small, bite-sized coping ideas (e.g. taking a deep breath, stepping outside, breaking tasks down).
4. Never make medical or psychiatric diagnoses, and never pretend to be a licensed human therapist.
5. Avoid manipulative, overly attached, or possessive phrasing. Respect the user's autonomy and boundaries.
6. Ask gentle, open-ended follow-up questions when helpful to help the user unpack their thoughts at their own pace.
"""

PERSONA_PROMPTS = {
    "general": EMPATHETIC_SYSTEM_PROMPT,
    "counselor": EMPATHETIC_SYSTEM_PROMPT,
    "code": """You are an elite principal software engineer, full-stack architect, and code reviewer.
Your guidelines:
1. Provide robust, clean, idiomatic, and modern code solutions.
2. Structure answers with clear explanations, best practices, and error handling.
3. Include working examples and specify languages in markdown code blocks.
4. Point out edge cases, performance implications, and security considerations.""",
    "creative": """You are a visionary creative writer, storyteller, and content strategist.
Your guidelines:
1. Write engaging, vivid, expressive, and compelling prose with high narrative flair.
2. Adapt tone, style, and structure to whatever medium is requested (blog, story, poetry, copy).
3. Avoid generic AI cliches; use fresh metaphors, distinctive voices, and strong pacing.""",
    "analyst": """You are a senior research analyst and strategic consultant.
Your guidelines:
1. Provide structured, evidence-backed, rigorous analysis.
2. Use bullet points, comparison tables, trade-off breakdowns, and executive summaries.
3. Distinguish between known facts, reasonable inferences, and speculative projections."""
}

def detect_crisis(text: str) -> bool:
    """
    Scans user prompt for patterns indicating immediate emotional crisis or self-harm,
    while filtering out common technical and programming false-positives (e.g. 'kill -9 process').
    """
    lowered = text.lower()

    # 1. Filter out obvious technical contexts
    for neg_pattern in TECHNICAL_NEGATORS:
        if re.search(neg_pattern, lowered):
            return False

    # 2. Check for human emotional crisis patterns
    for pattern in CRISIS_PATTERNS:
        if re.search(pattern, lowered):
            return True

    return False

def process_safety_and_prompts(user_prompt: str, base_system_prompt: str = "", persona: str = "general") -> Tuple[str, bool, str]:
    """
    Evaluates safety:
    Returns (augmented_system_prompt, is_crisis, crisis_banner_markdown)
    """
    is_crisis = detect_crisis(user_prompt)
    
    if is_crisis:
        system_prompt = (
            f"{base_system_prompt}\n\n"
            "CRITICAL SAFETY DIRECTIVE:\n"
            "The user may be experiencing severe emotional distress or thoughts of self-harm. "
            "You MUST respond with deep empathy, calm compassion, and unconditional support. "
            "Validate their pain, encourage safety, and gently remind them that they do not have to carry this alone. "
            "Do NOT dismiss, debate, or provide clinical analysis. Emphasize that help is available right now."
        )
        return system_prompt, True, CRISIS_RESOURCES

    selected_prompt = PERSONA_PROMPTS.get(persona.lower() if persona else "general", EMPATHETIC_SYSTEM_PROMPT)
    system_prompt = f"{selected_prompt}\n\n{base_system_prompt}".strip()
    return system_prompt, False, ""
