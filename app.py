import json
import time
import streamlit as st

from core.config import get_experience_text, get_openai_client
from core.parsers import extract_text_from_upload, parse_skill_buckets, coerce_json
from core.llm import call_gpt
from core.prompts import SYSTEM_PROMPT, build_user_prompt
from core.modify import json_convert
from core.docx_render import render_docx_bytes, timestamped_filename

# ---------------- Page Config ----------------
st.set_page_config(
    page_title="Resume Tailor • JD → JSON",
    page_icon="🧩",
    layout="wide"
)

# ---------------- Session State ----------------
ss = st.session_state
if "template_bytes" not in ss:
    ss.template_bytes = None
if "last_json" not in ss:
    ss.last_json = None
if "last_preset" not in ss:
    ss.last_preset = None

# ---------------- Load Styles ----------------
def load_local_css(path: str = "styles.css"):
    try:
        with open(path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        pass

load_local_css()

# ---------------- Data & Client ----------------
EXPERIENCE = get_experience_text()
client = get_openai_client()
BUCKETS = ["Programming", "Data Engineering", "Cloud", "Database", "ML/AI", "Misc"]
SKILL_INVENTORY = parse_skill_buckets(EXPERIENCE, BUCKETS=BUCKETS)

# ---------------- Header / Hero ----------------
st.markdown("""
<div class="hero">
  <div class="hero-left">
    <div class="badge">Data Engineering • ATS-Ready</div>
    <h1>Resume Tailor</h1>
    <p class="subtitle">Upload a JD → get <b>missing skills</b> by category and <b>tailored bullets</b> that match your fixed experience.</p>
  </div>
  <div class="hero-right">
    <div class="stat-card">
      <div class="stat-label">Model</div>
      <div class="stat-value">GPT-4o-mini</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Cost / run</div>
      <div class="stat-value">~$0.001–$0.005</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Delimiter</div>
      <div class="stat-value">$ per item</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ---------------- Experience Check ----------------
with st.expander("View loaded experience (server-side, read-only)"):
    st.text_area("Experience snapshot", value=EXPERIENCE[:10000], height=240, disabled=True)

# ---------------- 1) JD + Settings (FORM) ----------------
st.markdown('<div class="section-title">1) Job Description & Settings</div>', unsafe_allow_html=True)
with st.form(key="gen_form", clear_on_submit=False):
    cols = st.columns([1, 1])
    with cols[0]:
        jd_file = st.file_uploader("Upload JD (PDF/DOCX/TXT)", type=["pdf", "docx", "txt"], key="jd_uploader")
    with cols[1]:
        jd_text = st.text_area("Or paste JD text", value="", height=240, placeholder="Paste the entire JD here...")

    settings = st.columns([1, 2])
    with settings[0]:
        temperature = st.slider(
            "Creativity (temperature)", 0.0, 1.0, 0.25, 0.05,
            help="Lower = crisper JSON. 0.2–0.3 recommended."
        )
    with settings[1]:
        st.info("Output is JSON-only. Your core experience & architecture remain unchanged.", icon="✅")

    run_btn = st.form_submit_button("Generate", type="primary", use_container_width=True)

# ---------------- 2) Template Upload (persists across reruns) ----------------
st.markdown('<div class="section-title">2) Resume Template</div>', unsafe_allow_html=True)
tpl_cols = st.columns([1, 1, 1])
with tpl_cols[0]:
    tpl_file = st.file_uploader("Upload DOCX template", type=["docx"], key="tpl_uploader")
    if tpl_file is not None:
        ss.template_bytes = tpl_file.read()
        st.success(f"Template loaded: {tpl_file.name}")

# Try default template if none uploaded yet
if ss.template_bytes is None:
    try:
        with open("templates/resume_template.docx", "rb") as f:
            ss.template_bytes = f.read()
        st.caption("Using default template: templates/resume_template.docx")
    except FileNotFoundError:
        st.warning("Upload a DOCX template or place one at templates/resume_template.docx.")

with tpl_cols[1]:
    wrap_width = st.number_input("Wrap width", 60, 140, 100, key="wrap_width")
with tpl_cols[2]:
    wrap_trigger = st.number_input("Wrap trigger", 60, 160, 105, key="wrap_trigger")

# ---------------- Run (Generate) ----------------
if run_btn:
    with st.spinner("Analyzing JD and generating JSON..."):
        start = time.time()
        extracted = ""
        if jd_file is not None:
            extracted = extract_text_from_upload(jd_file)
        jd_final = (jd_text or "").strip() or (extracted or "").strip()

        if not jd_final:
            st.error("Please upload or paste a Job Description.")
        elif "YOUR EXPERIENCE TEXT NOT FOUND" in EXPERIENCE:
            st.error("Experience not configured. Set RESUME_EXPERIENCE or create experience.txt.")
        elif client is None:
            st.error("OPENAI_API_KEY not set. Configure env or Streamlit Secrets.")
        else:
            user_prompt = build_user_prompt(
                job_description=jd_final,
                experience_text=EXPERIENCE,
                skill_inventory=SKILL_INVENTORY,
                buckets=BUCKETS
            )
            raw = call_gpt(
                client=client,
                system_prompt=SYSTEM_PROMPT,
                user_prompt=user_prompt,
                model="gpt-4o-mini",
                temperature=temperature,
                max_tokens=2800  # more room for longer bullets
            )

            data = coerce_json(raw)
            if data is None:
                st.error("Could not parse JSON (model may have returned markdown or truncated JSON). Try lowering temperature.")
                with st.expander("Show raw model output"):
                    st.code(raw)
            else:
                elapsed = time.time() - start
                st.success(f"Done in {elapsed:.1f}s")

                st.subheader("🧩 Tailored Output (JSON)")
                st.json(data)

                # Persist results
                ss.last_json = data

                # Download JSON
                st.download_button(
                    "Download JSON",
                    data=json.dumps(data, indent=2).encode("utf-8"),
                    file_name="tailored_output.json",
                    mime="application/json",
                    use_container_width=True
                )

                # Convert to preset
                try:
                    ss.last_preset = json_convert(data)
                except Exception as e:
                    ss.last_preset = None
                    st.error(f"Preset conversion failed: {e}")
                else:
                    st.download_button(
                        "Download Preset JSON",
                        data=json.dumps(ss.last_preset, indent=2).encode("utf-8"),
                        file_name="tailored_preset.json",
                        mime="application/json",
                        use_container_width=True
                    )

# ---------------- 3) Render DOCX (FORM; uses persisted state) ----------------
st.markdown('<div class="section-title">3) Generate Resume DOCX</div>', unsafe_allow_html=True)
with st.form(key="render_form", clear_on_submit=False):
    disabled = (ss.template_bytes is None or ss.last_preset is None)
    render_btn = st.form_submit_button("Make DOCX", type="primary", use_container_width=True, disabled=disabled)

if "render_btn" in locals() and render_btn:
    if ss.template_bytes is None:
        st.error("No template loaded.")
    elif ss.last_preset is None:
        st.error("No tailored preset available. Generate JSON first.")
    else:
        try:
            docx_bytes = render_docx_bytes(
                template_bytes=ss.template_bytes,
                data=ss.last_preset,
                wrap_width=ss.wrap_width if "wrap_width" in ss else 100,
                wrap_trigger=ss.wrap_trigger if "wrap_trigger" in ss else 105
            )
            fname = timestamped_filename(
                role=ss.last_preset.get("TITLE_MAIN") or "Role",
                prefix="Resume"
            )
            st.download_button(
                "Download DOCX",
                data=docx_bytes,
                file_name=fname,
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True
            )
            st.success("DOCX generated.")
        except Exception as e:
            st.error(f"Failed to render DOCX: {e}")