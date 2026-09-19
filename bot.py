# -*- coding: utf-8 -*-
# ============================================================
# MOSTAQL JOBS BOT
# نسخة تعمل "جولة واحدة" في كل تشغيل (مناسبة لـ GitHub Actions)
# الحالة محفوظة في sent.json بدل قاعدة بيانات مؤقتة
# ============================================================

import os
import re
import sys
import json
import time
import random
import requests

from pathlib import Path
from urllib.parse import quote
from bs4 import BeautifulSoup


# ============================================================
# 1) الإعدادات (من متغيرات البيئة - لا تكتب المفاتيح هنا)
# ============================================================

TOKEN = os.environ.get("TELEGRAM_TOKEN", "").strip()
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
SCRAPER_KEY = os.environ.get("SCRAPER_KEY", "").strip()  # اختياري

MAX_OFFERS = int(os.environ.get("MAX_OFFERS", "10"))
TOP_N = int(os.environ.get("TOP_N", "10"))
PAGES = int(os.environ.get("PAGES", "3"))

BASE_URL = "https://mostaql.com/projects?page={}"

STATE_FILE = Path(__file__).parent / "sent.json"
MAX_STATE_SIZE = 800  # أقصى عدد روابط محفوظة

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ar,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


if not TOKEN or not CHAT_ID:
    print("❌ لم يتم ضبط TELEGRAM_TOKEN أو TELEGRAM_CHAT_ID")
    sys.exit(1)


# ============================================================
# 2) الكلمات المفتاحية
# ============================================================

KEYWORDS = [
    # برمجة عام
    "برمج", "برمجة", "موقع", "مواقع", "تطبيق", "تطبيقات", "ويب",
    "سوفت", "سوفت وير", "سكربت", "سكريبت", "نظام", "منصة", "تطوير",
    "برمجية", "برنامج", "نظام إدارة",

    # ويب
    "frontend", "front-end", "backend", "back-end", "full stack",
    "fullstack", "html", "css", "javascript", "typescript", "react",
    "reactjs", "next.js", "nextjs", "vue", "angular", "node", "nodejs",
    "express", "php", "laravel", "wordpress", "woocommerce",

    # موبايل
    "أندرويد", "اندرويد", "android", "ios", "flutter", "dart",
    "react native",

    # لغات
    "python", "java", "c++", "c#", ".net", "ruby", "golang",

    # ذكاء اصطناعي
    "ذكاء اصطناعي", "ذكاء صناعي", "تعلم الآلة", "تعلم آلة",
    "machine learning", "deep learning", "artificial intelligence",
    "tensorflow", "pytorch", "keras", "neural network", "شبكات عصبية",
    "نموذج ذكاء اصطناعي",

    # بيانات
    "بيانات", "داتا", "data science", "علم البيانات", "تحليل البيانات",
    "data analysis", "data mining", "تنقيب البيانات", "database",
    "قاعدة بيانات", "قواعد بيانات", "sql", "mysql", "postgresql",
    "mongodb",

    # API / بوتات
    "api", "apis", "بوت", "بوتات", "telegram bot", "chatbot",
    "شات بوت", "chatgpt", "openai", "automation", "أتمتة",

    # سحب بيانات
    "سحب بيانات", "scraper", "scraping", "web scraping",
    "استخراج البيانات",

    # متاجر
    "متجر", "متجر إلكتروني", "ecommerce", "e-commerce",
]

# كلمات قصيرة نطابقها ككلمة كاملة فقط (حتى لا تُطابق داخل كلمات أخرى)
SHORT_KEYWORDS = ["ai", "ml", "go", "data"]


# ============================================================
# 3) الحالة (الروابط المُرسلة سابقاً)
# ============================================================

def load_state():
    if not STATE_FILE.exists():
        return []
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception as e:
        print(f"⚠️ تعذّر قراءة sent.json: {e}")
        return []


