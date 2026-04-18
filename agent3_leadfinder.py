"""Agent 3: Lead Finder

Finds potential website-building clients in Israel via Google Places (New),
analyzes each with Claude, and outputs a CSV with personalized WhatsApp
messages and website-building prompts per lead.

Usage:
    python agent3_leadfinder.py
"""

import csv
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import requests
from anthropic import Anthropic
from dotenv import load_dotenv

# Windows terminal needs explicit UTF-8 for Hebrew output
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

load_dotenv()

GOOGLE_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY")
MODEL = "claude-haiku-4-5-20251001"

BASE_DIR = Path(__file__).parent
PROMPTS_DIR = BASE_DIR / "prompts"
OUTPUT_DIR = BASE_DIR / "output"

PLACES_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
PLACES_FIELD_MASK = (
    "places.displayName,places.formattedAddress,"
    "places.nationalPhoneNumber,places.internationalPhoneNumber,"
    "places.websiteUri,places.rating,places.userRatingCount,"
    "places.primaryTypeDisplayName,places.businessStatus"
)

FETCH_TIMEOUT = 5
MAX_HTML_CHARS = 4000


def load_prompt(name: str) -> str:
    return (PROMPTS_DIR / name).read_text(encoding="utf-8")


def search_businesses(business_type: str, location: str, count: int) -> list[dict]:
    query = f"{business_type} ב{location}" if location else business_type
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_KEY,
        "X-Goog-FieldMask": PLACES_FIELD_MASK,
    }
    body = {
        "textQuery": query,
        "maxResultCount": min(count, 20),
        "languageCode": "he",
        "regionCode": "IL",
    }
    r = requests.post(PLACES_SEARCH_URL, headers=headers, json=body, timeout=15)
    if r.status_code != 200:
        raise RuntimeError(f"Google Places error {r.status_code}: {r.text[:400]}")
    places = r.json().get("places", [])
    return [normalize_place(p) for p in places]


def normalize_place(p: dict) -> dict:
    return {
        "name": p.get("displayName", {}).get("text", ""),
        "category": p.get("primaryTypeDisplayName", {}).get("text", ""),
        "address": p.get("formattedAddress", ""),
        "phone": p.get("nationalPhoneNumber") or p.get("internationalPhoneNumber", ""),
        "website_url": p.get("websiteUri", ""),
        "rating": p.get("rating", ""),
        "review_count": p.get("userRatingCount", 0),
        "business_status": p.get("businessStatus", ""),
    }


def fetch_website(url: str) -> str | None:
    if not url:
        return None
    try:
        r = requests.get(
            url,
            timeout=FETCH_TIMEOUT,
            headers={"User-Agent": "Mozilla/5.0 (compatible; LeadFinder/1.0)"},
            allow_redirects=True,
        )
        if r.status_code != 200:
            return None
        return r.text[:MAX_HTML_CHARS]
    except requests.RequestException:
        return None


