# 🔍 FactCheck Agent

An AI-powered fact-checking web app that reads PDFs, cross-references claims against live web data, and flags inaccuracies.

## Live Demo
👉 **[Deploy link here after Streamlit Cloud deployment]**

## Features
- 📄 **PDF Upload** — extract text from any PDF document
- 🧠 **AI Claim Extraction** — Claude identifies all verifiable stats, dates, financial figures, and rankings
- 🌐 **Live Web Verification** — each claim is searched against the live web using Claude's web search tool
- 🏷️ **Three Verdicts**:
  - ✅ **Verified** — claim matches current reliable data
  - ⚠️ **Inaccurate** — claim is outdated or partially wrong (with correction provided)
  - ❌ **False** — claim has no credible support
- 📊 **Credibility Score** — overall document trust score
- ⬇️ **JSON Export** — download the full report

## Tech Stack
- **Frontend**: Streamlit
- **AI**: Claude Sonnet (Anthropic) with web search tool
- **PDF Parsing**: PyMuPDF (fitz)

## Setup

### 1. Clone the repo
```bash
git clone https://github.com/yourusername/factcheck-agent.git
cd factcheck-agent
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Set your Anthropic API key
```bash
export ANTHROPIC_API_KEY=sk-ant-your-key-here
```
Or enter it in the app UI when prompted.

### 4. Run locally
```bash
streamlit run app.py
```

## Deploy to Streamlit Cloud

1. Push this repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub repo
4. Set `ANTHROPIC_API_KEY` in **Secrets** (Settings → Secrets):
   ```toml
   ANTHROPIC_API_KEY = "sk-ant-your-key"
   ```
5. Deploy!

## How It Works

```
PDF Upload → Text Extraction (PyMuPDF)
     ↓
Claim Identification (Claude Sonnet)
     ↓
Web Search Verification (Claude + web_search tool)
     ↓
Verdict Assignment: Verified / Inaccurate / False
     ↓
Credibility Report + JSON Export
```

## Evaluation Criteria Met
- ✅ Extracts specific claims (stats, dates, financial/technical figures)
- ✅ Searches live web to confirm accuracy
- ✅ Flags claims as Verified, Inaccurate, or False
- ✅ Provides correct "real" facts for inaccurate/false claims
- ✅ Simple Streamlit frontend for PDF upload
- ✅ Deployable on Streamlit Cloud

## License
MIT
