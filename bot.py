import os
import time
import html
import re
import threading
import requests
import pytz
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from deep_translator import GoogleTranslator

# =====================================================================
# 1. YOUR CREDENTIALS & CONFIGURATION (ضع بياناتك هنا)
# =====================================================================
TELEGRAM_BOT_TOKEN = "8334394471:AAF3jOvX_-kMkqlN7low6iwwQKF0TL-Yjas"
TELEGRAM_CHANNEL_ID = "@Forex_News001"
FINNHUB_API_KEY = "d9is8vhr01qvkt7e0pe0d9is8vhr01qvkt7e0peg"

# Affiliate Links (Used for Telegram Buttons)
EXNESS_LINK = "https://www.exness.com"
XM_LINK = "https://www.xm.com"

# How often the bot checks for new market news (in seconds) -> 300 = 5 minutes
CHECK_INTERVAL = 300

# Timezone set strictly to Cairo Time (Egypt)
CAIRO_TZ = pytz.timezone("Africa/Cairo")

# Memory to keep track of sent news articles (prevents duplicates)
SEEN_NEWS_IDS = set()


# =====================================================================
# 2. KEEP-ALIVE WEB SERVER FOR RENDER ($0 FREE PLAN)
# =====================================================================
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"Bot is alive and running 24/7!")

    def log_message(self, format, *args):
        return  # Suppress web server logs in terminal

def start_health_server():
    port = int(os.getenv("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    print(f"🌐 Keep-Alive Web Server running on port {port}...")
    server.serve_forever()


# =====================================================================
# 3. TRANSLATION & CLEANING TOOLS
# =====================================================================
def translate_to_arabic(text):
    """ترجمة النصوص تلقائياً إلى اللغة العربية"""
    if not text:
        return ""
    try:
        translated = GoogleTranslator(source='auto', target='ar').translate(text)
        return translated if translated else text
    except Exception as e:
        print(f"⚠️ خطأ في الترجمة: {e}")
        return text

def clean_html(raw_text):
    """حذف أي أكواد HTML عشوائية من ملخص الخبر"""
    if not raw_text:
        return ""
    cleaner = re.compile('<.*?>')
    text_only = re.sub(cleaner, '', raw_text)
    return text_only


# =====================================================================
# 4. TELEGRAM SENDER WITH INLINE BUTTONS
# =====================================================================
def send_telegram_alert(message_text: str):
    """إرسال الرسالة المترجمة لقناتك في تلجرام مع الأزرار التفاعلية"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    reply_markup = {
        "inline_keyboard": [
            [{"text": "📈 فتح حساب Zero Spread على الذهب", "url": EXNESS_LINK}],
            [{"text": "🎁 استلام بونص 100% على الإيداع", "url": XM_LINK}]
        ]
    }

    payload = {
        "chat_id": TELEGRAM_CHANNEL_ID,
        "text": message_text,
        "parse_mode": "HTML",
        "reply_markup": reply_markup,
        "disable_web_page_preview": False
    }

    try:
        response = requests.post(url, json=payload, timeout=12)
        res_json = response.json()
        if res_json.get("ok"):
            print("✅ Successfully posted translated alert to Telegram!")
        else:
            print(f"❌ Telegram API Error: {res_json.get('description')}")
    except Exception as e:
        print(f"❌ Network error sending to Telegram: {e}")


# =====================================================================
# 5. NEWS FETCHING & FORMATTING
# =====================================================================
def fetch_market_news():
    """جلب الأخبار من Finnhub"""
    url = f"https://finnhub.io/api/v1/news?category=forex&token={FINNHUB_API_KEY}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"⚠️ Finnhub returned status code {response.status_code}")
    except Exception as e:
        print(f"❌ Error fetching news from Finnhub: {e}")
    return []

def format_news_post(article: dict) -> str:
    """ترجمة وتنسيق الخبر بالكامل إلى اللغة العربية"""
    # 1. ترجمة العنوان والعرض
    raw_headline = article.get("headline", "Market Update")
    raw_summary = clean_html(article.get("summary", ""))

    headline = html.escape(translate_to_arabic(raw_headline))
    summary = html.escape(translate_to_arabic(raw_summary))
    
    # اسم المصدر يبقى كما هو باللغة الأصلية بناءً على رغبتك
    source = html.escape(article.get("source", "Financial Feed"))
    article_url = article.get("url", "")

    now_cairo = datetime.now(CAIRO_TZ).strftime("%I:%M %p")

    if len(summary) > 350:
        summary = summary[:347] + "..."

    post_content = (
        f"💡 <b>تحديث أسواق الذهب والفوركس المباشر</b>\n"
        f"⏰ <i>توقيت القاهرة: {now_cairo} 🇪🇬</i>\n\n"
        f"<b>📰 {headline}</b>\n\n"
        f"{summary}\n\n"
        f"🏛️ <b>المصدر:</b> {source}\n"
        f"<a href='{article_url}'>🔗 قراءة الخبر الكامل من المصدر</a>"
    )
    return post_content

def process_news_feed():
    """التحقق من الأخبار الجديدة وترجمتها ونشرها"""
    articles = fetch_market_news()
    if not articles:
        return

    for article in reversed(articles[:5]):
        news_id = str(article.get("id", article.get("url")))

        if news_id in SEEN_NEWS_IDS:
            continue

        SEEN_NEWS_IDS.add(news_id)

        if len(SEEN_NEWS_IDS) > 500:
            SEEN_NEWS_IDS.clear()

        formatted_msg = format_news_post(article)
        send_telegram_alert(formatted_msg)
        time.sleep(3)


# =====================================================================
# 6. MAIN ENGINE LOOP
# =====================================================================
if __name__ == "__main__":
    print("🚀 Starting Telegram Arabic News Bot...")

    server_thread = threading.Thread(target=start_health_server, daemon=True)
    server_thread.start()

    print("🤖 Bot loop initialized. Translating & monitoring market news...")

    while True:
        try:
            process_news_feed()
        except Exception as err:
            print(f"❌ Error in main loop: {err}")

        time.sleep(CHECK_INTERVAL)