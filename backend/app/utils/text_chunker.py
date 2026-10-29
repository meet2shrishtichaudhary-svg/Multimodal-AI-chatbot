from typing import List, Dict, Any

def chunk_text(
    text: str,
    chunk_size: int = 600,
    chunk_overlap: int = 100,
    metadata: Dict[str, Any] = None
) -> List[Dict[str, Any]]:
    """
    Splits text into overlapping chunks, attempting to split at clean sentence
    or whitespace boundaries where possible.
    
    Returns a list of dicts with:
    - 'chunk_index': index of chunk
    - 'chunk_text': textual content of chunk
    - 'metadata': associated metadata (e.g., page, section)
    """
    if metadata is None:
        metadata = {}

    cleaned_text = text.strip()
    if not cleaned_text:
        return []

    chunks = []
    start = 0
    text_length = len(cleaned_text)
    chunk_index = 0

    while start < text_length:
        end = start + chunk_size

        if end >= text_length:
            chunk = cleaned_text[start:text_length].strip()
            if chunk:
                chunks.append({
                    "chunk_index": chunk_index,
                    "chunk_text": chunk,
                    "metadata": {**metadata, "start_char": start, "end_char": text_length}
                })
            break

        # Try to find a natural break point (newline, period, question mark, exclamation, or space)
        # Search backwards within the last 80 characters of the window
        search_window = cleaned_text[max(start, end - 80):end]
        break_offset = -1

        for punct in ["\n\n", "\n", ". ", "? ", "! ", " "]:
            pos = search_window.rfind(punct)
            if pos != -1:
                break_offset = max(start, end - 80) + pos + len(punct)
                break

        if break_offset != -1 and break_offset > start:
            chunk = cleaned_text[start:break_offset].strip()
            actual_end = break_offset
        else:
            chunk = cleaned_text[start:end].strip()
            actual_end = end

        if chunk:
            chunks.append({
                "chunk_index": chunk_index,
                "chunk_text": chunk,
                "metadata": {**metadata, "start_char": start, "end_char": actual_end}
            })
            chunk_index += 1

        # Advance start with overlap
        start = max(start + 1, actual_end - chunk_overlap)

    return chunks
