import streamlit as st
from pypdf import PdfReader
import json
import re
import os
import anthropic
import time

st.set_page_config(
    page_title="FactCheck Agent",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
  .stApp { background: #0D1B2A; }
  h1 { color: #3DCCC7 !important; }
  h2, h3 { color: #CADCFC !important; }
  .stButton>button {
    background: linear-gradient(135deg, #0E9AA7, #3DCCC7);
    color: white; border: none; border-radius: 8px;
    padding: 0.6rem 2rem; font-weight: bold; font-size: 1rem;
  }
  .verdict-verified {
    background: #0A3D2A; border-left: 4px solid #2EC4B6;
    border-radius: 8px; padding: 1rem; margin: 0.5rem 0;
  }
  .verdict-inaccurate {
    background: #3A2A00; border-left: 4px solid #F4A261;
    border-radius: 8px; padding: 1rem; margin: 0.5rem 0;
  }
  .verdict-false {
    background: #3A0A0A; border-left: 4px solid #E84855;
    border-radius: 8px; padding: 1rem; margin: 0.5rem 0;
  }
  .claim-text { color: #CADCFC; font-size: 0.95rem; }
  .verdict-badge { font-weight: bold; font-size: 0.85rem; padding: 2px 10px; border-radius: 4px; display: inline-block; }
  .badge-verified { background: #2EC4B6; color: #0D1B2A; }
  .badge-inaccurate { background: #F4A261; color: #0D1B2A; }
  .badge-false { background: #E84855; color: white; }
  .explanation { color: #A0B4CC; font-size: 0.88rem; margin-top: 0.4rem; }
  .correction { color: #3DCCC7; font-size: 0.88rem; margin-top: 0.3rem; }
  .summary-box { background: #1B3A6B; border-radius: 12px; padding: 1.5rem; margin: 1rem 0; border: 1px solid #2A4A8B; }
  .metric-big { font-size: 2.5rem; font-weight: bold; text-align: center; }
  .metric-label { font-size: 0.8rem; text-align: center; color: #6B7A99; margin-top: -0.5rem; }
</style>
""", unsafe_allow_html=True)


def extract_pdf_text(uploaded_file) -> str:
    text = ""
    reader = PdfReader(uploaded_file)
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"
    return text


def extract_claims(text: str, client: anthropic.Anthropic) -> list:
    prompt = f"""You are a fact-checking specialist. Extract ALL verifiable factual claims from the document below.

Focus on:
- Statistics and percentages (e.g., "67% of users...", "sales grew 40%")
- Dates and timelines (e.g., "launched in 2019", "founded in 2010")
- Financial figures (e.g., "revenue of $5B", "valued at $50M")
- Named metrics, rankings, or records (e.g., "#1 in market share", "fastest growing")
- Technical specifications or capabilities

Return ONLY a valid JSON array (no markdown, no preamble) like:
[
  {{"claim": "the exact claim text", "context": "brief surrounding context", "category": "statistic|date|financial|ranking|technical"}},
  ...
]

Document:
{text[:6000]}"""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )
    raw = response.content[0].text.strip()
    raw = re.sub(r"^```json\s*", "", raw)
    raw = re.sub(r"```$", "", raw).strip()
    return json.loads(raw)


def verify_claim(claim_obj: dict, client: anthropic.Anthropic) -> dict:
    claim = claim_obj["claim"]
    category = claim_obj.get("category", "general")

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=800,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{
            "role": "user",
            "content": f"""You are a rigorous fact-checker. Verify this claim using live web search:

CLAIM: "{claim}"
CATEGORY: {category}

Search the web and return ONLY a JSON object (no markdown):
{{
  "verdict": "Verified" | "Inaccurate" | "False",
  "explanation": "1-2 sentence explanation",
  "correct_fact": "The accurate fact if Inaccurate/False, or null if Verified",
  "source_hint": "Brief mention of source type"
}}

Verdict definitions:
- Verified: claim matches current reliable data
- Inaccurate: claim is partially wrong or outdated (provide correction)
- False: claim has no credible support or directly contradicts evidence"""
        }]
    )

    result_text = ""
    for block in response.content:
        if hasattr(block, "text"):
            result_text += block.text

    result_text = result_text.strip()
    result_text = re.sub(r"^```json\s*", "", result_text)
    result_text = re.sub(r"```$", "", result_text).strip()

    try:
        result = json.loads(result_text)
    except Exception:
        result = {
            "verdict": "False",
            "explanation": "Could not verify this claim — no reliable data found.",
            "correct_fact": None,
            "source_hint": "N/A"
        }

    return {**claim_obj, **result}


def render_result_card(result: dict, index: int):
    verdict = result.get("verdict", "False")
    css_class = {"Verified": "verdict-verified", "Inaccurate": "verdict-inaccurate", "False": "verdict-false"}.get(verdict, "verdict-false")
    badge_class = {"Verified": "badge-verified", "Inaccurate": "badge-inaccurate", "False": "badge-false"}.get(verdict, "badge-false")
    icon = {"Verified": "✅", "Inaccurate": "⚠️", "False": "❌"}.get(verdict, "❓")

    correct_fact_html = ""
    if result.get("correct_fact"):
        correct_fact_html = f'<div class="correction">📌 <strong>Correct fact:</strong> {result["correct_fact"]}</div>'

    st.markdown(f"""
    <div class="{css_class}">
      <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:0.4rem;">
        <div class="claim-text"><strong>#{index+1}</strong> &nbsp;{result['claim']}</div>
        <div style="margin-left:1rem;white-space:nowrap;">
          <span class="verdict-badge {badge_class}">{icon} {verdict}</span>
        </div>
      </div>
      <div class="explanation">💬 {result.get('explanation','')}</div>
      {correct_fact_html}
      <div style="color:#4A5A70;font-size:0.78rem;margin-top:0.3rem;">📚 {result.get('source_hint','')}</div>
    </div>
    """, unsafe_allow_html=True)


def main():
    st.markdown("""
    <div style="text-align:center; padding: 2rem 0 1rem 0;">
      <h1 style="font-size:3rem; margin-bottom:0;">🔍 FactCheck Agent</h1>
      <p style="color:#6B7A99; font-size:1.1rem; margin-top:0.5rem;">
        Upload a PDF → AI extracts claims → Live web verification → Instant truth report
      </p>
    </div>
    """, unsafe_allow_html=True)

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        api_key = st.text_input("🔑 Anthropic API Key", type="password", placeholder="sk-ant-...")
    if not api_key:
        st.info("👆 Enter your Anthropic API key to get started.")
        return

    client = anthropic.Anthropic(api_key=api_key)

    st.markdown("---")
    uploaded_file = st.file_uploader("📄 Upload PDF for fact-checking", type=["pdf"])

    if not uploaded_file:
        st.markdown("""
        <div style="text-align:center; padding: 2rem; color: #6B7A99;">
          <div style="font-size:3rem;">📂</div>
          <div>Drop a PDF above to begin</div>
        </div>
        """, unsafe_allow_html=True)
        return

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        run = st.button("🚀 Run Fact-Check", use_container_width=True)

    if not run:
        st.success(f"✅ PDF ready: **{uploaded_file.name}** ({uploaded_file.size // 1024} KB) — click Run to start")
        return

    st.markdown("---")

    with st.spinner("📖 Extracting text from PDF..."):
        try:
            pdf_text = extract_pdf_text(uploaded_file)
        except Exception as e:
            st.error(f"Failed to read PDF: {e}")
            return

    if len(pdf_text.strip()) < 50:
        st.error("⚠️ PDF appears to be empty or image-only (no extractable text).")
        return

    st.info(f"📝 Extracted {len(pdf_text):,} characters from PDF.")

    with st.spinner("🧠 Identifying verifiable claims with AI..."):
        try:
            claims = extract_claims(pdf_text, client)
        except Exception as e:
            st.error(f"Claim extraction failed: {e}")
            return

    if not claims:
        st.warning("No verifiable claims found in this document.")
        return

    st.success(f"🎯 Found **{len(claims)} verifiable claims** — checking against live web data...")

    results = []
    progress = st.progress(0)
    status_area = st.empty()

    for i, claim_obj in enumerate(claims):
        short = claim_obj['claim'][:80] + "..." if len(claim_obj['claim']) > 80 else claim_obj['claim']
        status_area.markdown(f"🔎 Verifying claim **{i+1}/{len(claims)}**: *{short}*")
        try:
            result = verify_claim(claim_obj, client)
        except Exception as e:
            result = {**claim_obj, "verdict": "False", "explanation": f"Verification error: {e}", "correct_fact": None, "source_hint": "N/A"}
        results.append(result)
        progress.progress((i + 1) / len(claims))
        time.sleep(0.3)

    status_area.empty()
    progress.empty()

    verified = sum(1 for r in results if r["verdict"] == "Verified")
    inaccurate = sum(1 for r in results if r["verdict"] == "Inaccurate")
    false_count = sum(1 for r in results if r["verdict"] == "False")
    total = len(results)
    credibility = round((verified / total) * 100) if total else 0

    st.markdown(f"""
    <div class="summary-box">
      <h2 style="text-align:center; color:#3DCCC7; margin-bottom:1.5rem;">📊 Fact-Check Report</h2>
      <div style="display:grid; grid-template-columns: repeat(4, 1fr); gap:1rem;">
        <div><div class="metric-big" style="color:#3DCCC7;">{total}</div><div class="metric-label">CLAIMS CHECKED</div></div>
        <div><div class="metric-big" style="color:#2EC4B6;">{verified}</div><div class="metric-label">✅ VERIFIED</div></div>
        <div><div class="metric-big" style="color:#F4A261;">{inaccurate}</div><div class="metric-label">⚠️ INACCURATE</div></div>
        <div><div class="metric-big" style="color:#E84855;">{false_count}</div><div class="metric-label">❌ FALSE</div></div>
      </div>
      <div style="margin-top:1.5rem; text-align:center;">
        <div style="font-size:1rem; color:#6B7A99; margin-bottom:0.3rem;">Document Credibility Score</div>
        <div style="font-size:3rem; font-weight:bold; color:{'#2EC4B6' if credibility>=70 else '#F4A261' if credibility>=40 else '#E84855'};">{credibility}%</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### 📋 Detailed Results")
    tab_all, tab_verified, tab_inaccurate, tab_false = st.tabs([
        f"All ({total})", f"✅ Verified ({verified})",
        f"⚠️ Inaccurate ({inaccurate})", f"❌ False ({false_count})"
    ])

    with tab_all:
        for i, r in enumerate(results):
            render_result_card(r, i)
    with tab_verified:
        v_results = [r for r in results if r["verdict"] == "Verified"]
        [render_result_card(r, i) for i, r in enumerate(v_results)] if v_results else st.info("No verified claims found.")
    with tab_inaccurate:
        i_results = [r for r in results if r["verdict"] == "Inaccurate"]
        [render_result_card(r, i) for i, r in enumerate(i_results)] if i_results else st.info("No inaccurate claims found.")
    with tab_false:
        f_results = [r for r in results if r["verdict"] == "False"]
        [render_result_card(r, i) for i, r in enumerate(f_results)] if f_results else st.info("No false claims found.")

    st.markdown("---")
    report_data = {
        "file": uploaded_file.name,
        "summary": {"total": total, "verified": verified, "inaccurate": inaccurate, "false": false_count, "credibility_score": credibility},
        "results": results
    }
    st.download_button(
        label="⬇️ Download Full Report (JSON)",
        data=json.dumps(report_data, indent=2),
        file_name="factcheck_report.json",
        mime="application/json"
    )


if __name__ == "__main__":
    main()
