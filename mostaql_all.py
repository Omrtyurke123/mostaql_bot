# ============================================================
# مستقل — كل المشاريع الجديدة (بحساب ScraperAPI تاني) -> منصة "فرصة"
#
# بيجيب أحدث صفحات مشاريع مستقل بـ ScraperAPI ويحطها في قسم "مستقل"
# في المنصة، من غير ما يعتمد على جروب التليجرام وبدون فلتر "أقل عروض".
# بيشتغل كل 4 ساعات (شوف .github/workflows/mostaql_all.yml).
#
# متغيرات البيئة:
#   SCRAPER_KEY_2              مفتاح ScraperAPI من الحساب التاني
#   SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
# اختيارية:
#   MOSTAQL_PAGES   عدد الصفحات (افتراضي 3)
#   MOSTAQL_FILTER  "keywords" (افتراضي: برمجة وتصميم بس) أو "none" (كل المشاريع)
#
# اختبار من غير حفظ:   python mostaql_all.py --test
# ============================================================

import os
import re
import sys
import time
import requests
from urllib.parse import quote
from bs4 import BeautifulSoup

SCRAPER_KEY = os.environ.get("SCRAPER_KEY_2")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
PAGES = int(os.environ.get("MOSTAQL_PAGES", "3"))
FILTER = os.environ.get("MOSTAQL_FILTER", "keywords")
TEST = "--test" in sys.argv

BASE_URL = "https://mostaql.com/projects?page={}"
SOURCE_LABEL = "مستقل"

KEYWORDS = [
    # Programming
    "برمج",
    "برمجة",
    "موقع",
    "مواقع",
    "تطبيق",
    "تطبيقات",
    "ويب",
    "سوفت",
    "سوفت وير",
    "سكربت",
    "سكريبت",
    "نظام",
    "منصة",
    "تطوير",

    # Web
    "frontend",
    "front-end",
    "backend",
    "back-end",
    "full stack",
    "fullstack",
    "html",
    "css",
    "javascript",
    "typescript",
    "react",
    "reactjs",
    "next.js",
    "nextjs",
    "vue",
    "angular",
    "node",
    "nodejs",
    "express",
    "php",
    "laravel",
    "wordpress",
    "woocommerce",

    # Mobile
    "أندرويد",
    "اندرويد",
    "android",
    "ios",
    "flutter",
    "dart",
    "react native",

    # Languages
    "python",
    "java",
    "c++",
    "c#",
    ".net",
    "ruby",
    "go",
    "golang",

    # AI / ML
    "ذكاء اصطناعي",
    "ذكاء صناعي",
    "تعلم الآلة",
    "تعلم آلة",
    "machine learning",
    "deep learning",
    "artificial intelligence",
    "ai",
    "ml",
    "tensorflow",
    "pytorch",
    "keras",
    "neural network",
    "شبكات عصبية",
    "نموذج ذكاء اصطناعي",
    "موديل",

    # Data
    "بيانات",
    "داتا",
    "data",
    "data science",
    "علم البيانات",
    "تحليل البيانات",
    "data analysis",
    "data mining",
    "تنقيب البيانات",
    "database",
    "قاعدة بيانات",
    "قواعد بيانات",
    "sql",
    "mysql",
    "postgresql",
    "mongodb",

    # API / Bots
    "api",
    "apis",
    "بوت",
    "بوتات",
    "telegram bot",
    "chatbot",
    "شات بوت",
    "chatgpt",
    "gpt",
    "openai",
    "automation",
    "أتمتة",

    # Scraping
    "سحب",
    "سحب بيانات",
    "scraper",
    "scraping",
    "web scraping",
    "استخراج البيانات",

    # Ecommerce
    "متجر",
    "متجر إلكتروني",
    "ecommerce",
    "e-commerce",

    # Software
    "برمجية",
    "software",
    "برنامج",
    "نظام إدارة",
]

DESIGN_KEYWORDS = [
    "تصميم",
    "تصاميم",
    "جرافيك",
    "جرافكس",
    "graphic",
    "design",
    "شعار",
    "لوجو",
    "logo",
    "هوية بصرية",
    "هوية تجارية",
    "branding",
    "واجهة",
    "ui",
    "ux",
    "ui/ux",
    "تجربة المستخدم",
    "بنر",
    "banner",
    "بوستر",
    "poster",
    "فلاير",
    "flyer",
    "بروشور",
    "brochure",
    "كتالوج",
    "catalog",
    "موشن جرافيك",
    "motion graphic",
    "انفوجراف",
    "انفوجرافيك",
    "infographic",
    "فوتوشوب",
    "photoshop",
    "illustrator",
    "figma",
    "canva",
    "تصميم داخلي",
    "تصميم ثلاثي الابعاد",
    "3d design",
]

def parse_offers(text):

    # بدون عروض
    if "أضف أول عرض" in text:
        return 0

    # مثال:
    # 5 عروض
    # 7 عروض مقدمة

    match = re.search(
        r"(\d+)\s*عروض?",
        text
    )

    if match:
        return int(match.group(1))

    return -1

