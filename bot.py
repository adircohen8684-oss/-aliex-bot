 import os
import time
import uuid
import schedule
import requests
import anthropic
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from flask import Flask, request as flask_request
from datetime import datetime
import threading

# ============================================================
# הגדרות - נטענות מ Environment Variables (בטוח!)
# ============================================================
RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY", "")
ALIEXPRESS_TRACKING_ID = os.environ.get("ALIEXPRESS_TRACKING_ID", "default")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
FACEBOOK_APP_ID = os.environ.get("FACEBOOK_APP_ID", "")
FACEBOOK_APP_SECRET = os.environ.get("FACEBOOK_APP_SECRET", "")
FACEBOOK_GROUP_ID = os.environ.get("FACEBOOK_GROUP_ID", "")
FACEBOOK_ACCESS_TOKEN = os.environ.get("FACEBOOK_ACCESS_TOKEN", "")

APPROVAL_EMAIL = os.environ.get("APPROVAL_EMAIL", "")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "")
SENDER_PASSWORD = os.environ.get("SENDER_PASSWORD", "")
BOT_URL = os.environ.get("BOT_URL", "http://localhost:5000")

# קטגוריות
CATEGORIES = [
    "wireless earbuds", "smart watch", "phone accessories",
    "home gadgets", "kitchen tools", "fitness equipment",
    "led lights", "bluetooth speaker", "portable charger", "laptop accessories"
]

category_index = 0
pending_posts = {}

# ============================================================
# Flask - שרת לאישורים
# ============================================================
app = Flask(__name__)

@app.route("/approve/<post_id>")
def approve_post(post_id):
    if post_id in pending_posts:
        post = pending_posts.pop(post_id)
        threading.Thread(target=publish_post, args=(post,)).start()
        return """
        <html><body style="font-family:Arial; text-align:center; padding:50px; background:#f0fff0;">
        <h1>✅ הפוסט אושר!</h1>
        <p>הפוסט יפורסם ברגעים אלה בקבוצת הפייסבוק.</p>
        </body></html>
        """
    return "<html><body><h1>❌ פוסט לא נמצא או כבר טופל</h1></body></html>"

@app.route("/reject/<post_id>")
def reject_post(post_id):
    if post_id in pending_posts:
        pending_posts.pop(post_id)
        return """
        <html><body style="font-family:Arial; text-align:center; padding:50px; background:#fff0f0;">
        <h1>🗑️ הפוסט נדחה</h1>
        <p>הפוסט לא יפורסם.</p>
        </body></html>
        """
    return "<html><body><h1>❌ פוסט לא נמצא או כבר טופל</h1></body></html>"

@app.route("/health")
def health():
    return {"status": "ok", "pending": len(pending_posts)}

# ============================================================
# שלב 1: שליפת מוצרים
# ============================================================
def get_aliexpress_products(keyword, count=3):
    url = "https://aliexpress-datahub.p.rapidapi.com/item_search_2"
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": "aliexpress-datahub.p.rapidapi.com"
    }
    params = {
        "q": keyword, "page": "1", "currency": "USD",
        "locale": "en_US", "region": "US", "sort": "SALE_PRICE_ASC"
    }
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        data = response.json()
        products = []
        items = data.get("result", {}).get("resultList", [])[:count]
        for item in items:
            p = item.get("item", {})
            product = {
                "title": p.get("title", ""),
                "price": p.get("sku", {}).get("def", {}).get("promotionPrice", ""),
                "original_price": p.get("sku", {}).get("def", {}).get("price", ""),
                "image": p.get("image", ""),
                "product_id": p.get("itemId", ""),
                "url": f"https://www.aliexpress.com/item/{p.get('itemId', '')}.html"
            }
            if product["product_id"]:
                products.append(product)
        return products
    except Exception as e:
        print(f"שגיאה בשליפת מוצרים: {e}")
        return []

# ============================================================
# שלב 2: לינק שותפים
# ============================================================
def create_affiliate_link(product_url):
    url = "https://aliexpress-datahub.p.rapidapi.com/item_affiliate_link"
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": "aliexpress-datahub.p.rapidapi.com"
    }
    params = {"url": product_url, "trackingId": ALIEXPRESS_TRACKING_ID}
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        data = response.json()
        return data.get("result", {}).get("promotionUrl", product_url)
    except Exception as e:
        print(f"שגיאה ביצירת לינק: {e}")
        return product_url

# ============================================================
# שלב 3: טקסט שיווקי עם Claude
# ============================================================
def generate_marketing_text(product):
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    prompt = f"""אתה מומחה שיווק דיגיטלי ישראלי. כתוב פוסט שיווקי קצר ומושך בעברית לקבוצת פייסבוק עבור המוצר הבא:

שם המוצר: {product['title']}
מחיר: ${product['price']}
מחיר מקורי: ${product['original_price']}

הנחיות:
- כתוב בעברית בלבד
- 3-4 משפטים קצרים ומושכים
- הדגש את המחיר והחיסכון
- הוסף אימוג'י רלוונטיים
- סיים עם קריאה לפעולה
- אל תכלול את הלינק
- סגנון קבוצת "ציידי הדילים"

כתוב רק את הטקסט, ללא הסברים נוספים."""
    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}]
        )
        return message.content[0].text
    except Exception as e:
        print(f"שגיאה ביצירת טקסט: {e}")
        return f"🔥 דיל מטורף! {product['title']}\n💰 רק ${product['price']}\n🛒 לחצו על הלינק לרכישה!"