def save_state(urls):
    trimmed = urls[-MAX_STATE_SIZE:]
    STATE_FILE.write_text(
        json.dumps(trimmed, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )


# ============================================================
# 4) جلب الصفحة (محاولة مباشرة ثم ScraperAPI عند الفشل)
# ============================================================

def fetch_page(page):
    target = BASE_URL.format(page)

    # (أ) محاولة مباشرة - مجانية ولا تستهلك رصيد ScraperAPI
    try:
        response = requests.get(target, headers=HEADERS, timeout=45)
        if response.ok and "project-row" in response.text:
            return response.text
        print(f"ℹ️ الجلب المباشر لم ينجح (كود {response.status_code})")
    except Exception as e:
        print(f"ℹ️ الجلب المباشر فشل: {e}")

    # (ب) ScraperAPI كخطة بديلة
    if not SCRAPER_KEY:
        raise RuntimeError("الجلب المباشر فشل ولا يوجد SCRAPER_KEY")

    api_url = (
        "https://api.scraperapi.com/?api_key="
        + SCRAPER_KEY
        + "&url="
        + quote(target, safe="")
    )
    response = requests.get(api_url, timeout=90)
    response.raise_for_status()
    return response.text


# ============================================================
# 5) تحليل العروض والميزانية
# ============================================================

def parse_offers(text):
    if "أضف أول عرض" in text:
        return 0

    match = re.search(r"(\d+)\s*عروض?", text)
    if match:
        return int(match.group(1))

    return -1


PRICE_PATTERNS = [
    r"\$\s*[\d,]+(?:\s*[-–]\s*\$?\s*[\d,]+)?",
    r"[\d,]+\s*\$\s*(?:[-–]\s*\$?\s*[\d,]+)?",
    r"[\d,]+\s*(?:دولار|دولارًا|دولاراً)",
    r"[\d,]+\s*ريال",
    r"[\d,]+\s*ر\.س",
    r"ريال\s*[\d,]+",
    r"[\d,]+\s*جنيه",
    r"[\d,]+\s*ج\.م",
    r"جنيه\s*[\d,]+",
]


def parse_price(text):
    text = " ".join(text.split())
    for pattern in PRICE_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(0).strip()
    return "غير محددة"


def matches_keywords(title, brief):
    text = (title + " " + brief).lower()

    for keyword in KEYWORDS:
        if keyword.lower() in text:
            return True

    for keyword in SHORT_KEYWORDS:
        if re.search(r"(?<!\w)" + re.escape(keyword) + r"(?!\w)", text):
            return True

    return False


# ============================================================
# 6) استخراج المشاريع
# ============================================================

def parse_rows(html):
    jobs = []
    soup = BeautifulSoup(html, "lxml")

    for row in soup.select("tr.project-row"):

        a = row.select_one(".card--title h2 a")
        if not a:
            continue

        title = a.get_text(" ", strip=True)
        link = a.get("href")
        if not link:
            continue

        if link.startswith("/"):
            link = "https://mostaql.com" + link

        brief_el = row.select_one("p.project__brief")
        brief = brief_el.get_text(" ", strip=True)[:200] if brief_el else ""

        if not matches_keywords(title, brief):
            continue

        offers = -1
        for element in row.select("li.text-muted"):
            value = parse_offers(element.get_text(" ", strip=True))
            if value >= 0:
                offers = value
                break

        if offers < 0 or offers >= MAX_OFFERS:
            continue

        price = parse_price(row.get_text(" ", strip=True))

        jobs.append({
            "title": title,
            "url": link,
            "brief": brief,
            "offers": offers,
            "price": price,
        })

    return jobs


def fetch_jobs():
    all_jobs = []
    seen_urls = set()

    for page in range(1, PAGES + 1):
        try:
            print(f"📄 جاري فحص الصفحة {page}...")
            rows = parse_rows(fetch_page(page))

            for job in rows:
                if job["url"] in seen_urls:
                    continue
                seen_urls.add(job["url"])
                all_jobs.append(job)

            print(f"✅ الصفحة {page}: {len(rows)} مشروع مطابق")

        except Exception as e:
            print(f"⚠️ فشل الصفحة {page}: {e}")

        time.sleep(random.uniform(2, 4))

    all_jobs.sort(key=lambda x: x["offers"])
    return all_jobs


# ============================================================
# 7) تليجرام
# ============================================================

def send_telegram(text):
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            json={
                "chat_id": CHAT_ID,
                "text": text,
                "parse_mode": "HTML",
                "link_preview_options": {"is_disabled": True},
            },
            timeout=30,
        )

        if not response.ok:
            print(f"⚠️ تليجرام: {response.text[:200]}")

        return response.ok

    except Exception as e:
        print(f"⚠️ فشل إرسال تليجرام: {e}")
        return False


# ============================================================
# 8) الجولة
# ============================================================

def run_round():
    print("=" * 55)
    print("🔄 جاري البحث عن مشاريع البرمجة والذكاء الاصطناعي...")
    print("=" * 55)

    jobs = fetch_jobs()

    sent = load_state()
    sent_set = set(sent)

    fresh = [j for j in jobs if j["url"] not in sent_set][:TOP_N]

    if not fresh:
        print("ℹ️ لا توجد مشاريع جديدة مناسبة حالياً.")
        return

    send_telegram(
        "🤖 <b>أفضل فرص البرمجة والذكاء الاصطناعي</b>\n\n"
        "🎯 مشاريع مطابقة للكلمات المفتاحية\n"
        f"⚡ أقل من {MAX_OFFERS} عروض\n"
        "📊 مرتبة حسب الأقل منافسة"
    )

    success = 0

    for i, job in enumerate(fresh, 1):

        if job["offers"] == 0:
            offers_text = "⚡ <b>بدون أي عروض — كن الأول!</b>"
        else:
            offers_text = f"👥 <b>العروض المقدمة:</b> {job['offers']}"

        message = (
            f"<b>{i}. 💼 {job['title']}</b>\n\n"
            f"📝 {job['brief']}\n\n"
            f"💰 <b>الميزانية:</b> {job['price']}\n"
            f"{offers_text}\n\n"
            f"🔗 {job['url']}"
        )

        if send_telegram(message):
            sent.append(job["url"])
            success += 1

        time.sleep(2)

    save_state(sent)
    print(f"\n✅ تم إرسال {success} مشروع جديد.")


if __name__ == "__main__":

    # عدد الجولات داخل التشغيل الواحد والفاصل بينها بالدقائق
    rounds = int(os.environ.get("ROUNDS", "1"))
    gap = float(os.environ.get("ROUND_GAP_MIN", "15"))

    for index in range(1, rounds + 1):

        if rounds > 1:
            print(f"\n🔁 الجولة {index} من {rounds}")

        try:
            run_round()
        except Exception as e:
            print(f"❌ خطأ في الجولة: {e}")

        if index < rounds:
            print(f"⏳ انتظار {gap} دقيقة...")
            time.sleep(gap * 60)
