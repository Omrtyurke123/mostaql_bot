# ============================================================
# 🤖 MOSTAQL JOBS BOT - Google Colab
# Programming + AI/ML
# Keyword Filtering + Budget + Offers < 10
# Sources: Mostaql + Nafezly + Kafiil
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

# ---- المصادر الإضافية (بتتقرا مباشرة بدون ScraperAPI عشان الكريديت) ----
ENABLE_MOSTAQL = True
ENABLE_NAFEZLY = True
ENABLE_KAFIIL = True

NAFEZLY_PAGES = 2
KAFIIL_PAGES = 2

NAFEZLY_URL = "https://nafezly.com/projects?specialize=development&page={}"
KAFIIL_URL = (
    "https://kafiil.com/projects/"
    "programming-web-and-application-development-2?page={}"
)

ACTIVE_SITES = [
    name
    for name, on in (
        ("مستقل", ENABLE_MOSTAQL),
        ("نفذلي", ENABLE_NAFEZLY),
        ("كفيل", ENABLE_KAFIIL),
    )
    if on
]

# عداد طلبات ScraperAPI في الجولة (لمتابعة الكريديت)
SCRAPER_CALLS = 0


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

from html import escape as h_escape
from urllib.parse import quote, urljoin
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

db.execute("""
    CREATE TABLE IF NOT EXISTS meta (
        key TEXT PRIMARY KEY,
        value TEXT
    )
""")

db.commit()


# ============================================================
# 5) Fetch page
# ============================================================

def fetch_page(page):

    global SCRAPER_CALLS
    SCRAPER_CALLS += 1

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

    parse_rows.raw = len(rows)

    print(
        f"   🔎 عدد المشاريع الخام في الصفحة: {len(rows)}"
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

            "price": price,

            "site": "مستقل",

            "posted": parse_posted(row_text)
        })


    return jobs


# ============================================================
# 10) Fetch all jobs
# ============================================================

def fetch_mostaql_jobs():

    all_jobs = []

    seen_urls = set()

    ok_pages = 0
    total_raw = 0
    last_error = None

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

            ok_pages += 1
            total_raw += getattr(parse_rows, "raw", 0)

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
                f"✅ الصفحة {page} تم فحصها — "
                f"المطابق للفلاتر: {len(rows)}"
            )

        except Exception as e:

            last_error = e

            print(
                f"⚠️ فشل الصفحة {page}: {e}"
            )

        time.sleep(2)


    # فشل كامل → تنبيه بدل ما يعدّي بصمت
    if ok_pages == 0:
        raise RuntimeError(
            f"فشلت كل الصفحات. آخر خطأ: {last_error}"
        )

    if total_raw == 0:
        raise RuntimeError(
            "الصفحات اتجابت لكن مفيش مشاريع اتقرت "
            "(الموقع ممكن يكون حظر الطلب أو غيّر شكله)"
        )

    return all_jobs


# ============================================================
# 10b) مصادر إضافية: نفذلي + كفيل
# ============================================================

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "ar,en;q=0.8",
}

PROJECT_ID_RE = re.compile(r"/project/(\d+)")

STATUS_WORDS = (
    "مفتوح", "مكتمل", "قيد التنفيذ", "تحت التنفيذ",
    "منتهى", "منتهي", "مغلق", "ملغي", "خاص",
    "بإنتظار الموافقة",
)

CLOSED_WORDS = (
    "مكتمل", "قيد التنفيذ", "تحت التنفيذ",
    "منتهى", "منتهي", "مغلق", "ملغي",
)


def fetch_direct(url, retries=1):

    last_error = None

    for attempt in range(retries + 1):

        try:

            response = requests.get(
                url,
                headers=BROWSER_HEADERS,
                timeout=30
            )

            response.raise_for_status()

            return response.content.decode(
                "utf-8",
                errors="replace"
            )

        except Exception as e:

            last_error = e
            time.sleep(3)

    raise last_error


def parse_posted(text):

    # مثال: منذ 3 أيام / منذ ساعة / منذ 20 ساعة
    match = re.search(
        r"منذ\s+(?:\d+\s+)?[^\s\d]+",
        text
    )

    return match.group(0) if match else ""


def parse_budget_usd(text):

    text = " ".join(text.split())

    # نطاق بالدولار: $250 - $500  أو  10 - 25 $
    for m in re.finditer(
        r"\$?\s*(\d[\d,.]*)\s*\$?\s*-\s*\$?\s*(\d[\d,.]*)\s*\$?",
        text
    ):
        if "$" in m.group(0):
            return f"${m.group(1)} - ${m.group(2)}"

    m = re.search(
        r"\$\s*(\d[\d,.]*)|(\d[\d,.]*)\s*\$",
        text
    )

    if m:
        return f"${m.group(1) or m.group(2)}"

    return "غير محددة"


