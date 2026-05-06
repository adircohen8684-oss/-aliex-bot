import os
import time
import uuid
import schedule
import requests
import anthropic
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from flask import Flask
from datetime import datetime
import threading

RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
FACEBOOK_ACCESS_TOKEN = os.environ.get("FACEBOOK_ACCESS_TOKEN", "")
FACEBOOK_USER_TOKEN = os.environ.get("FACEBOOK_USER_TOKEN", "")
APPROVAL_EMAIL = os.environ.get("APPROVAL_EMAIL", "")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "")
SENDER_PASSWORD = os.environ.get("SENDER_PASSWORD", "")
BOT_URL = os.environ.get("BOT_URL", "http://localhost:5000")
FACEBOOK_GROUPS = os.environ.get("FACEBOOK_GROUPS", "").split(",")

CATEGORIES = [
    "wireless earbuds", "smart watch", "phone accessories",
    "home gadgets", "kitchen tools", "fitness equipment",
    "led lights", "bluetooth speaker", "portable charger", "laptop accessories"
]

category_index = 0
pending_posts = {}
bot_started = False

app = Flask(__name__)

@app.route("/approve/<post_id>")
def approve_post(post_id):
    if post_id in pending_posts:
        post = pending_posts.pop(post_id)
        threading.Thread(target=publish_to_all_groups, args=(post,)).start()
        return "<html><body style='text-align:center;padding:50px;background:#f0fff0'><h1>✅ הפוסט אושר ויפורסם בכל הקבוצות!</h1></body></html>"
    return "<html><body><h1>❌ לא נמצא</h1></body></html>"

@app.route("/reject/<post_id>")
def reject_post(post_id):
    if post_id in pending_posts:
        pending_posts.pop(post_id)
        return "<html><body style='text-align:center;padding:50px;background:#fff0f0'><h1>🗑️ הפוסט נדחה</h1></body></html>"
    return "<html><body><h1>❌ לא נמצא</h1></body></html>"

@app.route("/health")
def health():
    return {"status": "ok", "pending": len(pending_posts)}

def get_aliexpress_products(keyword, count=3):
    url = "https://aliexpress-true-api.p.rapidapi.com/api/v3/get-products"
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": "aliexpress-true-api.p.rapidapi.com"
    }
    params = {
        "keywords": keyword,
        "page_no": "1",
        "page_size": str(count),
        "target_currency": "USD",
        "target_language": "EN",
        "country": "IL",
        "sort": "SALE_PRICE_ASC"
    }
    try:
        response = requests.get(url, headers=headers, params=params, timeout=15)
        data = response.json()
        print(f"🔍 API Response: {data}")
        items = data if isinstance(data, list) else []
        products = []
        for item in items[:count]:
            product = {
                "title": item.get("product_title", ""),
                "price": item.get("target_sale_price", item.get("sale_price", "")),
                "original_price": item.get("target_original_price", item.get("original_price", "")),
                "image": item.get("product_main_image_url", ""),
                "product_id": item.get("product_id", ""),
                "url": item.get("promotion_link", item.get("product_detail_url", ""))
            }
            if product["title"]:
                products.append(product)
        return products
    except Exception as e:
        print(f"שגיאה בשליפת מוצרים: {e}")
        return []

def generate_marketing_text(product):
    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=300,
            messages=[{"role": "user", "content": f"כתוב פוסט שיווקי קצר בעברית לקבוצת פייסבוק עבור: {product['title']}, מחיר: ${product['price']}, מקורי: ${product['original_price']}. 3-4 משפטים, אימוג'י, קריאה לפעולה. ללא לינק."}]
        )
        return message.content[0].text
    except Exception as e:
        return f"🔥 דיל מטורף! {product['title']}\n💰 רק ${product['price']}\n🛒 לחצו על הלינק!"

def create_affiliate_link(product_url):
    return product_url

