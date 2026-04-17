"""
Agent #1 — עוזר אישי בעברית
============================
הסוכן הזה יכול לדבר איתך בעברית, לשמור פתקים אוטומטית,
ולהיזכר במה שדיברתם בעבר.

זה הסוכן הראשון שלך — מטרתו ללמד אותך:
1. איך לדבר עם Claude API
2. איך מוסיפים "כלים" (Tools) לסוכן
3. איך עובד לולאת הסוכן (Agent Loop)
"""

import sys
from pathlib import Path
from datetime import datetime

import anthropic
from dotenv import load_dotenv

# מכריח את ה-console להשתמש ב-UTF-8 (פותר בעיות עברית/אימוג'י ב-Windows)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stdin.reconfigure(encoding="utf-8", errors="replace")

# טוען את ה-API key מקובץ .env
load_dotenv()

# תיקייה שבה נשמרים פתקים
NOTES_DIR = Path(__file__).parent / "notes"
NOTES_DIR.mkdir(exist_ok=True)


# ============================================================
# הכלים שהסוכן יכול להשתמש בהם
# ============================================================

def save_note(title: str, content: str) -> str:
    """שומר פתק לקובץ מקומי."""
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    safe_title = "".join(c for c in title if c.isalnum() or c in " -_").strip()[:40]
    filename = f"{timestamp}_{safe_title or 'note'}.md"
    filepath = NOTES_DIR / filename
    filepath.write_text(f"# {title}\n\n{content}\n", encoding="utf-8")
    return f"נשמר בהצלחה: {filename}"


def list_notes() -> str:
    """מציג רשימה של כל הפתקים השמורים."""
    notes = sorted(NOTES_DIR.glob("*.md"), reverse=True)
    if not notes:
        return "אין פתקים שמורים עדיין."
    return "פתקים שמורים (החדשים ראשונים):\n" + "\n".join(
        f"- {n.stem}" for n in notes[:20]
    )


def read_note(filename: str) -> str:
    """קורא תוכן של פתק ספציפי."""
    name = filename if filename.endswith(".md") else f"{filename}.md"
    filepath = NOTES_DIR / name
    if not filepath.exists():
        matches = list(NOTES_DIR.glob(f"*{filename}*"))
        if not matches:
            return f"לא מצאתי פתק בשם: {filename}"
        filepath = matches[0]
    return filepath.read_text(encoding="utf-8")


# מילון שמתרגם שם של כלי לפונקציה האמיתית
TOOL_FUNCTIONS = {
    "save_note": save_note,
    "list_notes": list_notes,
    "read_note": read_note,
}

# הגדרות הכלים בפורמט שClaude מבין
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
                "title": {
                    "type": "string",
                    "description": "כותרת קצרה ותיאורית לפתק (5-10 מילים)",
                },
                "content": {
                    "type": "string",
                    "description": "התוכן המלא של הפתק",
                },
            },
            "required": ["title", "content"],
        },
    },
    {
        "name": "list_notes",
        "description": (
            "מציג רשימה של כל הפתקים השמורים. השתמש כשהמשתמש שואל "
            "מה שמרת או רוצה לראות סקירה."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "read_note",
        "description": (
            "קורא את התוכן המלא של פתק ספציפי. השתמש אחרי list_notes "
            "כדי להציג פרטים, או כשהמשתמש שואל על נושא ספציפי."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "שם הקובץ של הפתק (חלקי מספיק)",
                },
            },
            "required": ["filename"],
        },
    },
]


def execute_tool(name: str, tool_input: dict) -> str:
    """מריץ כלי ומחזיר את התוצאה כמחרוזת."""
    try:
        func = TOOL_FUNCTIONS[name]
        return func(**tool_input)
    except Exception as e:
        return f"שגיאה בהרצת הכלי {name}: {e}"


# ============================================================
# הוראות המערכת — כך הסוכן מתנהג
# ============================================================

SYSTEM_PROMPT = """אתה העוזר האישי של אורי, שעובד על בניית עסק AI.

איך להתנהג:
- דבר עברית באופן טבעי, חברותי, וקצר.
- כשאורי מספר משהו שכדאי לזכור (רעיון, החלטה, מטלה, פרט) — שמור אוטומטית עם save_note. אל תשאל אישור.
- כשאורי שואל "מה שמרנו" או "מה דיברנו על X" — השתמש ב-list_notes ואז ב-read_note.
- ענה במשפטים קצרים. אל תכתוב הקדמות ארוכות.
- אם אתה לא בטוח — תשאל שאלה ממוקדת אחת."""


# ============================================================
# הלולאה הראשית — כאן הקסם קורה
# ============================================================

def chat():
    """לולאת השיחה הראשית עם הסוכן."""
    try:
        client = anthropic.Anthropic()
    except Exception as e:
        print(f"❌ שגיאה ביצירת חיבור: {e}")
        print("   ודא שה-API key נמצא בקובץ .env")
        sys.exit(1)

    messages = []  # היסטוריית השיחה

    print("\n" + "=" * 55)
    print("🤖 העוזר האישי שלך מוכן!")
    print("   הקלד 'יציאה' או Ctrl+C כדי לסיים")
    print("=" * 55)

    while True:
        try:
            user_input = input("\n👤 אתה: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\n👋 להתראות!")
            return

        if not user_input:
            continue
        if user_input.lower() in ("יציאה", "exit", "quit", "bye"):
            print("👋 להתראות!")
            return

        # מוסיף את ההודעה של המשתמש להיסטוריה
        messages.append({"role": "user", "content": user_input})

        # לולאת הסוכן: ממשיכים עד ש-Claude מסיים את התור
        while True:
            try:
                response = client.messages.create(
                    model="claude-opus-4-7",
                    max_tokens=4000,
                    system=SYSTEM_PROMPT,
                    tools=TOOLS,
                    messages=messages,
                )
            except anthropic.APIError as e:
                print(f"\n❌ שגיאה מ-API: {e}")
                # מסיר את ההודעה האחרונה כדי שאפשר יהיה לנסות שוב
                messages.pop()
                break

            # מוסיף את התגובה של Claude להיסטוריה
            messages.append({"role": "assistant", "content": response.content})

            # אם Claude סיים — מציג את התשובה ויוצא מהלולאה
            if response.stop_reason == "end_turn":
                for block in response.content:
                    if block.type == "text":
                        print(f"\n🤖 עוזר: {block.text}")
                break

            # אם Claude רוצה להשתמש בכלי — מריץ אותו ומחזיר תוצאה
            if response.stop_reason == "tool_use":
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        print(f"   [🔧 כלי: {block.name}]")
                        result = execute_tool(block.name, block.input)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        })
                messages.append({"role": "user", "content": tool_results})
                continue

            # סיבת עצירה לא צפויה — יוצא מהלולאה
            print(f"   [⚠️ סיבת עצירה: {response.stop_reason}]")
            break


if __name__ == "__main__":
    chat()