def is_meta_fragment(text):

    text = " ".join(text.split())

    if text in STATUS_WORDS:
        return True

    if re.match(r"^منذ\s", text):
        return True

    if re.match(r"^\d+\s*عروض?$", text):
        return True

    if re.match(r"^\d+\s*(?:أيام|يوم|ساعة|ساعات)$", text):
        return True

    if "$" in text and len(text) < 30:
        return True

    return False


def project_ids_in(node):

    ids = set()

    for x in node.select("a[href]"):

        m = PROJECT_ID_RE.search(x["href"])

        if m:
            ids.add(m.group(1))

    return ids


def scrape_cards(html, base_url, label, status_mode):
    """
    قارئ عام لصفحات قوائم المشاريع (نفذلي / كفيل).
    بيعتمد على روابط /project/<id> وبيطلع منها كارت المشروع،
    فمش مربوط بأسماء كلاسات CSS معينة.
    status_mode:
      "prefix" → الحالة أول كلمة في عنوان الرابط (كفيل)
      "suffix" → الحالة نص جوه الكارت (نفذلي)
    بيرجّع (المشاريع المطابقة للفلاتر, عدد المشاريع الخام)
    """

    soup = BeautifulSoup(html, "lxml")

    # أول رابط له نص لكل مشروع
    anchors = {}

    for a in soup.select("a[href]"):

        m = PROJECT_ID_RE.search(a["href"])

        if not m:
            continue

        text = a.get_text(" ", strip=True)

        if not text:
            continue

        pid = m.group(1)

        if pid not in anchors:
            anchors[pid] = (a, text)

    jobs = []

    for pid, (a, raw_title) in anchors.items():

        # ---- نطلع لأكبر عنصر فيه المشروع ده لوحده ----
        card = a

        while (
            card.parent is not None
            and getattr(card.parent, "name", None)
            not in (None, "[document]", "body", "html")
        ):

            if project_ids_in(card.parent) - {pid}:
                break

            card = card.parent

        fragments = list(card.stripped_strings)

        card_text = " ".join(fragments)

        if len(card_text) > 3000:
            continue

        # ---- العنوان + الحالة ----
        title = raw_title
        status = ""

        if status_mode == "prefix":

            m = re.match(
                r"^(" + "|".join(STATUS_WORDS) + r")\s+(.+)$",
                raw_title
            )

            if m:
                status, title = m.group(1), m.group(2)

        # ---- الوصف ----
        # الأول: أول h3/h4/p جوه الكارت مش عنوان ومش بيانات جانبية
        desc = ""

        for el in card.find_all(["h3", "h4", "p"]):

            t = el.get_text(" ", strip=True)

            if (
                t
                and t not in (raw_title, title)
                and not is_meta_fragment(t)
            ):
                desc = t
                break

        # لو مفيش: أطول جزء نصي مش بيانات جانبية
        if not desc:

            candidates = [
                f for f in fragments
                if f not in (raw_title, title)
                and not is_meta_fragment(f)
            ]

            desc = max(candidates, key=len) if candidates else ""

        # باقي بيانات الكارت (بدون العنوان والوصف)
        rest = card_text.replace(raw_title, " ", 1)

        if desc:
            rest = rest.replace(desc, " ", 1)

        rest = " ".join(rest.split())

        # ---- الحالة: لازم مشروع مفتوح ----
        if status_mode == "prefix":

            if status and status != "مفتوح":
                continue

        else:

            found = [
                f for f in fragments
                if f in STATUS_WORDS
            ]

            if not found:

                m = re.search(
                    r"(" + "|".join(STATUS_WORDS) + r")\s*$",
                    rest
                )

                if m:
                    found = [m.group(1)]

            if any(f in CLOSED_WORDS for f in found):
                continue

        # ---- الكلمات المفتاحية ----
        if not matches_keywords(title, desc):
            continue

        # ---- العروض ----
        offers = parse_offers(rest)

        if offers < 0 and (
            "لا توجد عروض" in rest
            or "بدون عروض" in rest
        ):
            offers = 0

        if offers < 0:
            continue

        if offers >= MAX_OFFERS:
            continue

        jobs.append({

            "title": title,

            "url": urljoin(base_url, a["href"]),

            "brief": desc[:200],

            "offers": offers,

            "price": parse_budget_usd(rest),

            "site": label,

            "posted": parse_posted(rest)
        })

    return jobs, len(anchors)


