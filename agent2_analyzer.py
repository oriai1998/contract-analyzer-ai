"""
Agent #2 — מנתח ומשווה מסמכים רב-תחומי (גרסה 3)
=================================================
תכונות:
- 🧠 Adaptive Thinking - חושב לעומק על מורכבים
- 🔴🟡🔵 רמות חומרה לכל סיכון
- 💬 Q&A - שאלות המשך אחרי הניתוח
- 📥 הורדת דוח כ-Markdown
- 🆚 **חדש: מצב השוואה - העלה 2 מסמכים והסוכן ממליץ על העדיף**

מצבים נתמכים:
- 🏠 נדל"ן | ⚖️ משפטי כללי | 💼 חוזי עבודה | 🤝 שירותים B2B | 🛡️ ביטוח

מריצים עם:
    streamlit run agent2_analyzer.py
"""

import base64
from datetime import datetime
from pathlib import Path

import anthropic
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# הגדרת הדף + RTL
# ============================================================
st.set_page_config(
    page_title="מנתח מסמכים",
    page_icon="🔍",
    layout="wide",
)

st.markdown(
    """
    <style>
        .stApp { direction: rtl; }
        [data-testid="stMarkdownContainer"] { direction: rtl; text-align: right; }
        [data-testid="stChatInput"] textarea { direction: rtl; text-align: right; }
        [data-testid="stTextArea"] textarea { direction: rtl; text-align: right; }
        [data-testid="stChatMessage"] { direction: rtl; text-align: right; }
        h1, h2, h3, h4 { direction: rtl; text-align: right; }
        .stTabs [data-baseweb="tab-list"] { direction: rtl; }
        code, pre { direction: ltr; text-align: left; }
        [data-testid="stDownloadButton"] button { width: 100%; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# מצבים
# ============================================================

BASE_DIR = Path(__file__).parent
PROMPTS_DIR = BASE_DIR / "prompts"
TEST_DATA_DIR = BASE_DIR / "test_data"

MODES = {
    "realestate": {
        "name": "🏠 נדל\"ן",
        "description": "ניתוח חוזי שכירות, מכר, ותיווך - מנקודת מבט יועץ נדל\"ן",
        "prompt_file": "realestate.md",
    },
    "legal": {
        "name": "⚖️ משפטי כללי",
        "description": "ניתוח משפטי מקיף של חוזים מסחריים, הסכמי סודיות (NDA), והסכמים כלליים",
        "prompt_file": "legal.md",
    },
    "employment": {
        "name": "💼 חוזי עבודה",
        "description": "ניתוח חוזה העסקה - מנקודת מבט עו\"ד דיני עבודה (אי-תחרות, IP, פיצויים, אופציות)",
        "prompt_file": "employment.md",
    },
    "services": {
        "name": "🤝 הסכמי שירותים B2B",
        "description": "ניתוח הסכמי ייעוץ, פיתוח, וקבלנות - לפרילנסרים ובעלי עסקים",
        "prompt_file": "services.md",
    },
    "insurance": {
        "name": "🛡️ פוליסות ביטוח",
        "description": "ניתוח פוליסת ביטוח - בריאות, חיים, רכב, דירה. מתמקד בסייגים והגנות חסרות",
        "prompt_file": "insurance.md",
    },
}


# ============================================================
# הוראות מצב השוואה - מתווספות לפרומפט הדומיין
# ============================================================

COMPARISON_INSTRUCTION_SUFFIX = """

---

# 🆚 מצב השוואה - **חשוב!**

עכשיו תקבל **שני מסמכים** ולא אחד. **שכח את המבנה הרגיל**. במקומו, ענה ב**מבנה השוואה** הבא:

## 📑 תקציר השוואה
2-4 שורות: על מה כל מסמך, ההתרשמות הראשונית של כל אחד, מי הצדדים.

## 📊 טבלת השוואה - נתונים מרכזיים
טבלה Markdown של הפרמטרים החשובים:

| פרמטר | מסמך A | מסמך B |
|--------|---------|---------|
| ... | ... | ... |

הפרמטרים בטבלה תלויים בסוג המסמך - לדוגמה:
- ביטוח: פרמיה, השתתפות עצמית, תקרת כיסוי, סייגים מרכזיים, חידוש אוטומטי
- חוזי עבודה: שכר, אופציות, אי-תחרות, פיצויים, חופשה
- שכירות: דמי שכירות, ערבויות, תקופה, חניה, יציאה מוקדמת

## ⚠️ סיכונים מרכזיים בכל אחד

### 📄 מסמך A - סיכונים
רשימה של 3-5 סיכונים מרכזיים עם רמות חומרה (🔴/🟡/🔵), בקצרה (משפט-שניים לכל אחד).

### 📄 מסמך B - סיכונים
אותו דבר.

## 🥊 השוואה ישירה לפי קטגוריות

לכל קטגוריה רלוונטית (מחיר, היקף, סיכונים, גמישות, אחריות, סיום, וכו'), כתוב:
- **קטגוריה X:** מסמך A 🥇 / מסמך B 🥇 - הסבר קצר למה.

## 🏆 הפסיקה הסופית

### **המלצה: 📄 מסמך A** _או_ **📄 מסמך B**

**3-5 סיבות עיקריות:**
1. ...
2. ...
3. ...

**⚠️ חיסרון של הבחירה:** מה כדאי לדעת על המסמך הנבחר. מה לדרוש לתקן בו לפני חתימה.

**🔄 מתי לבחור הפוך:** באילו תרחישים דווקא המסמך השני עדיף.

## 💰 ההבדל הכספי בפועל
תרגם את ההפרש לסכום בשקלים: "מסמך A חוסך לך כ-X ₪ בשנה / לתקופת ההסכם".

---

**זכור:** המומחיות שלך בתחום (כפי שהוגדר ב-system prompt) חלה על שני המסמכים. אל תמציא מידע שלא מופיע במסמכים. אם פרמטר חסר באחד - כתוב "לא צוין" באותה שורה בטבלה.
"""


# ============================================================
# פונקציות עזר
# ============================================================

def load_prompt(filename: str) -> str:
    """טוען system prompt מקובץ."""
    return (PROMPTS_DIR / filename).read_text(encoding="utf-8")


def list_sample_files():
    """מחזיר רשימת קבצי דוגמה לבדיקה."""
    if not TEST_DATA_DIR.exists():
        return []
    return sorted(TEST_DATA_DIR.glob("*.txt"))


def get_qa_system_prompt(mode_key: str, comparison: bool = False) -> str:
    """system prompt למצב Q&A."""
    domain_map = {
        "realestate": "יועץ נדל\"ן בכיר",
        "legal": "עורך דין מסחרי",
        "employment": "עו\"ד דיני עבודה",
        "services": "עו\"ד מסחרי המתמחה בהסכמי שירותים",
        "insurance": "יועץ ביטוח ופנסיוני",
    }
    domain = domain_map.get(mode_key, "מומחה בתחום")
    context = "ושני המסמכים שהשווית" if comparison else "והניתוח שעשית"
    return f"""אתה {domain} שזה עתה ניתחת {context} עבור משתמש.

איך לענות:
- בקצרה ובדיוק (1-3 פסקאות מקסימום)
- ענה רק על מה שיש במסמך/ים או בניתוח שעשית
- אם המידע לא קיים - תגיד "לא צוין במסמך" במקום להמציא
- אם רלוונטי - ציטט מהמסמך
- היה פרקטי - תן עצה ישימה
"""


def estimate_cost(usage) -> float:
    """מחזיר עלות ב-USD לפי השימוש."""
    return (usage.input_tokens * 5 + usage.output_tokens * 25) / 1_000_000


def build_export_markdown(
    analysis: str,
    mode_key: str,
    comparison: bool,
    document_preview_a: str,
    document_preview_b: str = "",
) -> str:
    """בונה קובץ Markdown להורדה."""
    mode_name = MODES[mode_key]["name"]
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    mode_label = "השוואה" if comparison else "ניתוח"

    docs_section = f"""## תצוגה מקדימה - מסמך A

```
{document_preview_a[:500]}{'...' if len(document_preview_a) > 500 else ''}
```
"""

    if comparison and document_preview_b:
        docs_section += f"""

## תצוגה מקדימה - מסמך B

```
{document_preview_b[:500]}{'...' if len(document_preview_b) > 500 else ''}
```
"""

    return f"""# דוח {mode_label} מסמך{'ים' if comparison else ''}

**תחום:** {mode_name}
**תאריך:** {timestamp}
**נוצר ע"י:** מנתח מסמכים AI (Claude Opus 4.7)

---

{docs_section}

---

{analysis}

---

*דוח זה נוצר אוטומטית. למסמכים מורכבים מומלץ להתייעץ גם עם איש מקצוע.*
"""


def build_message_content(doc_bytes, doc_text, doc_label="המסמך"):
    """בונה content block למסמך - PDF או טקסט."""
    if doc_bytes is not None:
        return [
            {"type": "text", "text": f"=== {doc_label} ==="},
            {
                "type": "document",
                "source": {
                    "type": "base64",
                    "media_type": "application/pdf",
                    "data": base64.standard_b64encode(doc_bytes).decode("utf-8"),
                },
            },
        ]
    return [{"type": "text", "text": f"=== {doc_label} ===\n\n{doc_text}"}]


# ============================================================
# מצב סשן
# ============================================================

if "last_analysis" not in st.session_state:
    st.session_state.last_analysis = None
if "last_usage" not in st.session_state:
    st.session_state.last_usage = None
if "last_document_text_a" not in st.session_state:
    st.session_state.last_document_text_a = None
if "last_document_text_b" not in st.session_state:
    st.session_state.last_document_text_b = None
if "last_mode_key" not in st.session_state:
    st.session_state.last_mode_key = None
if "last_was_comparison" not in st.session_state:
    st.session_state.last_was_comparison = False
if "qa_messages" not in st.session_state:
    st.session_state.qa_messages = []
if "comparison_mode" not in st.session_state:
    st.session_state.comparison_mode = False


# ============================================================
# כותרת + בחירות
# ============================================================

st.title("🔍 מנתח מסמכים")
st.caption("Claude Opus 4.7 · 5 מצבים · השוואה · Q&A")

col_mode, col_compare = st.columns([3, 2])

with col_mode:
    mode_key = st.selectbox(
        "בחר תחום ניתוח",
        options=list(MODES.keys()),
        format_func=lambda k: MODES[k]["name"],
        help="בחר את התחום שמתאים למסמך שאתה מנתח",
    )

with col_compare:
    st.session_state.comparison_mode = st.toggle(
        "🆚 מצב השוואה",
        value=st.session_state.comparison_mode,
        help="מעלים שני מסמכים, הסוכן משווה ביניהם וממליץ על העדיף",
    )

st.caption(f"💡 {MODES[mode_key]['description']}")

if st.session_state.comparison_mode:
    st.info(
        "🆚 **מצב השוואה פעיל.** העלה 2 מסמכים מאותו סוג - הסוכן ינתח כל אחד, "
        "ישווה ביניהם, וימליץ על העדיף עם הסבר למה."
    )

st.divider()


# ============================================================
# קלט: מסמך יחיד או 2 להשוואה
# ============================================================

document_bytes_a = None
document_text_a = None
document_bytes_b = None
document_text_b = None


def render_document_input(label: str, key_prefix: str):
    """רנדר טאבים להעלאת מסמך - PDF / טקסט / דוגמה."""
    doc_bytes = None
    doc_text = None

    tab1, tab2, tab3 = st.tabs(
        ["📤 העלה PDF", "📝 הדבק טקסט", "🧪 דוגמה"],
    )

    with tab1:
        uploaded = st.file_uploader(
            f"בחר קובץ PDF - {label}",
            type=["pdf"],
            key=f"{key_prefix}_pdf",
        )
        if uploaded is not None:
            doc_bytes = uploaded.read()
            st.success(f"✅ {uploaded.name} ({len(doc_bytes) // 1024} KB)")

    with tab2:
        text_input = st.text_area(
            f"הדבק טקסט - {label}",
            height=200,
            key=f"{key_prefix}_text",
            placeholder="הדבק את טקסט המסמך...",
        )
        if text_input.strip():
            doc_text = text_input
            st.success(f"✅ {len(text_input)} תווים")

    with tab3:
        samples = list_sample_files()
        if not samples:
            st.info("אין דוגמאות זמינות")
        else:
            for sample in samples:
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.text(f"📄 {sample.name}")
                with col2:
                    if st.button("השתמש", key=f"{key_prefix}_use_{sample.name}"):
                        st.session_state[f"{key_prefix}_sample_text"] = (
                            sample.read_text(encoding="utf-8")
                        )
                        st.session_state[f"{key_prefix}_sample_name"] = sample.name
                        st.session_state.last_analysis = None
                        st.session_state.qa_messages = []
                        st.rerun()

            sample_text = st.session_state.get(f"{key_prefix}_sample_text")
            if sample_text:
                doc_text = sample_text
                with st.expander(
                    f"👁️ {st.session_state.get(f'{key_prefix}_sample_name', '')}"
                ):
                    st.text(sample_text[:600] + ("..." if len(sample_text) > 600 else ""))

    return doc_bytes, doc_text


if not st.session_state.comparison_mode:
    # מצב יחיד
    st.subheader("📥 בחר מקור למסמך")
    document_bytes_a, document_text_a = render_document_input("מסמך", "single")
else:
    # מצב השוואה - 2 עמודות
    st.subheader("📥 העלה 2 מסמכים להשוואה")

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("### 📄 מסמך A")
        document_bytes_a, document_text_a = render_document_input("מסמך A", "doc_a")

    with col_b:
        st.markdown("### 📄 מסמך B")
        document_bytes_b, document_text_b = render_document_input("מסמך B", "doc_b")


# ============================================================
# כפתור פעולה
# ============================================================

st.divider()

if st.session_state.comparison_mode:
    has_a = (document_bytes_a is not None) or (document_text_a is not None)
    has_b = (document_bytes_b is not None) or (document_text_b is not None)
    has_input = has_a and has_b
    button_label = "🆚 השווה את 2 המסמכים"
    if not has_input:
        st.caption(
            f"⬆️ דרושים שני מסמכים: A {'✅' if has_a else '❌'} · "
            f"B {'✅' if has_b else '❌'}"
        )
else:
    has_input = (document_bytes_a is not None) or (document_text_a is not None)
    button_label = "🔍 נתח את המסמך"
    if not has_input:
        st.caption("⬆️ העלה PDF, הדבק טקסט, או בחר דוגמה")

action_clicked = st.button(
    button_label,
    type="primary",
    use_container_width=True,
    disabled=not has_input,
)


# ============================================================
# הרצת הניתוח / ההשוואה
# ============================================================

if action_clicked and has_input:
    try:
        client = anthropic.Anthropic()
    except Exception as e:
        st.error(f"שגיאה ביצירת חיבור: {e}")
        st.stop()

    base_prompt = load_prompt(MODES[mode_key]["prompt_file"])

    if st.session_state.comparison_mode:
        system_prompt = base_prompt + COMPARISON_INSTRUCTION_SUFFIX
        content = (
            build_message_content(document_bytes_a, document_text_a, "מסמך A")
            + build_message_content(document_bytes_b, document_text_b, "מסמך B")
            + [
                {
                    "type": "text",
                    "text": "השווה בין שני המסמכים והמליץ על העדיף, לפי המבנה שהוגדר.",
                }
            ]
        )
        max_tok = 12000  # יותר מקום להשוואה
    else:
        system_prompt = base_prompt
        content = build_message_content(document_bytes_a, document_text_a, "המסמך")
        content.append(
            {"type": "text", "text": "נתח את המסמך לפי המבנה שהוגדר."}
        )
        max_tok = 10000

    # שמירת הטקסט לסשן (לצורך Q&A)
    st.session_state.last_document_text_a = (
        document_text_a if document_text_a else f"[PDF - {len(document_bytes_a)} bytes]"
    )
    if st.session_state.comparison_mode:
        st.session_state.last_document_text_b = (
            document_text_b if document_text_b else f"[PDF - {len(document_bytes_b)} bytes]"
        )
    else:
        st.session_state.last_document_text_b = None

    st.session_state.qa_messages = []
    st.session_state.last_mode_key = mode_key
    st.session_state.last_was_comparison = st.session_state.comparison_mode

    st.markdown("---")
    title_label = "🆚 תוצאות ההשוואה" if st.session_state.comparison_mode else "📊 תוצאות הניתוח"
    st.subheader(f"{title_label} ({MODES[mode_key]['name']})")

    placeholder = st.empty()
    full_text = ""

    try:
        with client.messages.stream(
            model="claude-opus-4-7",
            max_tokens=max_tok,
            thinking={"type": "adaptive"},
            system=system_prompt,
            messages=[{"role": "user", "content": content}],
        ) as stream:
            for text_chunk in stream.text_stream:
                full_text += text_chunk
                placeholder.markdown(full_text + "▌")

            placeholder.markdown(full_text)
            final_message = stream.get_final_message()
    except anthropic.APIError as e:
        st.error(f"שגיאה מ-API: {e}")
        st.stop()
    except Exception as e:
        st.error(f"שגיאה לא צפויה: {e}")
        st.stop()

    st.session_state.last_analysis = full_text
    st.session_state.last_usage = final_message.usage

    cost_total = estimate_cost(final_message.usage)
    st.caption(
        f"📊 {final_message.usage.input_tokens:,} טוקנים קלט · "
        f"{final_message.usage.output_tokens:,} פלט · "
        f"💰 ${cost_total:.3f} (~{cost_total * 3.7:.2f} ₪)"
    )

elif st.session_state.last_analysis and not action_clicked:
    st.markdown("---")
    mode_name = MODES.get(st.session_state.last_mode_key, {}).get("name", "")
    label = "🆚 ההשוואה האחרונה" if st.session_state.last_was_comparison else "📊 הניתוח האחרון"
    st.subheader(f"{label} {mode_name}")
    st.markdown(st.session_state.last_analysis)
    if st.session_state.last_usage:
        cost_total = estimate_cost(st.session_state.last_usage)
        st.caption(
            f"📊 {st.session_state.last_usage.input_tokens:,} input · "
            f"{st.session_state.last_usage.output_tokens:,} output · "
            f"💰 ${cost_total:.3f}"
        )


# ============================================================
# כפתורי פעולה אחרי ניתוח
# ============================================================

if st.session_state.last_analysis:
    st.divider()

    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        export_md = build_export_markdown(
            analysis=st.session_state.last_analysis,
            mode_key=st.session_state.last_mode_key or mode_key,
            comparison=st.session_state.last_was_comparison,
            document_preview_a=st.session_state.last_document_text_a or "",
            document_preview_b=st.session_state.last_document_text_b or "",
        )
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        prefix = "comparison" if st.session_state.last_was_comparison else "analysis"
        st.download_button(
            label="📥 הורד דוח (Markdown)",
            data=export_md.encode("utf-8"),
            file_name=f"{prefix}_{timestamp}.md",
            mime="text/markdown",
            use_container_width=True,
        )

    with col2:
        if st.button("🗑️ נקה הכל", use_container_width=True):
            st.session_state.last_analysis = None
            st.session_state.last_usage = None
            st.session_state.last_document_text_a = None
            st.session_state.last_document_text_b = None
            st.session_state.qa_messages = []
            for k in list(st.session_state.keys()):
                if "_sample_text" in k or "_sample_name" in k:
                    st.session_state.pop(k)
            st.rerun()

    with col3:
        if st.session_state.qa_messages and st.button(
            "🔄 נקה רק Q&A", use_container_width=True
        ):
            st.session_state.qa_messages = []
            st.rerun()


# ============================================================
# Q&A: שאלות המשך
# ============================================================

if st.session_state.last_analysis and st.session_state.last_document_text_a:
    st.divider()
    st.subheader("💬 שאלות המשך")
    st.caption(
        "יש לך שאלה ספציפית על המסמך/ים או הניתוח? שאל כאן. "
        "הסוכן זוכר את הכל."
    )

    for q, a in st.session_state.qa_messages:
        with st.chat_message("user", avatar="👤"):
            st.markdown(q)
        with st.chat_message("assistant", avatar="🤖"):
            st.markdown(a)

    if question := st.chat_input("שאל שאלה..."):
        with st.chat_message("user", avatar="👤"):
            st.markdown(question)

        with st.chat_message("assistant", avatar="🤖"):
            try:
                client = anthropic.Anthropic()
            except Exception as e:
                st.error(f"שגיאה: {e}")
                st.stop()

            qa_system = get_qa_system_prompt(
                st.session_state.last_mode_key or mode_key,
                comparison=st.session_state.last_was_comparison,
            )

            # בונה קונטקסט לפי מצב
            if st.session_state.last_was_comparison:
                context_msg = (
                    "להלן 2 המסמכים שהשוויתי, ההמלצה שלי, ואז שאלות המשך.\n\n"
                    "=== מסמך A ===\n"
                    f"{st.session_state.last_document_text_a}\n\n"
                    "=== מסמך B ===\n"
                    f"{st.session_state.last_document_text_b}\n\n"
                    "=== ההשוואה וההמלצה ===\n"
                    f"{st.session_state.last_analysis}"
                )
            else:
                context_msg = (
                    "להלן המסמך שניתחתי, הניתוח שלי, ואז שאלות המשך.\n\n"
                    "=== המסמך ===\n"
                    f"{st.session_state.last_document_text_a}\n\n"
                    "=== הניתוח שלי ===\n"
                    f"{st.session_state.last_analysis}"
                )

            qa_messages = [
                {"role": "user", "content": context_msg},
                {"role": "assistant", "content": "מצוין, הכל מולי. שאל מה שתרצה."},
            ]

            for prev_q, prev_a in st.session_state.qa_messages:
                qa_messages.append({"role": "user", "content": prev_q})
                qa_messages.append({"role": "assistant", "content": prev_a})

            qa_messages.append({"role": "user", "content": question})

            placeholder = st.empty()
            answer_text = ""

            try:
                with client.messages.stream(
                    model="claude-opus-4-7",
                    max_tokens=2000,
                    thinking={"type": "adaptive"},
                    system=qa_system,
                    messages=qa_messages,
                ) as stream:
                    for text_chunk in stream.text_stream:
                        answer_text += text_chunk
                        placeholder.markdown(answer_text + "▌")
                    placeholder.markdown(answer_text)
                    qa_final = stream.get_final_message()
            except Exception as e:
                st.error(f"שגיאה: {e}")
                st.stop()

            cost = estimate_cost(qa_final.usage)
            st.caption(
                f"💰 ${cost:.3f} (~{cost * 3.7:.2f} ₪) · "
                f"{qa_final.usage.input_tokens:,} in / {qa_final.usage.output_tokens:,} out"
            )

        st.session_state.qa_messages.append((question, answer_text))
        st.rerun()
