# ============================================================
# 🤖 MOSTAQL JOBS BOT - Google Colab
# Programming + AI/ML
# Keyword Filtering + Budget + Offers < 10
# ============================================================

# ============================================================
# 1) تثبيت المكتبات
# ============================================================

import os
import subprocess
import sys

subprocess.run([
    sys.executable, "-m", "pip", "install", "-q",
    "requests", "beautifulsoup4", "lxml"
])


# ============================================================
# 2) الإعدادات
# ============================================================

# المفاتيح بتيجي من GitHub Secrets (متغيرات بيئة) — مش مكتوبة في الملف
TOKEN = os.environ["TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]
SCRAPER_KEY = os.environ["SCRAPER_KEY"]


MAX_OFFERS = 10
TOP_N = 10
PAGES = 5

BASE_URL = "https://mostaql.com/projects?page={}"


# ============================================================
# 3) الكلمات المفتاحية
# ============================================================

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


# ============================================================
# 4) Database
# ============================================================

import re
import time
import sqlite3
import requests

from urllib.parse import quote
from bs4 import BeautifulSoup


db = sqlite3.connect(
    "sent_jobs.db",
    check_same_thread=False
)

db.execute("""
    CREATE TABLE IF NOT EXISTS sent (
        url TEXT PRIMARY KEY
    )
""")

db.commit()


# ============================================================
# 5) Fetch page
# ============================================================

def fetch_page(page):

    target = BASE_URL.format(page)

    api_url = (
        "https://api.scraperapi.com/"
        "?api_key=" + SCRAPER_KEY +
        "&url=" + quote(target, safe="")
    )

    response = requests.get(
        api_url,
        timeout=90
    )

    response.raise_for_status()

    return response.text


# ============================================================
# 6) Parse offers
# ============================================================

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


# ============================================================
# 7) Parse budget
# ============================================================

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


# ============================================================
# 8) Keyword matching
# ============================================================

def matches_keywords(title, brief):

    text = (
        title + " " + brief
    ).lower()

    return any(
        keyword.lower() in text
        for keyword in KEYWORDS
    )


# ============================================================
# 9) Parse projects
# ============================================================

def parse_rows(html):

    jobs = []

    soup = BeautifulSoup(
        html,
        "lxml"
    )

    rows = soup.select(
        "tr.project-row"
    )

    for row in rows:

        # ----------------------------------------------------
        # Title
        # ----------------------------------------------------

        a = row.select_one(
            ".card--title h2 a"
        )

        if not a:
            continue

        title = a.get_text(
            " ",
            strip=True
        )

        link = a.get(
            "href"
        )

        if not link:
            continue


        # ----------------------------------------------------
        # Description
        # ----------------------------------------------------

        brief_el = row.select_one(
            "p.project__brief"
        )

        brief = ""

        if brief_el:

            brief = brief_el.get_text(
                " ",
                strip=True
            )[:200]


        # ----------------------------------------------------
        # Keyword filter
        # ----------------------------------------------------

        if not matches_keywords(
            title,
            brief
        ):
            continue


        # ----------------------------------------------------
        # Offers
        # ----------------------------------------------------

        offers = -1

        for element in row.select(
            "li.text-muted"
        ):

            value = parse_offers(
                element.get_text(
                    " ",
                    strip=True
                )
            )

            if value >= 0:

                offers = value
                break


        # لا نأخذ مشروع لا نعرف عروضه
        if offers < 0:
            continue


        # أقل من 10 عروض
        if offers >= MAX_OFFERS:
            continue


        # ----------------------------------------------------
        # Budget
        # ----------------------------------------------------

        # نأخذ كل النص الموجود داخل المشروع
        row_text = row.get_text(
            " ",
            strip=True
        )

        price = parse_price(
            row_text
        )


        # ----------------------------------------------------
        # Add project
        # ----------------------------------------------------

        jobs.append({

            "title": title,

            "url": link,

            "brief": brief,

            "offers": offers,

            "price": price
        })


    return jobs


# ============================================================
# 10) Fetch all jobs
# ============================================================

def fetch_jobs():

    all_jobs = []

    seen_urls = set()

    for page in range(
        1,
        PAGES + 1
    ):

        try:

            print(
                f"📄 جاري فحص الصفحة {page}..."
            )

            html = fetch_page(
                page
            )

            rows = parse_rows(
                html
            )

            for job in rows:

                if job["url"] in seen_urls:
                    continue

                seen_urls.add(
                    job["url"]
                )

                all_jobs.append(
                    job
                )

            print(
                f"✅ الصفحة {page} تم فحصها"
            )

        except Exception as e:

            print(
                f"⚠️ فشل الصفحة {page}: {e}"
            )

        time.sleep(2)


    # ترتيب حسب أقل عدد عروض
    all_jobs.sort(
        key=lambda x: x["offers"]
    )

    return all_jobs


# ============================================================
# 11) Telegram
# ============================================================

def send_telegram(text):

    try:

        response = requests.post(

            f"https://api.telegram.org/bot{TOKEN}/sendMessage",

            json={

                "chat_id": CHAT_ID,

                "text": text,

                "parse_mode": "HTML",

                "link_preview_options": {
                    "is_disabled": True
                }
            },

            timeout=30
        )

        return response.ok

    except Exception as e:

        print(
            f"⚠️ فشل إرسال Telegram: {e}"
        )

        return False


# ============================================================
# 12) Run round
# ============================================================

def run_round():

    print()
    print("=" * 60)

    print(
        "🔄 جاري البحث عن مشاريع البرمجة والذكاء الاصطناعي..."
    )

    print("=" * 60)


    # Fetch
    jobs = fetch_jobs()


    # Already sent
    sent = {
        row[0]
        for row in db.execute(
            "SELECT url FROM sent"
        )
    }


    # New only
    fresh = [

        job

        for job in jobs

        if job["url"] not in sent

    ]


    # Top 10
    fresh = fresh[:TOP_N]


    if not fresh:

        print(
            "ℹ️ لا توجد مشاريع جديدة مناسبة حالياً."
        )

        return


    # Header
    send_telegram(

        "🤖 <b>أفضل فرص البرمجة والذكاء الاصطناعي</b>\n\n"
        "🎯 مشاريع مطابقة للكلمات المفتاحية\n"
        "⚡ أقل من 10 عروض\n"
        "📊 مرتبة حسب الأقل منافسة"
    )


    success = 0


    for i, job in enumerate(
        fresh,
        1
    ):


        # ----------------------------------------------------
        # Offers - يظهر في Telegram فقط
        # ----------------------------------------------------

        if job["offers"] == 0:

            offers_text = (
                "⚡ <b>بدون أي عروض — كن الأول!</b>"
            )

        else:

            offers_text = (
                f"👥 <b>العروض المقدمة:</b> "
                f"{job['offers']}"
            )


        # ----------------------------------------------------
        # Telegram message
        # ----------------------------------------------------

        message = (

            f"<b>{i}. 💼 {job['title']}</b>\n\n"

            f"📝 {job['brief']}\n\n"

            f"💰 <b>الميزانية:</b> "
            f"{job['price']}\n"

            f"{offers_text}\n\n"

            f"🔗 {job['url']}"
        )


        # Send
        if send_telegram(
            message
        ):

            db.execute(
                "INSERT OR IGNORE INTO sent VALUES (?)",
                (job["url"],)
            )

            db.commit()

            success += 1


        time.sleep(2)


    print()
    print(
        f"✅ تم إرسال {success} مشروع جديد."
    )


# ============================================================
# 13) Start
# ============================================================

# على GitHub Actions: جولة واحدة في كل تشغيل،
# والتكرار (كل 4 ساعات) بيتحكم فيه ملف الـ workflow

run_round()