def send_approval_email(post_id, product, marketing_text, affiliate_link):
    if not SENDER_EMAIL or not SENDER_PASSWORD:
        return False
    try:
        approve_url = f"{BOT_URL}/approve/{post_id}"
        reject_url = f"{BOT_URL}/reject/{post_id}"
        groups_list = "<br>".join([f"• קבוצה {g}" for g in FACEBOOK_GROUPS if g])
        html = f"""
        <html><body style="font-family:Arial;max-width:600px;margin:0 auto;padding:20px">
        <h2 style="color:#1877f2">🤖 פוסט חדש ממתין לאישור</h2>
        <div style="background:#f5f5f5;padding:15px;border-radius:10px">
        <h3>{product['title'][:80]}</h3>
        <p>💰 ${product['price']} (מקורי: ${product['original_price']})</p>
        <img src="{product['image']}" style="max-width:300px"/>
        </div>
        <div style="background:#fff3cd;padding:15px;border-radius:10px;margin:20px 0;direction:rtl">
        <p style="white-space:pre-line">{marketing_text}</p>
        </div>
        <div style="background:#e8f4e8;padding:10px;border-radius:10px;margin:10px 0">
        <p><strong>יפורסם בקבוצות:</strong><br>{groups_list}</p>
        </div>
        <div style="text-align:center;margin:30px 0">
        <a href="{approve_url}" style="background:#28a745;color:white;padding:15px 40px;border-radius:8px;text-decoration:none;font-size:18px">✅ אשר ופרסם</a>
        &nbsp;&nbsp;&nbsp;
        <a href="{reject_url}" style="background:#dc3545;color:white;padding:15px 40px;border-radius:8px;text-decoration:none;font-size:18px">❌ דחה</a>
        </div>
        </body></html>
        """
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"🛒 פוסט לאישור - {product['title'][:40]}"
        msg["From"] = SENDER_EMAIL
        msg["To"] = APPROVAL_EMAIL
        msg.attach(MIMEText(html, "html"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, APPROVAL_EMAIL, msg.as_string())
        print(f"📧 מייל אישור נשלח")
        return True
    except Exception as e:
        print(f"שגיאת מייל: {e}")
        return False

def publish_to_group(group_id, text, image_url, token):
    try:
        group_id = group_id.strip()
        if not group_id:
            return
        url = f"https://graph.facebook.com/{group_id}/photos"
        data = {
            "message": text,
            "url": image_url,
            "access_token": token
        }
        response = requests.post(url, data=data)
        result = response.json()
        if "id" in result:
            print(f"✅ פורסם בקבוצה {group_id}")
        else:
            print(f"❌ שגיאה בקבוצה {group_id}: {result}")
    except Exception as e:
        print(f"שגיאה בפרסום לקבוצה {group_id}: {e}")

def publish_to_all_groups(post_data):
    product = post_data["product"]
    marketing_text = post_data["marketing_text"]
    affiliate_link = post_data["affiliate_link"]
    token = FACEBOOK_USER_TOKEN or FACEBOOK_ACCESS_TOKEN
    full_text = f"{marketing_text}\n\n🛒 קנה עכשיו: {affiliate_link}"
    for group_id in FACEBOOK_GROUPS:
        if group_id.strip():
            publish_to_group(group_id, full_text, product.get("image", ""), token)
            time.sleep(5)

def run_agent():
    global category_index
    print(f"\n🤖 הסוכן פועל - {datetime.now().strftime('%H:%M %d/%m/%Y')}")
    keyword = CATEGORIES[category_index % len(CATEGORIES)]
    category_index += 1
    print(f"🔍 מחפש: {keyword}")
    products = get_aliexpress_products(keyword, count=3)
    if not products:
        print("❌ לא נמצאו מוצרים")
        return
    print(f"✅ נמצאו {len(products)} מוצרים")
    for i, product in enumerate(products, 1):
        affiliate_link = create_affiliate_link(product["url"])
        marketing_text = generate_marketing_text(product)
        post_id = str(uuid.uuid4())[:8]
        post_data = {"product": product, "marketing_text": marketing_text, "affiliate_link": affiliate_link}
        if send_approval_email(post_id, product, marketing_text, affiliate_link):
            pending_posts[post_id] = post_data
            print(f"📧 ממתין לאישור (ID: {post_id})")
        else:
            publish_to_all_groups(post_data)
        if i < len(products):
            time.sleep(30)

def run_scheduler():
    schedule.every(2).hours.do(run_agent)
    while True:
        schedule.run_pending()
        time.sleep(60)

def start_bot():
    global bot_started
    if not bot_started:
        bot_started = True
        print("🚀 AliX Hunters Bot מתחיל")
        threading.Thread(target=run_agent, daemon=True).start()
        threading.Thread(target=run_scheduler, daemon=True).start()

if __name__ == "__main__":
    start_bot()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
else:
    start_bot()
