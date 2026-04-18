"""Agent 3 Web — ממשק Streamlit למציאת לידים

מריצים עם:
    streamlit run agent3_web.py
"""

import os
import time
from datetime import datetime

import pandas as pd
import streamlit as st
from anthropic import Anthropic
from dotenv import load_dotenv

from agent3_leadfinder import (
    analyze_business,
    fetch_website,
    generate_message,
    generate_website_prompt,
    load_seen_leads,
    reset_seen_leads,
    save_seen_leads,
    search_with_dedup,
)

load_dotenv()
for secret_name in ("ANTHROPIC_API_KEY", "GOOGLE_MAPS_API_KEY", "APP_PASSWORD"):
    if secret_name not in os.environ:
        try:
            os.environ[secret_name] = st.secrets[secret_name]
        except (KeyError, FileNotFoundError):
            pass

# ============================================================
# Page config
# ============================================================
st.set_page_config(
    page_title="Lead Finder — מחפש לידים",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ============================================================
# Professional styling
# ============================================================
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Heebo:wght@300;400;500;600;700;800&display=swap');

    * {
        font-family: 'Heebo', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }

    .stApp { direction: rtl; background: #f7f8fa; }
    [data-testid="stMarkdownContainer"] { direction: rtl; text-align: right; }
    [data-testid="stTextArea"] textarea { direction: rtl; text-align: right; font-family: 'Heebo', sans-serif !important; }
    [data-testid="stTextInput"] input { direction: rtl; text-align: right; }
    h1, h2, h3, h4, h5 { direction: rtl; text-align: right; letter-spacing: -0.02em; }
    code, pre { direction: ltr; text-align: left; font-family: 'SF Mono', Consolas, monospace !important; }

    /* Hide default Streamlit header/footer */
    #MainMenu, footer, header[data-testid="stHeader"] { visibility: hidden; }

    /* Main container padding */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 1200px;
    }

    /* Hero header */
    .hero {
        background: linear-gradient(135deg, #1e3a8a 0%, #7c3aed 100%);
        color: white;
        padding: 2rem 2.5rem;
        border-radius: 16px;
        margin-bottom: 2rem;
        box-shadow: 0 10px 40px rgba(30, 58, 138, 0.15);
    }
    .hero h1 {
        color: white !important;
        margin: 0 !important;
        font-size: 2rem !important;
        font-weight: 700 !important;
    }
    .hero p {
        color: rgba(255,255,255,0.85) !important;
        margin: 0.5rem 0 0 0 !important;
        font-size: 1rem !important;
    }

    /* Form card */
    .search-form {
        background: white;
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04), 0 0 0 1px rgba(0,0,0,0.04);
        margin-bottom: 1.5rem;
    }

    /* Primary button */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #1e3a8a 0%, #7c3aed 100%) !important;
        border: none !important;
        color: white !important;
        font-weight: 600 !important;
        font-size: 1rem !important;
        padding: 0.6rem 1.5rem !important;
        border-radius: 8px !important;
        transition: all 0.2s !important;
        box-shadow: 0 2px 8px rgba(30, 58, 138, 0.2) !important;
    }
    .stButton > button[kind="primary"]:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 16px rgba(30, 58, 138, 0.3) !important;
    }

    /* Secondary button */
    .stButton > button:not([kind="primary"]) {
        background: white !important;
        border: 1px solid #d1d5db !important;
        color: #374151 !important;
        border-radius: 8px !important;
    }

    /* Metrics */
    [data-testid="stMetric"] {
        background: white;
        border-radius: 12px;
        padding: 1.25rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04), 0 0 0 1px rgba(0,0,0,0.04);
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.85rem !important;
        color: #6b7280 !important;
        font-weight: 500 !important;
    }
    [data-testid="stMetricValue"] {
        font-size: 2rem !important;
        font-weight: 700 !important;
        color: #111827 !important;
    }

    /* Expander cards */
    [data-testid="stExpander"] {
        background: white;
        border-radius: 12px !important;
        border: 1px solid #e5e7eb !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.03);
        margin-bottom: 0.75rem !important;
        transition: all 0.2s;
    }
    [data-testid="stExpander"]:hover {
        border-color: #c7d2fe !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }
    [data-testid="stExpander"] summary {
        padding: 1rem 1.25rem !important;
        font-weight: 600 !important;
    }

    /* Tabs */
    [data-baseweb="tab-list"] {
        gap: 0.5rem;
        border-bottom: 1px solid #e5e7eb !important;
    }
    [data-baseweb="tab"] {
        padding: 0.5rem 1rem !important;
        border-radius: 8px 8px 0 0 !important;
        font-weight: 500 !important;
    }
    [aria-selected="true"] {
        background: #f3f4f6 !important;
    }

    /* Score pills */
    .score-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 12px;
        border-radius: 999px;
        font-weight: 700;
        font-size: 0.85rem;
        margin-left: 8px;
    }
    .score-hot {
        background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
        color: #92400e;
        border: 1px solid #fcd34d;
    }
    .score-warm {
        background: #e0e7ff;
        color: #3730a3;
        border: 1px solid #c7d2fe;
    }
    .score-cold {
        background: #f3f4f6;
        color: #6b7280;
        border: 1px solid #e5e7eb;
    }

    /* Status info */
    .stAlert {
        border-radius: 10px !important;
        border: none !important;
    }

    /* Memory badge in header */
    .memory-badge {
        display: inline-block;
        padding: 4px 12px;
        background: rgba(255,255,255,0.2);
        border-radius: 999px;
        font-size: 0.85rem;
        color: white;
    }

    /* Download button styling */
    [data-testid="stDownloadButton"] button {
        width: 100%;
        border-radius: 8px !important;
        font-weight: 500 !important;
    }

    /* Caption */
    .elapsed-caption {
        color: #6b7280;
        font-size: 0.85rem;
        margin-bottom: 1rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# Optional password gate
# ============================================================

def require_password() -> None:
    expected = os.getenv("APP_PASSWORD", "")
    if not expected:
        return
    if st.session_state.get("authenticated"):
        return

    st.markdown('<div class="hero"><h1>🔐 כניסה למערכת</h1></div>', unsafe_allow_html=True)
    with st.form("login"):
        pwd = st.text_input("סיסמה", type="password")
        if st.form_submit_button("כניסה", type="primary"):
            if pwd == expected:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("סיסמה שגויה")
    st.stop()


require_password()


# ============================================================
# Validation
# ============================================================

if not os.getenv("GOOGLE_MAPS_API_KEY"):
    st.error("חסר GOOGLE_MAPS_API_KEY ב-.env")
    st.stop()
if not os.getenv("ANTHROPIC_API_KEY"):
    st.error("חסר ANTHROPIC_API_KEY ב-.env")
    st.stop()


# ============================================================
# Header
# ============================================================

seen = load_seen_leads()
memory_html = (
    f'<span class="memory-badge">💾 זיכרון: {len(seen)} עסקים</span>'
    if seen
    else '<span class="memory-badge">💾 זיכרון ריק</span>'
)

st.markdown(
    f"""
    <div class="hero">
        <h1>🎯 Lead Finder</h1>
        <p>מוצא עסקים פוטנציאליים לבניית אתרים · ניתוח חכם · הודעות פנייה מוכנות · פרומפטים לבניית אתר</p>
        <div style="margin-top: 1rem;">{memory_html}</div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# Search form
# ============================================================

with st.container():
    with st.form("search_form"):
        st.markdown("#### פרמטרים לחיפוש")
        col1, col2, col3 = st.columns([3, 3, 1])
        with col1:
            business_type = st.text_input(
                "סוג עסק",
                placeholder="מוסכים, מרפאות שיניים, חנויות בגדים...",
                label_visibility="visible",
            )
        with col2:
            location = st.text_input(
                "אזור (אופציונלי)",
                placeholder="תל אביב, ראשון לציון, חיפה...",
                label_visibility="visible",
            )
        with col3:
            count = st.number_input("כמות", min_value=1, max_value=20, value=5)

        col_btn1, col_btn2 = st.columns([4, 1])
        with col_btn1:
            submitted = st.form_submit_button(
                "חפש לידים חדשים",
                type="primary",
                use_container_width=True,
            )
        with col_btn2:
            reset = st.form_submit_button("🗑 אפס זיכרון", use_container_width=True)


if reset:
    reset_seen_leads()
    st.session_state.pop("last_results", None)
    st.success("הזיכרון אופס — הסוכן יכול להחזיר עכשיו את כל העסקים מחדש")
    time.sleep(1)
    st.rerun()


# ============================================================
# Search execution
# ============================================================

SCORE_EMOJI = {"hot": "🔥", "warm": "💡", "cold": "❄️"}
SCORE_LABEL = {"hot": "חם", "warm": "חמים", "cold": "קר"}


def score_bucket(score: int) -> str:
    if score >= 7:
        return "hot"
    if score >= 4:
        return "warm"
    return "cold"


def score_pill(score: int) -> str:
    bucket = score_bucket(score)
    return (
        f'<span class="score-pill score-{bucket}">'
        f'{SCORE_EMOJI[bucket]} {score}/10'
        f'</span>'
    )


def run_search(business_type: str, location: str, count: int) -> list[dict]:
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    seen_ids = load_seen_leads()

    status = st.status("מחפש ב-Google Places...", expanded=True)
    with status:
        try:
            businesses, filtered = search_with_dedup(business_type, location, count, seen_ids)
        except Exception as e:
            st.error(f"שגיאה בחיפוש: {e}")
            return []

        if not businesses:
            if filtered > 0:
                st.warning(
                    f"כל {filtered} התוצאות שנמצאו כבר בזיכרון. "
                    "נסה חיפוש אחר או לחץ 'אפס זיכרון'."
                )
            else:
                st.warning("לא נמצאו עסקים. נסה חיפוש רחב יותר.")
            return []

        msg = f"נמצאו {len(businesses)} עסקים חדשים"
        if filtered:
            msg += f" (עוד {filtered} נוספים כבר בזיכרון)"
        st.write(f"✓ {msg}. מנתח...")

        progress = st.progress(0.0)
        results = []
        for idx, biz in enumerate(businesses, 1):
            name = biz["name"] or "(ללא שם)"
            st.write(f"[{idx}/{len(businesses)}] {name}")
            try:
                html = fetch_website(biz["website_url"])
                analysis = analyze_business(client, biz, html)
                message = generate_message(client, biz, analysis)
                website_prompt = generate_website_prompt(client, biz)
                results.append({
                    **biz,
                    "score": analysis["score"],
                    "explanation": analysis["explanation"],
                    "whatsapp_message": message,
                    "website_build_prompt": website_prompt,
                })
            except Exception as e:
                st.write(f"  ⚠ שגיאה: {e}")
                results.append({
                    **biz,
                    "score": 0,
                    "explanation": f"שגיאה: {e}",
                    "whatsapp_message": "",
                    "website_build_prompt": "",
                })
            progress.progress(idx / len(businesses))

        results.sort(key=lambda r: r.get("score", 0) or 0, reverse=True)

        # commit to memory
        seen_ids.update(b["place_id"] for b in businesses if b.get("place_id"))
        save_seen_leads(seen_ids)

        status.update(label=f"הסתיים — {len(results)} לידים חדשים נשמרו", state="complete")
    return results


def render_results(results: list[dict]) -> None:
    avg = sum(r.get("score", 0) or 0 for r in results) / len(results)
    hot_count = sum(1 for r in results if (r.get("score") or 0) >= 7)
    warm_count = sum(1 for r in results if 4 <= (r.get("score") or 0) < 7)

    st.markdown("### סיכום")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("🎯 סה\"כ לידים", len(results))
    col2.metric("🔥 חמים (7+)", hot_count)
    col3.metric("💡 פושרים (4-6)", warm_count)
    col4.metric("📊 ציון ממוצע", f"{avg:.1f}")

    # Download
    df = pd.DataFrame(results)
    column_order = [
        "name", "category", "phone", "address", "website_url",
        "rating", "review_count", "score", "explanation",
        "whatsapp_message", "website_build_prompt",
    ]
    df = df.reindex(columns=column_order)
    csv_bytes = ("\ufeff" + df.to_csv(index=False)).encode("utf-8")
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")

    col_d1, col_d2 = st.columns([1, 3])
    with col_d1:
        st.download_button(
            "⬇️ הורד CSV",
            data=csv_bytes,
            file_name=f"leads_{timestamp}.csv",
            mime="text/csv",
        )

    st.markdown("### תוצאות")
    st.caption("הלידים ממוינים מהחם לקר. לחץ על כרטיס כדי לפתוח את ההודעה ופרומפט האתר.")

    for idx, r in enumerate(results, 1):
        score = r.get("score") or 0
        name = r.get("name") or "(ללא שם)"
        has_website = r.get("website_url")
        website_tag = "אתר קיים" if has_website else "ללא אתר"

        header_html = (
            f"{score_pill(score)} "
            f"<span style='font-weight:600;'>{name}</span> "
            f"<span style='color:#6b7280; font-size:0.9rem; margin-right:8px;'>· {website_tag}</span>"
        )

        # Streamlit expander labels don't support HTML, so we use a plain-text header
        bucket = score_bucket(score)
        label = f"{SCORE_EMOJI[bucket]}  {score}/10  ·  {name}  ·  {website_tag}"

        with st.expander(label, expanded=(idx <= 3)):
            # Details grid
            info_col, body_col = st.columns([1, 2])
            with info_col:
                st.markdown(f"**📞 טלפון**  \n`{r.get('phone') or 'לא זמין'}`")
                st.markdown(f"**📍 כתובת**  \n{r.get('address') or 'לא זמין'}")
                if has_website:
                    st.markdown(f"**🌐 אתר**  \n[{has_website}]({has_website})")
                else:
                    st.markdown("**🌐 אתר**  \n_אין אתר_")
                rating = r.get("rating") or "-"
                review_count = r.get("review_count") or 0
                st.markdown(f"**⭐ דירוג**  \n{rating} ({review_count} ביקורות)")
                if r.get("category"):
                    st.markdown(f"**🏷 קטגוריה**  \n{r['category']}")

            with body_col:
                st.markdown("**🔍 ניתוח**")
                st.info(r.get("explanation") or "-")

            tabs = st.tabs(["💬 הודעת WhatsApp", "🎨 פרומפט לבניית אתר"])
            with tabs[0]:
                message = r.get("whatsapp_message") or ""
                st.caption("העתק את הטקסט ושלח ב-WhatsApp ללקוח")
                st.text_area(
                    label="message",
                    value=message,
                    height=180,
                    key=f"msg_{idx}",
                    label_visibility="collapsed",
                )
            with tabs[1]:
                prompt_text = r.get("website_build_prompt") or ""
                st.caption("הדבק ב-Lovable / v0 / Claude / Bolt כדי לבנות אתר לדוגמה")
                st.text_area(
                    label="prompt",
                    value=prompt_text,
                    height=400,
                    key=f"prompt_{idx}",
                    label_visibility="collapsed",
                )


# ============================================================
# Main flow
# ============================================================

if submitted:
    if not business_type.strip():
        st.warning("אנא הזן סוג עסק")
    else:
        start = time.time()
        results = run_search(business_type.strip(), location.strip(), int(count))
        if results:
            st.session_state["last_results"] = results
            st.session_state["last_elapsed"] = time.time() - start
            st.rerun()

if "last_results" in st.session_state:
    elapsed = st.session_state.get("last_elapsed", 0)
    st.markdown(
        f'<div class="elapsed-caption">⏱ זמן הרצה אחרון: {elapsed:.1f} שניות</div>',
        unsafe_allow_html=True,
    )
    render_results(st.session_state["last_results"])
else:
    st.info(
        "💡 מלא את הטופס ולחץ 'חפש לידים חדשים' כדי להתחיל. "
        "הסוכן זוכר עסקים שכבר הופיעו ולא יציג אותם שוב."
    )