def parse_price(text):

    # تنظيف المسافات
    text = " ".join(text.split())

    # --------------------------------------------------------
    # دولار
    # --------------------------------------------------------

    patterns = [

        r"\$\s*[\d,]+(?:\s*[-–]\s*\$?\s*[\d,]+)?",

        r"[\d,]+\s*\$\s*(?:[-–]\s*\$?\s*[\d,]+)?",

        r"[\d,]+\s*(?:دولار|دولارًا|دولاراً)"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:
            return match.group(0).strip()


    # --------------------------------------------------------
    # ريال
    # --------------------------------------------------------

    patterns = [

        r"[\d,]+\s*ريال",

        r"[\d,]+\s*ر\.س",

        r"ريال\s*[\d,]+"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:
            return match.group(0).strip()


    # --------------------------------------------------------
    # جنيه مصري
    # --------------------------------------------------------

    patterns = [

        r"[\d,]+\s*جنيه",

        r"[\d,]+\s*ج\.م",

        r"جنيه\s*[\d,]+"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:
            return match.group(0).strip()


    return "غير محددة"

def parse_posted(text):

    # مثال: منذ 3 أيام / منذ ساعة / منذ 20 ساعة
    match = re.search(
        r"منذ\s+(?:\d+\s+)?[^\s\d]+",
        text
    )

    return match.group(0) if match else ""


ALL_KEYWORDS = [k.lower() for k in KEYWORDS + DESIGN_KEYWORDS]


def wanted(title, brief):
    if FILTER == "none":
        return True
    text = (title + " " + brief).lower()
    return any(k in text for k in ALL_KEYWORDS)


def fetch_page(page):
    api_url = (
        "https://api.scraperapi.com/?api_key=" + SCRAPER_KEY
        + "&url=" + quote(BASE_URL.format(page), safe="")
    )
    r = requests.get(api_url, timeout=90)
    r.raise_for_status()
    return r.text


def parse_projects(html):
    soup = BeautifulSoup(html, "lxml")
    rows = soup.select("tr.project-row")
    out = []
    for row in rows:
        a = row.select_one(".card--title h2 a")
        if not a or not a.get("href"):
            continue
        title = a.get_text(" ", strip=True)
        brief_el = row.select_one("p.project__brief")
        brief = brief_el.get_text(" ", strip=True)[:200] if brief_el else ""
        if not wanted(title, brief):
            continue
        offers = -1
        for el in row.select("li.text-muted"):
            v = parse_offers(el.get_text(" ", strip=True))
            if v >= 0:
                offers = v
                break
        row_text = row.get_text(" ", strip=True)
        out.append({
            "title": title,
            "url": a["href"],
            "brief": brief,
            "offers": offers,
            "price": parse_price(row_text),
            "posted": parse_posted(row_text),
        })
    return len(rows), out


def to_row(j):
    lines = [f"🟢 {j['title']}"]
    if j["price"] and j["price"] != "غير محددة":
        lines.append(f"💰 {j['price']}")
    if j["offers"] == 0:
        lines.append("⚡ بدون عروض — كن الأول!")
    elif j["offers"] > 0:
        lines.append(f"👥 {j['offers']} عروض")
    if j["posted"]:
        lines.append(f"🕒 {j['posted']}")
    if j["brief"]:
        lines.append(j["brief"])
    lines.append(j["url"])  # الرابط في آخر سطر: الواجهة بتخفيه وتخليه قابل للضغط
    return {
        "feed_type": "instant",
        "source": SOURCE_LABEL,
        "raw_text": "\n".join(lines),
        "external_id": j["url"],
    }


def push(rows):
    if not rows or TEST:
        return
    r = requests.post(
        f"{SUPABASE_URL}/rest/v1/jobs",
        headers={
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates",
        },
        params={"on_conflict": "feed_type,source,external_id"},
        json=rows,
        timeout=30,
    )
    if not r.ok:
        raise SystemExit(f"❌ فشل الحفظ في Supabase: {r.status_code} {r.text[:300]}")


def main():
    if not SCRAPER_KEY:
        raise SystemExit("❌ ناقص SCRAPER_KEY_2")
    if not TEST and not (SUPABASE_URL and SUPABASE_KEY):
        raise SystemExit("❌ ناقص SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY")

    seen, jobs, raw_total, ok_pages, last_err = set(), [], 0, 0, None
    for page in range(1, PAGES + 1):
        try:
            raw, found = parse_projects(fetch_page(page))
            ok_pages += 1
            raw_total += raw
            for j in found:
                if j["url"] not in seen:
                    seen.add(j["url"])
                    jobs.append(j)
            print(f"📄 صفحة {page}: {raw} مشروع، المطابق: {len(found)}")
        except Exception as e:
            last_err = e
            print(f"⚠️ فشلت صفحة {page}: {e}")
        time.sleep(2)

    # فشل كامل = لازم الـ workflow يفشل عشان تعرف
    if ok_pages == 0:
        raise SystemExit(f"❌ فشلت كل الصفحات. آخر خطأ: {last_err}")
    if raw_total == 0:
        raise SystemExit("❌ الصفحات اتجابت بس مفيش مشاريع اتقرت (الموقع ممكن يكون حظر الطلب أو غيّر شكله)")

    rows = [to_row(j) for j in jobs]
    if TEST and rows:
        print("\n--- مثال لأول مشروع ---\n" + rows[0]["raw_text"])
    push(rows)
    print(f"✅ {len(rows)} مشروع" + (" (اختبار — مفيش حفظ)" if TEST else " اتحفظوا في المنصة"))


if __name__ == "__main__":
    main()
