"""Context truncation for AI prompts.

Sending the full document wastes tokens and context window. This module keeps
a window around the selected text so the LLM sees the immediate surroundings.
"""

from typing import Optional


def truncate_context(
    context: Optional[str],
    selected_text: Optional[str] = None,
    limit: int = 4000,
) -> Optional[str]:
    """Return at most `limit` characters of `context`, centered on `selected_text`.

    If `selected_text` is missing or not found, returns the head of the context.
    Returns None if context is empty.
    """
    if not context:
        return None
    if len(context) <= limit:
        return context

    idx = context.find(selected_text) if selected_text else -1
    if idx < 0:
        return context[:limit]

    half = limit // 2
    start = max(0, idx - half)
    end = min(len(context), start + limit)
    # Re-anchor start so we always produce exactly `limit` chars when possible.
    start = max(0, end - limit)

    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(context) else ""
    return prefix + context[start:end] + suffix
