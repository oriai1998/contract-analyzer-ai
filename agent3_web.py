"""Agent 3 Web — ממשק Streamlit למציאת לידים

מריצים עם:
    streamlit run agent3_web.py
"""

import io
import os
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st
from anthropic import Anthropic
from dotenv import load_dotenv

from agent3_leadfinder import (
    analyze_business,
    fetch_website,
    generate_message,
    generate_website_prompt,
    search_businesses,
)

load_dotenv()
for secret_name in ("ANTHROPIC_API_KEY", "GOOGLE_MAPS_API_KEY", "APP_PASSWORD"):
    if secret_name not in os.environ:
        try:
            os.environ[secret_name] = st.secrets[secret_name]
        except (KeyError, FileNotFoundError):
            pass

# ============================================================
# Page config + RTL
# ============================================================
st.set_page_config(
    page_title="מחפש לידים",
    page_icon="🎯",
    layout="wide",
)

st.markdown(
    """
    <style>
        .stApp { direction: rtl; }
        [data-testid="stMarkdownContainer"] { direction: rtl; text-align: right; }
        [data-testid="stTextArea"] textarea { direction: rtl; text-align: right; }
        [data-testid="stTextInput"] input { direction: rtl; text-align: right; }
        h1, h2, h3, h4 { direction: rtl; text-align: right; }
        code, pre { direction: ltr; text-align: left; }
        .score-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-weight: bold;
            font-size: 14px;
        }
        .score-hot { background-color: #d4edda; color: #155724; }
        .score-warm { background-color: #fff3cd; color: #856404; }
        .score-cold { background-color: #f8d7da; color: #721c24; }
        .lead-card {
            border: 1px solid #e1e4e8;
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 12px;
            background-color: #fafbfc;
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
        return  # no password configured → skip gate (local dev)

    if st.session_state.get("authenticated"):
        return

    st.title("🔐 כניסה למערכת")
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
    st.error("❌ חסר GOOGLE_MAPS_API_KEY ב-.env")
    st.stop()
if not os.getenv("ANTHROPIC_API_KEY"):
    st.error("❌ חסר ANTHROPIC_API_KEY ב-.env")
    st.stop()


# ============================================================
# Header
# ============================================================

st.title("🎯 מחפש לידים")
st.caption("מצא עסקים פוטנציאליים לשירותי בניית אתרים — ניתוח + הודעת WhatsApp + פרומפט לאתר")


# ============================================================
# Search form
# ============================================================

with st.form("search_form"):
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        business_type = st.text_input(
            "סוג עסק",
            placeholder="לדוגמה: מוסכים, מרפאות שיניים, מסעדות",
        )
    with col2:
        location = st.text_input(
            "אזור",
            placeholder="לדוגמה: תל אביב, פתח תקווה (השאר ריק לכל הארץ)",
        )
    with col3:
        count = st.number_input("כמות", min_value=1, max_value=20, value=5)

    submitted = st.form_submit_button("🔍 חפש לידים", type="primary", use_container_width=True)


# ============================================================
# Search execution
# ============================================================

def score_class(score: int) -> str:
    if score >= 7:
        return "score-hot"
    if score >= 4:
        return "score-warm"
    return "score-cold"


def score_emoji(score: int) -> str:
    if score >= 7:
        return "🔥"
    if score >= 4:
        return "💡"
    return "❄️"


def run_search(business_type: str, location: str, count: int) -> list[dict]:
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    status = st.status("מחפש ב-Google Places...", expanded=True)
    with status:
        try:
            businesses = search_businesses(business_type, location, count)
        except Exception as e:
            st.error(f"שגיאה בחיפוש: {e}")
            return []

        if not businesses:
            st.warning("לא נמצאו עסקים. נסה חיפוש רחב יותר.")
            return []

        st.write(f"✓ נמצאו {len(businesses)} עסקים. מנתח...")

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
        status.update(label=f"✅ הסתיים — {len(results)} לידים", state="complete")
    return results


def render_results(results: list[dict]) -> None:
    avg = sum(r.get("score", 0) or 0 for r in results) / len(results)
    hot_count = sum(1 for r in results if (r.get("score") or 0) >= 7)

    col1, col2, col3 = st.columns(3)
    col1.metric("סה\"כ לידים", len(results))
    col2.metric("לידים חמים (7+)", hot_count)
    col3.metric("ציון ממוצע", f"{avg:.1f}")

    # Download button
    df = pd.DataFrame(results)
    column_order = [
        "name", "category", "phone", "address", "website_url",
        "rating", "review_count", "score", "explanation",
        "whatsapp_message", "website_build_prompt",
    ]
    df = df.reindex(columns=column_order)
    csv_bytes = ("\ufeff" + df.to_csv(index=False)).encode("utf-8")
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    st.download_button(
        "⬇️ הורד CSV",
        data=csv_bytes,
        file_name=f"leads_{timestamp}.csv",
        mime="text/csv",
        use_container_width=True,
    )

    st.divider()
    st.subheader("תוצאות (ממוינות לפי ציון)")

    for idx, r in enumerate(results, 1):
        score = r.get("score") or 0
        emoji = score_emoji(score)
        name = r.get("name") or "(ללא שם)"
        has_website = "יש אתר" if r.get("website_url") else "ללא אתר"

        with st.expander(f"{emoji} **{score}/10** — {name} ({has_website})", expanded=(idx <= 3)):
            meta_col, body_col = st.columns([1, 2])
            with meta_col:
                st.markdown(f"**טלפון:** `{r.get('phone') or 'לא זמין'}`")
                st.markdown(f"**כתובת:** {r.get('address') or 'לא זמין'}")
                if r.get("website_url"):
                    st.markdown(f"**אתר:** [{r['website_url']}]({r['website_url']})")
                st.markdown(f"**דירוג:** {r.get('rating') or 'ללא'} ({r.get('review_count') or 0} ביקורות)")
                st.markdown(f"**קטגוריה:** {r.get('category') or '-'}")

            with body_col:
                st.markdown("**למה הציון הזה:**")
                st.info(r.get("explanation") or "-")

            tabs = st.tabs(["💬 הודעת WhatsApp", "🎨 פרומפט לבניית אתר"])
            with tabs[0]:
                message = r.get("whatsapp_message") or ""
                st.text_area(
                    "ההודעה (העתק ושלח)",
                    value=message,
                    height=180,
                    key=f"msg_{idx}",
                )
            with tabs[1]:
                prompt_text = r.get("website_build_prompt") or ""
                st.text_area(
                    "הפרומפט (הדבק ב-Lovable / v0 / Claude כדי לבנות אתר לדוגמה)",
                    value=prompt_text,
                    height=400,
                    key=f"prompt_{idx}",
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

if "last_results" in st.session_state:
    elapsed = st.session_state.get("last_elapsed", 0)
    st.caption(f"⏱ זמן הרצה: {elapsed:.1f} שניות")
    render_results(st.session_state["last_results"])
else:
    st.info("👆 מלא את הטופס ולחץ 'חפש לידים' כדי להתחיל")