def claude_call(client: Anthropic, prompt: str, max_tokens: int = 1024) -> str:
    for attempt in range(2):
        try:
            resp = client.messages.create(
                model=MODEL,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            return resp.content[0].text.strip()
        except Exception as e:
            if attempt == 0:
                time.sleep(2)
                continue
            raise RuntimeError(f"Claude API failed twice: {e}")


def analyze_business(client: Anthropic, business: dict, html: str | None) -> dict:
    template = load_prompt("analyze_prompt.txt")
    prompt = template.format(
        name=business["name"],
        category=business["category"] or "עסק",
        address=business["address"],
        phone=business["phone"] or "לא זמין",
        rating=business["rating"] or "ללא דירוג",
        review_count=business["review_count"],
        has_website="כן" if business["website_url"] else "לא",
        website_url=business["website_url"] or "אין",
        html_snippet=html if html else "[לא נטען אתר]",
    )
    raw = claude_call(client, prompt, max_tokens=500)
    return parse_json(raw, fallback={"score": 0, "explanation": "שגיאה בניתוח"})


def generate_message(client: Anthropic, business: dict, analysis: dict) -> str:
    template = load_prompt("message_prompt.txt")
    prompt = template.format(
        name=business["name"],
        category=business["category"] or "עסק",
        has_website="כן" if business["website_url"] else "לא",
        website_url=business["website_url"] or "אין",
        score=analysis["score"],
        explanation=analysis["explanation"],
    )
    return claude_call(client, prompt, max_tokens=400)


def generate_website_prompt(client: Anthropic, business: dict) -> str:
    template = load_prompt("website_prompt.txt")
    prompt = template.format(
        name=business["name"],
        category=business["category"] or "עסק",
        address=business["address"],
        phone=business["phone"] or "לא זמין",
        rating=business["rating"] or "ללא דירוג",
        review_count=business["review_count"],
        website_url=business["website_url"] or "אין",
    )
    return claude_call(client, prompt, max_tokens=1200)


def parse_json(raw: str, fallback: dict) -> dict:
    cleaned = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return fallback


def save_to_csv(results: list[dict], category: str) -> Path:
    OUTPUT_DIR.mkdir(exist_ok=True)
    safe_cat = re.sub(r"[^\w\u0590-\u05FF]+", "_", category).strip("_") or "leads"
    date_str = datetime.now().strftime("%Y-%m-%d_%H%M")
    path = OUTPUT_DIR / f"leads_{date_str}_{safe_cat}.csv"
    fieldnames = [
        "name", "category", "phone", "address", "website_url",
        "rating", "review_count", "score", "explanation",
        "whatsapp_message", "website_build_prompt",
    ]
    # utf-8-sig adds BOM so Excel opens Hebrew correctly
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in results:
            writer.writerow({k: row.get(k, "") for k in fieldnames})
    return path


def prompt_user() -> tuple[str, str, int]:
    print("=" * 60)
    print("🔍 Lead Finder — מציאת לקוחות פוטנציאליים")
    print("=" * 60)
    business_type = input("איזה סוג עסק לחפש? (לדוגמה: מוסכים): ").strip()
    location = input("באיזה אזור? (לדוגמה: תל אביב, ריק=כל הארץ): ").strip()
    count_raw = input("כמה תוצאות? (ברירת מחדל: 10): ").strip() or "10"
    try:
        count = int(count_raw)
    except ValueError:
        count = 10
    count = max(1, min(count, 20))
    return business_type, location, count


def validate_env() -> None:
    missing = []
    if not GOOGLE_KEY:
        missing.append("GOOGLE_MAPS_API_KEY")
    if not ANTHROPIC_KEY:
        missing.append("ANTHROPIC_API_KEY")
    if missing:
        print(f"❌ חסרים מפתחות ב-.env: {', '.join(missing)}")
        sys.exit(1)


def main() -> None:
    validate_env()
    business_type, location, count = prompt_user()

    print(f"\n🔎 מחפש '{business_type}' ב{location or 'ישראל'}, עד {count} עסקים...")
    try:
        businesses = search_businesses(business_type, location, count)
    except RuntimeError as e:
        print(f"❌ שגיאה בחיפוש: {e}")
        sys.exit(1)

    if not businesses:
        print("❌ לא נמצאו עסקים. נסה חיפוש אחר או אזור רחב יותר.")
        sys.exit(0)

    print(f"✓ נמצאו {len(businesses)} עסקים. מתחיל ניתוח...\n")

    client = Anthropic(api_key=ANTHROPIC_KEY)
    results = []
    for idx, biz in enumerate(businesses, 1):
        name = biz["name"] or "(ללא שם)"
        print(f"[{idx}/{len(businesses)}] {name}")
        try:
            html = fetch_website(biz["website_url"])
            if biz["website_url"]:
                print(f"  ↳ אתר: {'נטען' if html else 'לא נטען'}")
            analysis = analyze_business(client, biz, html)
            print(f"  ↳ ציון: {analysis['score']}/10")
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
            print(f"  ⚠ שגיאה: {e} — מדלג")
            results.append({
                **biz,
                "score": 0,
                "explanation": f"שגיאה: {e}",
                "whatsapp_message": "",
                "website_build_prompt": "",
            })

    results.sort(key=lambda r: r.get("score", 0) or 0, reverse=True)
    path = save_to_csv(results, business_type)
    print(f"\n✅ הסתיים. נשמר: {path}")
    print(f"   סה\"כ {len(results)} עסקים. ציון ממוצע: "
          f"{sum(r.get('score', 0) or 0 for r in results) / len(results):.1f}")


if __name__ == "__main__":
    main()
