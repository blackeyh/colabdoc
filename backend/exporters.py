from __future__ import annotations

import re
from html import escape
from typing import Any


def export_filename(title: str | None, extension: str, fallback: str) -> str:
    base = (title or "").strip().lower()
    base = re.sub(r"[^a-z0-9]+", "-", base).strip("-")
    if not base:
        base = fallback
    return f"{base}.{extension}"


def content_to_plain_text(content: Any) -> str:
    if not content:
        return ""
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, dict):
        if isinstance(content.get("text"), str) and not content.get("type"):
            return content["text"].strip()
        if content.get("type") == "doc":
            return _render_text_blocks(content.get("content", [])).strip()
    return ""


def document_to_plain_text(title: str, content: Any) -> str:
    body = content_to_plain_text(content)
    if body:
        return f"{title}\n\n{body}"
    return title


def document_to_html(title: str, content: Any) -> str:
    body = _render_html_root(content)
    if not body:
        body = "<p></p>"
    escaped_title = escape(title)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{escaped_title}</title>
  <style>
    :root {{
      color-scheme: light;
      font-family: Georgia, "Times New Roman", serif;
    }}
    body {{
      margin: 0;
      background: #f6f3ee;
      color: #1f2937;
    }}
    main {{
      max-width: 840px;
      margin: 0 auto;
      padding: 48px 24px 72px;
    }}
    article {{
      background: #fffdf8;
      border: 1px solid #e5dccf;
      border-radius: 18px;
      padding: 40px;
      box-shadow: 0 12px 30px rgba(31, 41, 55, 0.08);
    }}
    h1, h2, h3, h4, h5, h6 {{
      line-height: 1.2;
      margin-top: 1.4em;
      margin-bottom: 0.5em;
    }}
    h1 {{
      margin-top: 0;
      font-size: 2.25rem;
      border-bottom: 1px solid #eadfce;
      padding-bottom: 0.45em;
    }}
    p, li, blockquote, pre {{
      line-height: 1.7;
      font-size: 1rem;
    }}
    ul, ol {{
      padding-left: 1.5rem;
    }}
    blockquote {{
      margin: 1.25rem 0;
      padding-left: 1rem;
      border-left: 4px solid #d3b88c;
      color: #5b4630;
    }}
    pre {{
      background: #1f2937;
      color: #f9fafb;
      padding: 1rem;
      border-radius: 12px;
      overflow-x: auto;
    }}
    code {{
      font-family: "SFMono-Regular", Menlo, Consolas, monospace;
    }}
    hr {{
      border: none;
      border-top: 1px solid #e5dccf;
      margin: 2rem 0;
    }}
  </style>
</head>
<body>
  <main>
    <article>
      <h1>{escaped_title}</h1>
      {body}
    </article>
  </main>
