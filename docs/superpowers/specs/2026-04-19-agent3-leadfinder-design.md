# Agent 3: Lead Finder — Design Spec

**Date:** 2026-04-19
**Status:** Approved, ready for implementation

## Purpose

Find potential clients for a website-building service. First used personally by the developer (Ori) for his own freelance work; later packaged for resale to other freelancers on Upwork.

## Users

- **Primary (MVP):** Ori — Israeli freelance web developer looking for leads
- **Secondary (future):** Other freelancers in Israel (designers, developers) who want automated lead generation

## Target Leads

Israeli businesses that either:
- Have no website at all
- Have an outdated / low-quality website

Single business category per run (e.g., "auto repair shops", "dental clinics").
Geographic scope: all of Israel, narrowable by city/area.

## Output

CSV file with one row per business, containing:
1. Business name
2. Phone
3. Address
4. Website URL (if any)
5. Relevance score 1–10
6. Explanation (why this lead is/isn't a good fit)
7. WhatsApp outreach message (personalized, Hebrew)
8. Website-building prompt (detailed prompt Ori can feed to an AI to build a sample site for this specific business)

## Architecture

Single Python script: `agent3_leadfinder.py`

Six internal functions:

1. `search_businesses(business_type, location, count)` → list of businesses from Google Places API
2. `fetch_website(url)` → HTML of the business's homepage (with timeout); returns None on failure
3. `analyze_business(business_info, html)` → uses Claude to return `(score, explanation)`
4. `generate_message(business_info, analysis)` → uses Claude to return a personalized Hebrew WhatsApp message
5. `generate_website_prompt(business_info, analysis)` → uses Claude to return a detailed prompt for building a website for this specific business (includes: style recommendation, colors, required features, sample Hebrew copy)
6. `save_to_csv(results, filepath)` → writes results to `output/leads_YYYY-MM-DD_<category>.csv`

### External APIs

- **Google Places API** (new SDK via `googlemaps` pip package) — $200/month free tier covers normal usage
- **Anthropic Claude API** — using Haiku 4.5 for cost efficiency (~$0.20 per run of 10 leads)

### Dependencies

Add to `requirements.txt`:
- `googlemaps` (new)
- `anthropic` (already present)
- `requests` (already present)
- `python-dotenv` (already present)

## Data Flow

```
USER INPUT (interactive prompts)
  ↓
  business_type, location, count
  ↓
search_businesses() → Google Places API
  ↓
  list of raw business records
  ↓
FOR EACH business:
  ↓
  fetch_website() if URL present → HTML or None
  ↓
  analyze_business() → Claude → (score, explanation)
  ↓
  generate_message() → Claude → WhatsApp message
  ↓
  generate_website_prompt() → Claude → site-building prompt
  ↓
  accumulate result dict
  ↓
save_to_csv() → output/leads_YYYY-MM-DD_<category>.csv
```

## Error Handling

| Error | Behavior |
|---|---|
| Google Places returns 0 results | Print friendly message, exit cleanly |
| Website fetch timeout (3s) | Skip HTML, mark "website not analyzed" |
| Website fetch 4xx/5xx | Skip HTML, mark "website not analyzed" |
| Claude API transient error | Retry once; on second failure skip this business and log |
| Missing API key | Clear error message with setup instructions |
| Google Places quota exceeded | Stop gracefully, save what was collected so far |

## Prompts

Stored as external files in `prompts/`:
- `analyze_prompt.txt` — scoring rubric + explanation format
- `message_prompt.txt` — tone guidance for Hebrew WhatsApp outreach
- `website_prompt.txt` — template for generating website-building prompts per business

Keeping prompts external makes them easy to tune without editing code.

## File Layout

```
money/
├── agent3_leadfinder.py          (new, main script)
├── .env                          (add GOOGLE_MAPS_API_KEY)
├── prompts/
│   ├── analyze_prompt.txt        (new)
│   ├── message_prompt.txt        (new)
│   └── website_prompt.txt        (new)
├── output/                       (new directory)
│   └── leads_YYYY-MM-DD_<cat>.csv (generated)
└── requirements.txt              (add googlemaps)
```

## Testing Strategy

MVP phase: manual validation only.
- Run once with a known category (e.g., "dental clinics in Tel Aviv", count=5)
- Human review: are messages sensible? Are prompts usable? Are scores reasonable?
- If all three pass, consider MVP validated.

No automated tests in MVP. If the script graduates to a sold product (Streamlit UI phase), add basic integration tests for the search + analyze flow.

## Out of Scope (MVP)

- Streamlit web UI (deferred to phase 2, only if MVP proves itself)
- Screenshot-based website analysis (deferred — HTML-only for now)
- Mobile responsiveness / speed / SEO checks (deferred to "deep analysis" upgrade)
- Auto-sending messages (explicitly never — user must review and send manually)
- Multiple business categories per run (one per run)

## Estimates

- Build time: 4–6 hours
- Cost per run: ~$0.30 (Google Places ~$0.05 + Claude Haiku ~$0.20 + buffer)
- Monthly cost at 2 runs/day: ~$18
