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
    page_title="Lead Finder",
    page_icon=":dart:",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ============================================================
# Minimal black theme
# ============================================================
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Heebo:wght@300;400;500;600;700&display=swap');

    * {
        font-family: 'Heebo', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }

    /* Background and base text */
    .stApp { direction: rtl; background: #000000; color: #ffffff; }
    body, p, span, div, label { color: #ffffff; }

    [data-testid="stMarkdownContainer"] { direction: rtl; text-align: right; color: #ffffff; }
    [data-testid="stMarkdownContainer"] * { color: #ffffff; }
    [data-testid="stTextArea"] textarea {
        direction: rtl;
        text-align: right;
        background: #0a0a0a !important;
        color: #ffffff !important;
        border: 1px solid #2a2a2a !important;
        border-radius: 4px !important;
    }
    [data-testid="stTextInput"] input {
        direction: rtl;
        text-align: right;
        background: #0a0a0a !important;
        color: #ffffff !important;
        border: 1px solid #2a2a2a !important;
        border-radius: 4px !important;
    }
    [data-testid="stNumberInput"] input {
        background: #0a0a0a !important;
        color: #ffffff !important;
        border: 1px solid #2a2a2a !important;
        border-radius: 4px !important;
    }
    [data-testid="stNumberInput"] button {
        background: #0a0a0a !important;
        color: #ffffff !important;
        border-color: #2a2a2a !important;
    }

    h1, h2, h3, h4, h5, h6 {
        direction: rtl;
        text-align: right;
        color: #ffffff !important;
        letter-spacing: -0.01em;
    }

    code, pre {
        direction: ltr;
        text-align: left;
        background: #0a0a0a !important;
        color: #ffffff !important;
        font-family: 'SF Mono', Consolas, monospace !important;
    }

    a { color: #ffffff !important; text-decoration: underline; }

    /* Hide default Streamlit chrome */
    #MainMenu, footer, header[data-testid="stHeader"] { visibility: hidden; }

    .block-container {
        padding-top: 3rem;
        padding-bottom: 4rem;
        max-width: 1100px;
    }

    /* Hero — clean black with thin border */
    .hero {
        border: 1px solid #2a2a2a;
        padding: 2rem 2rem;
        margin-bottom: 2rem;
        background: #000000;
    }
    .hero h1 {
        color: #ffffff !important;
        margin: 0 !important;
        font-size: 1.75rem !important;
        font-weight: 600 !important;
        letter-spacing: -0.02em !important;
    }
    .hero p {
        color: #a0a0a0 !important;
        margin: 0.5rem 0 0 0 !important;
        font-size: 0.95rem !important;
        font-weight: 400 !important;
    }
    .hero .meta {
        margin-top: 1rem;
        color: #808080;
        font-size: 0.8rem;
        letter-spacing: 0.02em;
        text-transform: uppercase;
    }

    /* Buttons — outline style, no gradients */
    .stButton > button, [data-testid="stDownloadButton"] button, [data-testid="stFormSubmitButton"] button {
        background: #000000 !important;
        border: 1px solid #ffffff !important;
        color: #ffffff !important;
        font-weight: 500 !important;
        font-size: 0.9rem !important;
        padding: 0.6rem 1.25rem !important;
        border-radius: 2px !important;
        transition: all 0.15s !important;
        box-shadow: none !important;
    }
    .stButton > button:hover, [data-testid="stDownloadButton"] button:hover, [data-testid="stFormSubmitButton"] button:hover {
        background: #ffffff !important;
        color: #000000 !important;
    }
    .stButton > button[kind="primary"], [data-testid="stFormSubmitButton"] button[kind="primary"] {
        background: #ffffff !important;
        color: #000000 !important;
        border: 1px solid #ffffff !important;
    }
    .stButton > button[kind="primary"]:hover, [data-testid="stFormSubmitButton"] button[kind="primary"]:hover {
        background: #000000 !important;
        color: #ffffff !important;
    }

    /* Metrics */
    [data-testid="stMetric"] {
        background: #000000;
        border: 1px solid #2a2a2a;
        padding: 1rem 1.25rem;
        border-radius: 2px;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.75rem !important;
        color: #808080 !important;
        font-weight: 500 !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    [data-testid="stMetricValue"] {
        font-size: 1.75rem !important;
        font-weight: 600 !important;
        color: #ffffff !important;
    }

    /* Expanders */
    [data-testid="stExpander"] {
        background: #000000;
        border: 1px solid #2a2a2a !important;
        border-radius: 2px !important;
        margin-bottom: 0.5rem !important;
        transition: border-color 0.15s;
    }
    [data-testid="stExpander"]:hover {
        border-color: #4a4a4a !important;
    }
    [data-testid="stExpander"] summary {
        padding: 1rem 1.25rem !important;
        font-weight: 500 !important;
        color: #ffffff !important;
    }
    [data-testid="stExpander"] summary:hover {
        color: #ffffff !important;
    }
    [data-testid="stExpander"] [data-testid="stMarkdownContainer"] p {
        color: #ffffff !important;
    }
    details > summary svg { fill: #ffffff !important; }

    /* Tabs */
    [data-baseweb="tab-list"] {
        gap: 0;
        border-bottom: 1px solid #2a2a2a !important;
        background: transparent;
    }
    [data-baseweb="tab"] {
        padding: 0.5rem 1rem !important;
        font-weight: 500 !important;
        color: #808080 !important;
        background: transparent !important;
        border-radius: 0 !important;
    }
    [data-baseweb="tab"]:hover { color: #ffffff !important; }
    [aria-selected="true"] {
        background: transparent !important;
        color: #ffffff !important;
        border-bottom: 2px solid #ffffff !important;
    }
    [data-baseweb="tab-highlight"] { background: #ffffff !important; }

    /* Score label — text only, no colored background */
    .score-label {
        display: inline-block;
        padding: 2px 10px;
        border: 1px solid #ffffff;
        font-weight: 500;
        font-size: 0.85rem;
        margin-left: 8px;
        letter-spacing: 0.02em;
    }
    .score-dim {
        display: inline-block;
        padding: 2px 10px;
        border: 1px solid #4a4a4a;
        color: #808080 !important;
        font-weight: 400;
        font-size: 0.85rem;
        margin-left: 8px;
    }

    /* Alerts — minimal */
    [data-testid="stAlert"] {
        background: #0a0a0a !important;
        border: 1px solid #2a2a2a !important;
        border-radius: 2px !important;
        color: #ffffff !important;
    }
    [data-testid="stAlert"] * { color: #ffffff !important; }

    /* Status block */
    [data-testid="stStatusWidget"] { background: #0a0a0a !important; border: 1px solid #2a2a2a !important; }

    /* Progress */
    [data-testid="stProgress"] > div > div > div > div {
        background: #ffffff !important;
    }
    [data-testid="stProgress"] > div > div > div {
        background: #2a2a2a !important;
    }

    /* Form container */
    [data-testid="stForm"] {
        background: #000000;
        border: 1px solid #2a2a2a;
        border-radius: 2px;
        padding: 1.5rem;
    }

    /* Labels above inputs */
    label, [data-testid="stWidgetLabel"] {
        color: #a0a0a0 !important;
        font-size: 0.8rem !important;
        font-weight: 500 !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    /* Caption */
    .stCaption, [data-testid="stCaptionContainer"] {
        color: #808080 !important;
        font-size: 0.85rem;
    }

    .elapsed-caption {
        color: #808080;
        font-size: 0.8rem;
        margin-bottom: 1rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
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

    st.markdown('<div class="hero"><h1>כניסה למערכת</h1></div>', unsafe_allow_html=True)
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
memory_text = f"{len(seen)} עסקים בזיכרון" if seen else "זיכרון ריק"

st.markdown(
    f"""
    <div class="hero">
        <h1>Lead Finder</h1>
        <p>מוצא עסקים פוטנציאליים לבניית אתרים. ניתוח, הודעת פנייה, ופרומפט לבניית אתר — לכל ליד.</p>
        <div class="meta">{memory_text}</div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# Search form
# ============================================================

with st.container():
    with st.form("search_form"):
        col1, col2, col3 = st.columns([3, 3, 1])
        with col1:
            business_type = st.text_input(
                "סוג עסק",
                placeholder="מוסכים, מרפאות שיניים, חנויות בגדים",
                label_visibility="visible",
            )
        with col2:
            location = st.text_input(
                "אזור",
                placeholder="תל אביב, ראשון לציון, חיפה",
                label_visibility="visible",
            )
        with col3:
            count = st.number_input("כמות", min_value=1, max_value=20, value=5)

        col_btn1, col_btn2 = st.columns([4, 1])
        with col_btn1:
            submitted = st.form_submit_button(
                "חפש לידים",
                type="primary",
                use_container_width=True,
            )
        with col_btn2:
            reset = st.form_submit_button("אפס זיכרון", use_container_width=True)


if reset:
    reset_seen_leads()
    st.session_state.pop("last_results", None)
    st.success("הזיכרון אופס — הסוכן יכול להחזיר עכשיו את כל העסקים מחדש")
    time.sleep(1)
    st.rerun()


# ============================================================
# Search execution
# ============================================================

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
        st.write(f"{msg}. מנתח...")

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
                st.write(f"  שגיאה: {e}")
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
    col1.metric("סה\"כ לידים", len(results))
    col2.metric("ציון גבוה", hot_count)
    col3.metric("ציון בינוני", warm_count)
    col4.metric("ציון ממוצע", f"{avg:.1f}")

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
            "הורד CSV",
            data=csv_bytes,
            file_name=f"leads_{timestamp}.csv",
            mime="text/csv",
        )

    st.markdown("### תוצאות")
    st.caption("הלידים ממוינים מהציון הגבוה לנמוך. לחץ על כרטיס כדי לראות את ההודעה ופרומפט האתר.")

    for idx, r in enumerate(results, 1):
        score = r.get("score") or 0
        name = r.get("name") or "(ללא שם)"
        has_website = r.get("website_url")
        website_tag = "אתר קיים" if has_website else "ללא אתר"

        label = f"{score}/10   ·   {name}   ·   {website_tag}"

        with st.expander(label, expanded=(idx <= 3)):
            info_col, body_col = st.columns([1, 2])
            with info_col:
                st.markdown(f"**טלפון**  \n`{r.get('phone') or 'לא זמין'}`")
                st.markdown(f"**כתובת**  \n{r.get('address') or 'לא זמין'}")
                if has_website:
                    st.markdown(f"**אתר**  \n[{has_website}]({has_website})")
                else:
                    st.markdown("**אתר**  \n_אין_")
                rating = r.get("rating") or "-"
                review_count = r.get("review_count") or 0
                st.markdown(f"**דירוג**  \n{rating} ({review_count} ביקורות)")
                if r.get("category"):
                    st.markdown(f"**קטגוריה**  \n{r['category']}")

            with body_col:
                st.markdown("**ניתוח**")
                st.info(r.get("explanation") or "-")

            tabs = st.tabs(["הודעת WhatsApp", "פרומפט לבניית אתר"])
            with tabs[0]:
                message = r.get("whatsapp_message") or ""
                st.caption("העתק ושלח ב-WhatsApp")
                st.text_area(
                    label="message",
                    value=message,
                    height=180,
                    key=f"msg_{idx}",
                    label_visibility="collapsed",
                )
            with tabs[1]:
                prompt_text = r.get("website_build_prompt") or ""
                st.caption("הדבק ב-Lovable / v0 / Claude / Bolt")
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
        f'<div class="elapsed-caption">זמן הרצה אחרון: {elapsed:.1f} שניות</div>',
        unsafe_allow_html=True,
    )
    render_results(st.session_state["last_results"])
else:
    st.info(
        "מלא את הטופס ולחץ 'חפש לידים' כדי להתחיל. "
        "הסוכן זוכר עסקים שכבר הופיעו ולא יציג אותם שוב."
    )
