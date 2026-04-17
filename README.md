# Hebrew AI Document Analyzer

Multi-mode document analysis platform powered by Claude Opus 4.7 with native Hebrew support and RTL UI.

Built with the Anthropic Claude API to help Israeli professionals (real estate agents, lawyers, business owners) analyze contracts in seconds instead of hours.

---

## ✨ What's included

| Agent | Purpose | Tech demonstrated |
|-------|---------|-------------------|
| **Agent #1** — Personal Assistant | Hebrew chat assistant with persistent notes (file storage) | Claude API · tool use · agentic loop |
| **Agent #2** — Document Analyzer | Multi-mode contract analyzer (Real Estate / Legal) with PDF + text input | Claude API · PDF processing · structured output · streaming · multi-persona prompting |

Both agents run as web apps using Streamlit, with full Hebrew RTL UI.

---

## 🛠 Tech Stack

- **Language:** Python 3.14
- **LLM:** Claude Opus 4.7 (`claude-opus-4-7`) via official `anthropic` SDK (v0.96+)
- **Web UI:** Streamlit 1.56 with custom RTL CSS
- **Config:** `python-dotenv` for API key management
- **Document handling:** Native PDF support via Anthropic's document content blocks (base64), plus raw text input

---

## 🚀 Setup

```bash
# 1. Install dependencies
python -m pip install -r requirements.txt

# 2. Add your Anthropic API key
cp .env.example .env
# Then edit .env and paste your key from https://console.anthropic.com

# 3. Run an agent
python -m streamlit run agent1_web.py        # Personal assistant
python -m streamlit run agent2_analyzer.py   # Document analyzer
```

---

## 📁 Project Structure

```
money/
├── agent1_assistant.py      # CLI version of personal assistant
├── agent1_web.py            # Streamlit version of personal assistant
├── agent2_analyzer.py       # Multi-mode document analyzer
├── prompts/
│   ├── realestate.md        # Real estate analysis persona
│   └── legal.md             # Legal analysis persona
├── test_data/
│   └── sample_rental.txt    # Sample Hebrew rental contract for testing
├── notes/                   # Personal assistant note storage (gitignored)
├── docs/
│   ├── PORTFOLIO.md         # Marketing-facing project description (Hebrew)
│   ├── CASE_STUDY.md        # Real analysis output as proof of concept
│   └── social-templates.md  # WhatsApp/LinkedIn/Upwork outreach templates
├── assets/                  # Screenshots for portfolio
├── requirements.txt
└── .env                     # API key (gitignored)
```

---

## 🎯 Real-world use cases

- **Real estate agents** — review rental/sale contracts before signing
- **Lawyers** — quick first-pass analysis of incoming contracts
- **Business owners** — understand vendor agreements without paying for legal review
- **Anyone** — review their own apartment lease, employment contract, NDA

---

## 🧠 Architecture decisions

- **Single agent, multiple modes:** Instead of separate codebases per domain, agent #2 uses a shared engine with swappable system prompts. Adding a new vertical = adding a new prompt file.
- **Streaming output:** Long analyses stream token-by-token so the user sees progress immediately (better UX than a 30-second wait).
- **Structured Markdown output:** Each prompt instructs Claude to respond in fixed sections (summary, key data, risks, checklist, questions). This makes the output predictable and parseable.
- **Local-first:** Files saved to disk, API key in local `.env`. No external storage needed.

---

## 📊 Performance (sample run)

Tested on a 2-page Hebrew rental contract:
- **Latency:** ~25 seconds (full streaming response)
- **Cost:** ~$0.10 per document analysis
- **Detected:** 7 problematic clauses out of 10 planted issues, plus 1 bonus catch (excessive late-payment interest rate vs Israeli legal benchmark)
- **Bonus:** Cited specific Israeli law (חוק השכירות והשאילה תיקון 2017) without prompting

See [`docs/CASE_STUDY.md`](docs/CASE_STUDY.md) for the full analysis.