# ============================================================
# שלב 4: שליחת מייל לאישור
# ============================================================
def send_approval_email(post_id, product, marketing_text, affiliate_link):
    if not SENDER_EMAIL or not SENDER_PASSWORD:
        print("⚠️ אין פרטי מייל - מפרסם ישירות")
        return False

    approve_url = f"{BOT_URL}/approve/{post_id}"
    reject_url = f"{BOT_URL}/reject/{post_id}"

    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #1877f2;">🤖 פוסט חדש ממתין לאישור</h2>
        <div style="background: #f5f5f5; padding: 15px; border-radius: 10px; margin: 20px 0;">
            <h3>📦 {product['title'][:80]}</h3>
            <p>💰 מחיר: <strong>${product['price']}</strong> (מקורי: ${product['original_price']})</p>
            <img src="{product['image']}" style="max-width:300px; border-radius:8px;" />
        </div>
        <div style="background: #fff3cd; padding: 15px; border-radius: 10px; margin: 20px 0; direction: rtl;">
            <h3>📝 טקסט הפוסט:</h3>
            <p style="white-space: pre-line;">{marketing_text}</p>
            <p>🔗 <a href="{affiliate_link}">לינק השותפים</a></p>
        </div>
        <div style="text-align: center; margin: 30px 0;">
            <a href="{approve_url}" style="background:#28a745; color:white; padding:15px 40px;
               border-radius:8px; text-decoration:none; font-size:18px; margin: 10px;">
               ✅ אשר ופרסם
            </a>
            &nbsp;&nbsp;&nbsp;
            <a href="{reject_url}" style="background:#dc3545; color:white; padding:15px 40px;
               border-radius:8px; text-decoration:none; font-size:18px; margin: 10px;">
               ❌ דחה
            </a>
        </div>
        <p style="color: #888; font-size: 12px; text-align: center;">
            נשלח אוטומטית מבוט AliX Hunters | {datetime.now().strftime('%d/%m/%Y %H:%M')}
        </p>
    </body>
    </html>
    """

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"🛒 פוסט חדש לאישור - {product['title'][:40]}..."
        msg["From"] = SENDER_EMAIL
        msg["To"] = APPROVAL_EMAIL
        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, APPROVAL_EMAIL, msg.as_string())

        print(f"📧 מייל אישור נשלח ל-{APPROVAL_EMAIL}")
        return True
    except Exception as e:
        print(f"שגיאה בשליחת מייל: {e}")
        return False

# ============================================================
# פרסום לפייסבוק
# ============================================================
def get_facebook_token():
    url = "https://graph.facebook.com/oauth/access_token"
    params = {
        "client_id": FACEBOOK_APP_ID,
        "client_secret": FACEBOOK_APP_SECRET,
        "grant_type": "client_credentials"
    }
    try:
        response = requests.get(url, params=params)
        return response.json().get("access_token", "")
    except Exception as e:
        print(f"שגיאה בקבלת טוקן: {e}")
        return ""

def publish_post(post_data):
    product = post_data["product"]
    marketing_text = post_data["marketing_text"]
    affiliate_link = post_data["affiliate_link"]

    token = FACEBOOK_ACCESS_TOKEN or get_facebook_token()
    full_text = f"{marketing_text}\n\n🛒 קנה עכשיו: {affiliate_link}"

    url = f"https://graph.facebook.com/{FACEBOOK_GROUP_ID}/photos"
    data = {
        "message": full_text,
        "url": product.get("image", ""),
        "access_token": token
    }

    try:
        response = requests.post(url, data=data)
        result = response.json()
        if "id" in result:
            print(f"✅ פורסם בהצלחה: {result['id']}")
        else:
            print(f"❌ שגיאה בפרסום: {result}")
    except Exception as e:
        print(f"שגיאה בפרסום: {e}")

# ============================================================
# הסוכן הראשי
# ============================================================
def run_agent():
    global category_index

    print(f"\n{'='*50}")
    print(f"🤖 הסוכן פועל - {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}")
    print(f"{'='*50}")

    keyword = CATEGORIES[category_index % len(CATEGORIES)]
    category_index += 1
    print(f"🔍 מחפש מוצרים: {keyword}")

    products = get_aliexpress_products(keyword, count=3)

    if not products:
        print("❌ לא נמצאו מוצרים")
        return

    print(f"✅ נמצאו {len(products)} מוצרים")

    for i, product in enumerate(products, 1):
        print(f"\n📦 מעבד מוצר {i}/{len(products)}: {product['title'][:50]}...")

        affiliate_link = create_affiliate_link(product["url"])
        marketing_text = generate_marketing_text(product)

        post_id = str(uuid.uuid4())[:8]
        post_data = {
            "product": product,
            "marketing_text": marketing_text,
            "affiliate_link": affiliate_link
        }

        email_sent = send_approval_email(post_id, product, marketing_text, affiliate_link)

        if email_sent:
            pending_posts[post_id] = post_data
            print(f"📧 ממתין לאישורך במייל (ID: {post_id})")
        else:
            publish_post(post_data)

        if i < len(products):
            print("⏳ ממתין 30 שניות...")
            time.sleep(30)

    print(f"\n✅ סבב הושלם!")

# ============================================================
# הפעלה
# ============================================================
def run_scheduler():
    schedule.every(2).hours.do(run_agent)
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    print("🚀 מתחיל סוכן AliX Hunters עם אישור מייל")
    print("="*50)

    threading.Thread(target=run_agent).start()
    threading.Thread(target=run_scheduler, daemon=True).start()

    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
