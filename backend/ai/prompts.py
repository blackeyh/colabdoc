"""Prompt templates for AI actions.

Templates use `str.format` with `{selected_text}` and `{context_block}`
placeholders. Keeping them in a module (rather than hardcoded in the router)
makes it trivial to swap wording, add new actions, or translate for tests.
"""

from typing import Optional

PROMPTS: dict[str, str] = {
    "summarize": (
        "Summarize the following text concisely, preserving key points and meaning."
        "{context_block}\n\nText to summarize:\n{selected_text}\n\n"
        "Provide only the summary, no preamble."
    ),
    "rewrite": (
        "Rewrite the following text to improve clarity, flow, and style while preserving "
        "the original meaning and tone."
        "{context_block}\n\nText to rewrite:\n{selected_text}\n\n"
        "Provide only the rewritten text, no preamble."
    ),
    "translate": (
        "Translate the following text to English. If it is already in English, translate "
        "it to Spanish."
        "{context_block}\n\nText to translate:\n{selected_text}\n\n"
        "Provide only the translation, no preamble."
    ),
    "restructure": (
        "Restructure the following text to improve its organization and logical flow. "
        "Use appropriate headings, bullet points, or paragraphs as needed."
        "{context_block}\n\nText to restructure:\n{selected_text}\n\n"
        "Provide only the restructured text, no preamble."
    ),
    "expand": (
        "Expand and elaborate on the following text, adding detail while preserving tone."
        "{context_block}\n\nText to expand:\n{selected_text}\n\n"
        "Provide only the expanded text, no preamble."
    ),
    "grammar": (
        "Fix grammar, spelling, and punctuation in the following text. "
        "Preserve voice and meaning; do not rewrite."
        "{context_block}\n\nText to correct:\n{selected_text}\n\n"
        "Provide only the corrected text, no preamble."
    ),
}

VALID_ACTIONS = frozenset(PROMPTS.keys())


def build_prompt(action: str, selected_text: str, context: Optional[str] = None) -> str:
    context_block = f"\n\nDocument context:\n{context}" if context else ""
    template = PROMPTS.get(action)
    if template is None:
        return f"Process the following text according to '{action}':\n{selected_text}"
    return template.format(selected_text=selected_text, context_block=context_block)