def fetch_site_jobs(label, url_tpl, pages, status_mode):

    all_jobs = []

    seen_urls = set()

    ok_pages = 0
    total_raw = 0
    last_error = None

    for page in range(1, pages + 1):

        try:

            print(
                f"📄 [{label}] جاري فحص الصفحة {page}..."
            )

            url = url_tpl.format(page)

            html = fetch_direct(url)

            jobs, raw = scrape_cards(
                html,
                url,
                label,
                status_mode
            )

            ok_pages += 1
            total_raw += raw

            print(
                f"   🔎 [{label}] مشاريع خام: {raw} — "
                f"المطابق للفلاتر: {len(jobs)}"
            )

            for job in jobs:

                if job["url"] in seen_urls:
                    continue

                seen_urls.add(job["url"])

                all_jobs.append(job)

        except Exception as e:

            last_error = e

            print(
                f"⚠️ [{label}] فشل الصفحة {page}: {e}"
            )

        time.sleep(2)

    if ok_pages == 0:
        raise RuntimeError(
            f"فشلت كل الصفحات. آخر خطأ: {last_error}"
        )

    if total_raw == 0:
        raise RuntimeError(
            "الصفحات اتجابت لكن مفيش مشاريع اتقرت "
            "(الموقع ممكن يكون حظر الطلب أو غيّر شكله)"
        )

    return all_jobs


def notify_failure(site, reason):
    """
    تنبيه على تليجرام لما مصدر يفشل — مرة واحدة كل 24 ساعة لكل مصدر،
    ومن غير ما يسرّب أي مفاتيح.
    """

    reason = re.sub(
        r"api_key=[^&\s]+",
        "api_key=***",
        str(reason)
    )

    for secret in (SCRAPER_KEY, TOKEN):

        if secret:
            reason = reason.replace(secret, "***")

    reason = reason[:250]

    key = f"alert:{site}"

    row = db.execute(
        "SELECT value FROM meta WHERE key = ?",
        (key,)
    ).fetchone()

    now = time.time()

    if row and now - float(row[0]) < 24 * 3600:
        return

    sent = send_telegram(
        f"⚠️ <b>تنبيه: مشكلة في مصدر {h_escape(site)}</b>\n\n"
        f"{h_escape(reason, quote=False)}\n\n"
        "(التنبيه ده بيتكرر مرة كل 24 ساعة كحد أقصى)"
    )

    if sent:

        db.execute(
            "INSERT OR REPLACE INTO meta VALUES (?, ?)",
            (key, str(now))
        )

        db.commit()


# ============================================================
# 10c) Fetch all jobs (كل المصادر)
# ============================================================

def fetch_jobs():

    sources = []

    if ENABLE_MOSTAQL:
        sources.append((
            "مستقل",
            fetch_mostaql_jobs
        ))

    if ENABLE_NAFEZLY:
        sources.append((
            "نفذلي",
            lambda: fetch_site_jobs(
                "نفذلي", NAFEZLY_URL, NAFEZLY_PAGES, "suffix"
            )
        ))

    if ENABLE_KAFIIL:
        sources.append((
            "كفيل",
            lambda: fetch_site_jobs(
                "كفيل", KAFIIL_URL, KAFIIL_PAGES, "prefix"
            )
        ))

    all_jobs = []

    for label, fn in sources:

        try:

            all_jobs.extend(fn())

        except Exception as e:

            print(
                f"⚠️ [{label}] فشل المصدر: {e}"
            )

            notify_failure(label, e)

    # ترتيب حسب أقل عدد عروض
    all_jobs.sort(
        key=lambda x: x["offers"]
    )

    print(
        f"📡 طلبات ScraperAPI في الجولة دي: {SCRAPER_CALLS}"
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

        if not response.ok:
            print(
                f"⚠️ Telegram رفض الرسالة: "
                f"{response.status_code} {response.text[:200]}"
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
        "📊 مرتبة حسب الأقل منافسة\n"
        f"🌐 المصادر: {' • '.join(ACTIVE_SITES)}"
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

        # الهروب من رموز HTML عشان تليجرام مايرفضش الرسالة
        # لو العنوان فيه & أو < (مثال: C++ & Python)
        source_line = (
            f"🌐 <b>المصدر:</b> {h_escape(job['site'], quote=False)}"
        )

        if job.get("posted"):
            source_line += (
                f" • 🕒 {h_escape(job['posted'], quote=False)}"
            )

        message = (

            f"<b>{i}. 💼 {h_escape(job['title'], quote=False)}</b>\n\n"

            f"📝 {h_escape(job['brief'], quote=False)}\n\n"

            f"💰 <b>الميزانية:</b> "
            f"{h_escape(job['price'], quote=False)}\n"

            f"{offers_text}\n"

            f"{source_line}\n\n"

            f"🔗 {h_escape(job['url'], quote=False)}"
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
