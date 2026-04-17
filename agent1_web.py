"""
Agent #1 — ממשק Web (גרסה משופרת)
==================================
שיפורים:
- ⚡ Streaming - תשובות מופיעות מילה-אחר-מילה בזמן אמת
- 🧠 Adaptive Thinking - חושב לעומק בשאלות מורכבות
- 🔍 search_notes - חיפוש מילולי בתוכן הפתקים

מריצים עם:
    streamlit run agent1_web.py
"""

import os
from datetime import datetime
from pathlib import Path

import anthropic
import streamlit as st
from dotenv import load_dotenv

# טוען API key: קודם מ-.env (לוקאלי), ואם אין - מ-Streamlit Secrets (cloud)
load_dotenv()
if "ANTHROPIC_API_KEY" not in os.environ:
    try:
        os.environ["ANTHROPIC_API_KEY"] = st.secrets["ANTHROPIC_API_KEY"]
    except (KeyError, FileNotFoundError):
        pass

# ============================================================
# הגדרות הדף + RTL
# ============================================================
st.set_page_config(
    page_title="העוזר האישי שלי",
    page_icon="🤖",
    layout="wide",
)

st.markdown(
    """
    <style>
        .stApp { direction: rtl; }
        [data-testid="stChatMessage"] { direction: rtl; text-align: right; }
        [data-testid="stMarkdownContainer"] { direction: rtl; text-align: right; }
        [data-testid="stChatInput"] textarea { direction: rtl; text-align: right; }
        h1, h2, h3 { direction: rtl; text-align: right; }
        code, pre { direction: ltr; text-align: left; }
    </style>
    """,
    unsafe_allow_html=True,
)

NOTES_DIR = Path(__file__).parent / "notes"
NOTES_DIR.mkdir(exist_ok=True)


# ============================================================
# כלים
# ============================================================

def save_note(title: str, content: str) -> str:
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    safe_title = "".join(c for c in title if c.isalnum() or c in " -_").strip()[:40]
    filename = f"{timestamp}_{safe_title or 'note'}.md"
    filepath = NOTES_DIR / filename
    filepath.write_text(f"# {title}\n\n{content}\n", encoding="utf-8")
    return f"נשמר: {filename}"


def list_notes() -> str:
    notes = sorted(NOTES_DIR.glob("*.md"), reverse=True)
    if not notes:
        return "אין פתקים שמורים עדיין."
    return "פתקים שמורים:\n" + "\n".join(f"- {n.stem}" for n in notes[:20])


def read_note(filename: str) -> str:
    name = filename if filename.endswith(".md") else f"{filename}.md"
    filepath = NOTES_DIR / name
    if not filepath.exists():
        matches = list(NOTES_DIR.glob(f"*{filename}*"))
        if not matches:
            return f"לא מצאתי פתק בשם: {filename}"
        filepath = matches[0]
    return filepath.read_text(encoding="utf-8")


def search_notes(query: str) -> str:
    """מחפש בתוכן של כל הפתקים."""
    matches = []
    query_lower = query.lower()
    for note_path in sorted(NOTES_DIR.glob("*.md"), reverse=True):
        content = note_path.read_text(encoding="utf-8")
        # התאמה גם בעברית (בלי lowercasing - לא משנה) וגם באנגלית (עם lowercasing)
        if query in content or query_lower in content.lower():
            # מציאת snippet מסביב להתאמה
            search_in = content if query in content else content.lower()
            search_for = query if query in content else query_lower
            idx = search_in.find(search_for)
            start = max(0, idx - 60)
            end = min(len(content), idx + len(query) + 100)
            snippet = content[start:end].replace("\n", " ").strip()
            matches.append(f"📄 **{note_path.stem}**\n   …{snippet}…")
        if len(matches) >= 10:
            break
    if not matches:
        return f"לא מצאתי שום פתק שמכיל '{query}'."
    return f"מצאתי {len(matches)} התאמות עבור '{query}':\n\n" + "\n\n".join(matches)


TOOL_FUNCTIONS = {
    "save_note": save_note,
    "list_notes": list_notes,
    "read_note": read_note,
    "search_notes": search_notes,
}

TOOLS = [
    {
        "name": "save_note",
        "description": (
            "שומר פתק לקובץ מקומי. השתמש בכלי הזה בכל פעם שהמשתמש "
            "מספר משהו שכדאי לזכור: רעיון, מטלה, פגישה, תובנה, מטרה. "
            "אל תשאל אישור, פשוט שמור."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "כותרת קצרה ותיאורית"},
                "content": {"type": "string", "description": "תוכן הפתק"},
            },
            "required": ["title", "content"],
        },
    },
    {
        "name": "list_notes",
        "description": "מציג רשימה של כל הפתקים השמורים (כותרות בלבד).",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "read_note",
        "description": "קורא את התוכן המלא של פתק ספציפי, לפי שם הקובץ או חלק ממנו.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {"type": "string", "description": "שם קובץ (חלקי מספיק)"},
            },
            "required": ["filename"],
        },
    },
    {
        "name": "search_notes",
        "description": (
            "מחפש מילה או ביטוי בתוכן של כל הפתקים. "
            "השתמש כשהמשתמש שואל 'מה כתבנו על X' או רוצה למצוא מידע ספציפי "
            "ולא יודע באיזה פתק זה. עדיף על list_notes כשמחפשים נושא."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "מילה או ביטוי לחיפוש"},
            },
            "required": ["query"],
        },
    },
]