</body>
</html>
"""


def _render_text_blocks(nodes: list[dict[str, Any]]) -> str:
    blocks = []
    for node in nodes:
        rendered = _render_text_node(node)
        if rendered:
            blocks.append(rendered.strip("\n"))
    return "\n\n".join(blocks)


def _render_text_node(node: dict[str, Any]) -> str:
    node_type = node.get("type")
    children = node.get("content", [])

    if node_type == "doc":
        return _render_text_blocks(children)
    if node_type in {"paragraph", "heading"}:
        return _render_inline_text(children)
    if node_type == "bulletList":
        items = []
        for child in children:
            rendered = _render_list_item(child, "- ")
            if rendered:
                items.append(rendered)
        return "\n".join(items)
    if node_type == "orderedList":
        start = node.get("attrs", {}).get("start") or 1
        items = []
        for index, child in enumerate(children, start):
            rendered = _render_list_item(child, f"{index}. ")
            if rendered:
                items.append(rendered)
        return "\n".join(items)
    if node_type == "listItem":
        return _render_text_blocks(children)
    if node_type == "blockquote":
        body = _render_text_blocks(children)
        return "\n".join(f"> {line}" if line else ">" for line in body.splitlines())
    if node_type == "codeBlock":
        return _extract_text(node)
    if node_type == "horizontalRule":
        return "-----"
    if node_type == "hardBreak":
        return "\n"
    if node_type == "text":
        return _apply_text_marks(node.get("text", ""), node.get("marks", []))
    return _render_text_blocks(children)


def _render_list_item(node: dict[str, Any], prefix: str) -> str:
    body = _render_text_node(node).strip()
    if not body:
        return ""
    lines = body.splitlines()
    padding = " " * len(prefix)
    return "\n".join(
        [f"{prefix}{lines[0]}"] + [f"{padding}{line}" for line in lines[1:]]
    )


def _render_inline_text(nodes: list[dict[str, Any]]) -> str:
    parts = []
    for node in nodes:
        node_type = node.get("type")
        if node_type == "text":
            parts.append(_apply_text_marks(node.get("text", ""), node.get("marks", [])))
        elif node_type == "hardBreak":
            parts.append("\n")
        else:
            parts.append(_render_text_node(node))
    return "".join(parts).strip()


def _apply_text_marks(text: str, marks: list[dict[str, Any]]) -> str:
    wrapped = text or ""
    for mark in marks or []:
        mark_type = mark.get("type")
        if mark_type == "code":
            wrapped = f"`{wrapped}`"
        elif mark_type == "strike":
            wrapped = f"~~{wrapped}~~"
    return wrapped


def _render_html_root(content: Any) -> str:
    if not content:
        return ""
    if isinstance(content, str):
        return f"<p>{escape(content)}</p>"
    if isinstance(content, dict):
        if isinstance(content.get("text"), str) and not content.get("type"):
            return f"<p>{escape(content['text'])}</p>"
        if content.get("type") == "doc":
            return "".join(_render_html_node(node) for node in content.get("content", []))
    return ""


def _render_html_node(node: dict[str, Any]) -> str:
    node_type = node.get("type")
    children = "".join(_render_html_node(child) for child in node.get("content", []))

    if node_type == "text":
        return _apply_html_marks(node.get("text", ""), node.get("marks", []))
    if node_type == "paragraph":
        return f"<p>{children or '<br />'}</p>"
    if node_type == "heading":
        level = node.get("attrs", {}).get("level") or 1
        level = min(max(int(level), 1), 6)
        return f"<h{level}>{children}</h{level}>"
    if node_type == "bulletList":
        return f"<ul>{children}</ul>"
    if node_type == "orderedList":
        start = node.get("attrs", {}).get("start")
        start_attr = f' start="{int(start)}"' if start and int(start) != 1 else ""
        return f"<ol{start_attr}>{children}</ol>"
    if node_type == "listItem":
        return f"<li>{children}</li>"
    if node_type == "blockquote":
        return f"<blockquote>{children}</blockquote>"
    if node_type == "codeBlock":
        return f"<pre><code>{escape(_extract_text(node))}</code></pre>"
    if node_type == "hardBreak":
        return "<br />"
    if node_type == "horizontalRule":
        return "<hr />"
    return children


def _apply_html_marks(text: str, marks: list[dict[str, Any]]) -> str:
    rendered = escape(text or "")
    for mark in marks or []:
        mark_type = mark.get("type")
        if mark_type == "bold":
            rendered = f"<strong>{rendered}</strong>"
        elif mark_type == "italic":
            rendered = f"<em>{rendered}</em>"
        elif mark_type == "strike":
            rendered = f"<s>{rendered}</s>"
        elif mark_type == "code":
            rendered = f"<code>{rendered}</code>"
    return rendered


def _extract_text(node: Any) -> str:
    if not node:
        return ""
    if isinstance(node, str):
        return node
    if isinstance(node, dict):
        node_type = node.get("type")
        if node_type == "text":
            return node.get("text", "")
        if node_type == "hardBreak":
            return "\n"
        return "".join(_extract_text(child) for child in node.get("content", []))
    if isinstance(node, list):
        return "".join(_extract_text(item) for item in node)
    return ""
