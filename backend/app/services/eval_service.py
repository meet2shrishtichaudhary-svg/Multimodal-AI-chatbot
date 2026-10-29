import re
from typing import List, Dict, Any, Tuple

INJECTION_PATTERNS = [
    (r"ignore\s+(?:all\s+)?(?:previous|prior|above)\s+instructions", "Instruction override attempt"),
    (r"system\s+override\b", "System override attempt"),
    (r"disregard\s+(?:all\s+)?(?:safety|system|guardrail)", "Safety bypass attempt"),
    (r"you\s+are\s+now\s+(?:dan|unfiltered|jailbroken|unrestricted)", "Jailbreak persona adoption"),
    (r"pretend\s+you\s+have\s+no\s+(?:rules|restrictions|limits)", "Rule removal prompt"),
    (r"reveal\s+(?:your\s+)?(?:system\s+prompt|hidden\s+instructions|api\s+key)", "Prompt extraction attempt")
]

def detect_prompt_injection(prompt: str) -> Tuple[bool, float, str]:
    """
    Evaluates whether an incoming user prompt or uploaded document content
    contains adversarial jailbreak or prompt injection signatures.
    Returns: (is_injection, risk_score, reason)
    """
    lowered = prompt.lower()
    for pattern, reason in INJECTION_PATTERNS:
        match = re.search(pattern, lowered)
        if match:
            return True, 0.95, f"{reason} matched: '{match.group(0)}'"

    return False, 0.0, "Input clean"

def evaluate_citation_groundedness(
    response_text: str,
    citations: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Evaluates whether generated answer citations correspond to referenced facts.
    """
    if not citations:
        return {
            "has_citations": False,
            "groundedness_score": 1.0,
            "unsupported_citations": []
        }

    unsupported = []
    supported_count = 0

    for c in citations:
        title = c.get("title") or c.get("document_title") or ""
        # Check if title or key snippet keywords appear or are grounded
        snippet = c.get("snippet", "")
        key_words = [w.lower() for w in re.findall(r'\b\w{5,}\b', snippet)[:5]]
        
        matches = sum(1 for kw in key_words if kw in response_text.lower())
        if matches >= 1 or (title and title.lower() in response_text.lower()):
            supported_count += 1
        else:
            unsupported.append(title or "Unknown citation")

    score = supported_count / len(citations) if citations else 1.0

    return {
        "has_citations": True,
        "total_citations": len(citations),
        "supported_citations": supported_count,
        "groundedness_score": round(score, 2),
        "unsupported_citations": unsupported
    }

