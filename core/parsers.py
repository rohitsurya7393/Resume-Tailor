import io
import re
import streamlit as st
import json

def extract_text_from_upload(uploaded_file) -> str:
    name = uploaded_file.name.lower()
    data = uploaded_file.read()
    if name.endswith(".txt"):
        return data.decode("utf-8", errors="ignore")
    if name.endswith(".pdf"):
        try:
            import PyPDF2
        except ImportError:
            st.error("PyPDF2 not installed. Run: pip install PyPDF2")
            return ""
        reader = PyPDF2.PdfReader(io.BytesIO(data))
        return "\n".join([page.extract_text() or "" for page in reader.pages])
    if name.endswith(".docx"):
        try:
            import docx
        except ImportError:
            st.error("python-docx not installed. Run: pip install python-docx")
            return ""
        doc = docx.Document(io.BytesIO(data))
        return "\n".join([p.text for p in doc.paragraphs])
    # Fallback: try decode as text
    try:
        return data.decode("utf-8", errors="ignore")
    except Exception:
        return ""

def parse_skill_buckets(text: str, BUCKETS=None) -> dict:
    """
    Parses [Programming]... [Data Engineering]... etc from experience.txt
    Returns dict of {bucket: [skills]}
    """
    BUCKETS = BUCKETS or ["Programming", "Data Engineering", "Cloud", "Database", "ML/AI", "Misc"]
    out = {b: [] for b in BUCKETS}
    blocks = re.split(r"\n\s*(?=\[)", text.strip())
    for block in blocks:
        m = re.match(r"\[(?P<h>.+?)\]\s*\n(?P<body>[\s\S]+)", block)
        if not m:
            continue
        h = m.group("h").strip()
        body = m.group("body").strip()
        if h in out:
            items = [i.strip(" •\t,-") for i in re.split(r"[,\n]", body) if i.strip()]
            out[h] = [i for i in items if i]
    return out

def coerce_json(text: str):
    """
    Try to recover a valid JSON object from model output that may include
    markdown or be slightly malformed/truncated.

    Strategy:
      1) Prefer fenced ```json ... ``` block if present.
      2) Else, take substring from first '{' to last '}'.
      3) Light repairs: balance braces, remove trailing commas.
    Returns: dict or None
    """
    # 1) fenced ```json block
    m = re.search(r"```json\s*(\{[\s\S]*?\})\s*```", text)
    if m:
        candidate = m.group(1)
    else:
        # 2) first { ... last }
        start = text.find("{")
        end   = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        candidate = text[start:end+1]

    # 3) strict parse
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        # Light repairs
        open_braces = candidate.count("{")
        close_braces = candidate.count("}")
        if close_braces < open_braces:
            candidate = candidate + ("}" * (open_braces - close_braces))
        # remove trailing commas before } or ]
        candidate = re.sub(r",(\s*[}\]])", r"\1", candidate)
        # collapse unmatched backticks or stray code fences
        candidate = candidate.replace("```", "")
        try:
            return json.loads(candidate)
        except Exception:
            return None