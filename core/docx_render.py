import json
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Iterable, Any, Tuple
from docxtpl import DocxTemplate, RichText

# ----------------------------
# Text & bullet processing
# ----------------------------

def collapse_ws(s: str) -> str:
    """Collapse all whitespace (incl. newlines/tabs) to single spaces."""
    return " ".join((s or "").split())


def split_on_dollar(s: str) -> List[str]:
    """
    Split a big textarea where bullets are delimited by '$'.
    Strips each item and drops empties.
    """
    if not s:
        return []
    parts = [p.strip() for p in s.split("$")]
    return [p for p in parts if p]


def smart_break_positions(text: str, width: int) -> Iterable[int]:
    """
    Yield break positions so that lines are ~`width` chars and
    we prefer breaking at a space at/left of the width.
    """
    i = 0
    n = len(text)
    while i + width < n:
        # try to break on the last space up to width
        cut = text.rfind(" ", i, i + width + 1)
        if cut == -1 or cut <= i + int(width * 0.25):
            # no nice space; hard break at width
            cut = i + width
        yield cut
        i = cut + 1  # resume after break (skip the space)
    # remaining tail handled by caller


def soft_wrap_multiline(text: str, width: int = 100, trigger: int = 105) -> List[str]:
    """
    For very long bullets, insert *soft* line breaks so they remain a SINGLE bullet.
    Rule:
      - If len(text) <= trigger: return [text]
      - Else: wrap to multiple lines at ~width chars, preferring spaces.
    Returns list of line parts that belong to ONE bullet.
    """
    text = collapse_ws(text)
    if len(text) <= trigger:
        return [text]

    lines: List[str] = []
    start = 0
    for cut in smart_break_positions(text, width):
        lines.append(text[start:cut].rstrip())
        start = cut + 1
    lines.append(text[start:].rstrip())
    return lines


def bullets_to_richtext(bullets: Iterable[str], width: int = 100, trigger: int = 105) -> List[RichText]:
    """
    Convert plain bullet strings to RichText, inserting soft line breaks
    so the continuation stays in the same bullet paragraph.
    """
    rts: List[RichText] = []
    for b in bullets:
        b = b.strip()
        if not b:
            continue
        parts = soft_wrap_multiline(b, width=width, trigger=trigger)
        rt = RichText()
        for idx, part in enumerate(parts):
            if idx > 0:
                rt.add("\n")  # soft line break in SAME paragraph
            rt.add(part)
        rts.append(rt)
    return rts


# ----------------------------
# Context builder & rendering
# ----------------------------

EXPECTED_ARRAY_KEYS = [
    "EXTRA_COURSEWORK",
    "EXTRA_PROGRAMMING",
    "EXTRA_DE",
    "EXTRA_CLOUD",
    "EXTRA_DB",
    "EXTRA_AI",
    "EXTRA_MISC",
    # bullets:
    "EXTRA_BULLETS_TEK",
    "EXTRA_BULLETS_ASSOCIATE",
    "EXTRA_BULLETS_INTERN",
    "EXTRA_ECOMMERCE",
    "EXTRA_HOSPITAL",
]

EXPECTED_SCALAR_KEYS = [
    "TITLE_MAIN",
    "TITLE_SUB",
    "TITLE_INTERN",
]

def build_context_from_json(data: Dict[str, Any],
                            wrap_width: int = 100,
                            wrap_trigger: int = 105) -> Dict[str, Any]:
    """
    Build the docxtpl context from a JSON-like dict.
    Creates RichText lists for bullets so long items soft-wrap inside one bullet.
    """
    ctx: Dict[str, Any] = {}

    # Scalars
    for k in EXPECTED_SCALAR_KEYS:
        ctx[k] = str(data.get(k, "") or "")

    # Arrays
    for k in EXPECTED_ARRAY_KEYS:
        val = data.get(k, [])
        if isinstance(val, str):
            # If someone stored bullets as a single '$'-joined string, split it.
            if k.startswith("EXTRA_BULLETS_") or k in ("EXTRA_ECOMMERCE", "EXTRA_HOSPITAL"):
                val = split_on_dollar(val)
            else:
                # skills/coursework could also be comma-separated
                val = [x.strip() for x in val.replace(",", "$").split("$") if x.strip()]
        elif not isinstance(val, list):
            val = []
        ctx[k] = [collapse_ws(str(x)) for x in val]

    # Rich bullets (use these in the Word template)
    ctx["RICH_BULLETS_TEK"]       = bullets_to_richtext(ctx["EXTRA_BULLETS_TEK"],       width=wrap_width, trigger=wrap_trigger)
    ctx["RICH_BULLETS_ASSOCIATE"] = bullets_to_richtext(ctx["EXTRA_BULLETS_ASSOCIATE"], width=wrap_width, trigger=wrap_trigger)
    ctx["RICH_BULLETS_INTERN"]    = bullets_to_richtext(ctx["EXTRA_BULLETS_INTERN"],    width=wrap_width, trigger=wrap_trigger)
    ctx["RICH_ECOMMERCE"]         = bullets_to_richtext(ctx["EXTRA_ECOMMERCE"],         width=wrap_width, trigger=wrap_trigger)
    ctx["RICH_HOSPITAL"]          = bullets_to_richtext(ctx["EXTRA_HOSPITAL"],          width=wrap_width, trigger=wrap_trigger)

    return ctx


def render_docx_bytes(template_bytes: bytes,
                      data: Dict[str, Any],
                      wrap_width: int = 100,
                      wrap_trigger: int = 105) -> bytes:
    """
    Render a DOCX in-memory and return its bytes.
    """
    ctx = build_context_from_json(data, wrap_width=wrap_width, wrap_trigger=wrap_trigger)
    tpl = DocxTemplate(BytesIO(template_bytes))
    tpl.render(ctx)
    buf = BytesIO()
    tpl.save(buf)
    buf.seek(0)
    return buf.read()


def timestamped_filename(role: str, prefix: str = "Resume") -> str:
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
    safe_role = (role or "Role").replace(" ", "_")
    return f"{prefix}_{safe_role}_{ts}.docx"