SYSTEM_PROMPT = """אתה העוזר האישי של אורי, שעובד על בניית עסק AI.

איך להתנהג:
- דבר עברית באופן טבעי, חברותי, וקצר.
- כשאורי מספר משהו שכדאי לזכור (רעיון, החלטה, מטלה, פרט) — שמור אוטומטית עם save_note. אל תשאל אישור.
- כשאורי שואל "מה כתבנו על X" או "מצא לי פתק על Y" — השתמש ב-search_notes (לא ב-list_notes!).
- כשאורי שואל "מה שמרנו" באופן כללי — השתמש ב-list_notes.
- כשאתה מוצא פתק רלוונטי בחיפוש - אם צריך פרטים מלאים, השתמש ב-read_note.
- ענה במשפטים קצרים. אל תכתוב הקדמות ארוכות.
- אם אתה לא בטוח — תשאל שאלה ממוקדת אחת."""


def execute_tool(name: str, tool_input: dict) -> str:
    try:
        return TOOL_FUNCTIONS[name](**tool_input)
    except Exception as e:
        return f"שגיאה בכלי {name}: {e}"


# ============================================================
# מצב סשן
# ============================================================

if "display_messages" not in st.session_state:
    st.session_state.display_messages = []
if "api_messages" not in st.session_state:
    st.session_state.api_messages = []


# ============================================================
# כותרת + סרגל צד
# ============================================================

st.title("🤖 העוזר האישי שלי")
st.caption("Claude Opus 4.7 · Streaming · Adaptive Thinking · 4 כלים")

with st.sidebar:
    st.header("📊 מידע")
    notes_count = len(list(NOTES_DIR.glob("*.md")))
    st.metric("פתקים שמורים", notes_count)
    st.metric("הודעות בשיחה", len(st.session_state.display_messages))

    if st.button("🗑️ נקה שיחה", use_container_width=True):
        st.session_state.display_messages = []
        st.session_state.api_messages = []
        st.rerun()

    st.divider()
    st.subheader("📝 פתקים אחרונים")
    recent_notes = sorted(NOTES_DIR.glob("*.md"), reverse=True)[:8]
    if not recent_notes:
        st.caption("עדיין אין פתקים")
    else:
        for note in recent_notes:
            with st.expander(note.stem[:35]):
                st.markdown(note.read_text(encoding="utf-8"))


# ============================================================
# הצגת הודעות קודמות
# ============================================================

for msg in st.session_state.display_messages:
    avatar = "🤖" if msg["role"] == "assistant" else "👤"
    with st.chat_message(msg["role"], avatar=avatar):
        if msg.get("type") == "tool":
            st.info(f"🔧 השתמשתי בכלי: `{msg['content']}`")
        else:
            st.markdown(msg["content"])


# ============================================================
# קלט משתמש + לולאת הסוכן (עם streaming)
# ============================================================

if user_input := st.chat_input("שאל או ספר לי משהו..."):
    st.session_state.display_messages.append({"role": "user", "content": user_input})
    st.session_state.api_messages.append({"role": "user", "content": user_input})
    with st.chat_message("user", avatar="👤"):
        st.markdown(user_input)

    with st.chat_message("assistant", avatar="🤖"):
        try:
            client = anthropic.Anthropic()
        except Exception as e:
            st.error(f"שגיאה ביצירת חיבור: {e}")
            st.stop()

        # לולאת הסוכן עם streaming
        iteration = 0
        while True:
            iteration += 1
            if iteration > 10:
                st.warning("הגענו ל-10 איטרציות. עוצר.")
                break

            placeholder = st.empty()
            text_so_far = ""

            try:
                with client.messages.stream(
                    model="claude-opus-4-7",
                    max_tokens=4000,
                    thinking={"type": "adaptive"},
                    system=SYSTEM_PROMPT,
                    tools=TOOLS,
                    messages=st.session_state.api_messages,
                ) as stream:
                    for text_chunk in stream.text_stream:
                        text_so_far += text_chunk
                        placeholder.markdown(text_so_far + "▌")

                    # מציג את הטקסט הסופי בלי הסמן
                    if text_so_far:
                        placeholder.markdown(text_so_far)
                    else:
                        # אם לא היה טקסט (רק tool use) - מנקים את ה-placeholder
                        placeholder.empty()

                    response = stream.get_final_message()
            except anthropic.APIError as e:
                st.error(f"שגיאה מ-API: {e}")
                # מסיר את ההודעה האחרונה כדי שאפשר יהיה לנסות שוב
                st.session_state.api_messages.pop()
                st.session_state.display_messages.pop()
                break

            # שומר את התגובה ב-API messages לטיפול בסבב הבא
            st.session_state.api_messages.append(
                {"role": "assistant", "content": response.content}
            )

            if response.stop_reason == "end_turn":
                # שומר את הטקסט להיסטוריית התצוגה
                if text_so_far:
                    st.session_state.display_messages.append(
                        {"role": "assistant", "content": text_so_far}
                    )
                break

            if response.stop_reason == "tool_use":
                # מבצע את הכלים
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        st.info(f"🔧 משתמש בכלי: `{block.name}`")
                        st.session_state.display_messages.append(
                            {
                                "role": "assistant",
                                "type": "tool",
                                "content": block.name,
                            }
                        )
                        result = execute_tool(block.name, block.input)
                        tool_results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": result,
                            }
                        )
                st.session_state.api_messages.append(
                    {"role": "user", "content": tool_results}
                )
                continue

            st.warning(f"סיבת עצירה לא צפויה: {response.stop_reason}")
            break

    st.rerun()
