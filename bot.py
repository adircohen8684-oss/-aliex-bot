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

CATEGORIES = ["wireless earbuds","smart watch","phone accessories","home gadgets","kitchen tools","fitness equipment","led lights","bluetooth speaker","portable charger","laptop accessories"]
category_index = 0
pending_posts = {}

app = Flask(__name__)

@app.route("/approve/<post_id>")
def approve_post(post_id):
    if post_id in pending_posts:
        post = pending_posts.pop(post_id)
        threading.Thread(target=publish_post, args=(post,)).start()
        return "<html><body style='text-align:center;padding:50px'><h1>✅ הפוסט אושר!</h1></body></html>"
    return "<html><body><h1>❌ לא נמצא</h1></body></html>"

@app.route("/reject/<post_id>")
def reject_post(post_id):
    if post_id in pending_posts:
        pending_posts.pop(post_id)
        return "<html><body style='text-align:center;padding:50px'><h1>🗑️ הפוסט נדחה</h1></body></html>"
    return "<html><body><h1>❌ לא נמצא</h1></body></html>"

@app.route("/health")
def health():
    return {"status": "ok", "pending": len(pending_posts)}

def get_aliexpress_products(keyword, count=3):
    url = "https://aliexpress-datahub.p.rapidapi.com/item_search_2"
    headers = {"X-RapidAPI-Key": RAPIDAPI_KEY, "X-RapidAPI-Host": "aliexpress-datahub.p.rapidapi.com"}
    params = {"q": keyword, "page": "1", "currency": "USD", "locale": "en_US", "region": "US", "sort": "SALE_PRICE_ASC"}
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        data = response.json()
        products = []
        for item in data.get("result", {}).get("resultList", [])[:count]:
            p = item.get("item", {})
            product = {"title": p.get("title", ""), "price": p.get("sku", {}).get("def", {}).get("promotionPrice", ""), "original_price": p.get("sku", {}).get("def", {}).get("price", ""), "image": p.get("image", ""), "product_id": p.get("itemId", ""), "url": f"https://www.aliexpress.com/item/{p.get('itemId', '')}.html"}
            if product["product_id"]:
                products.append(product)
        return products
    except Exception as e:
        print(f"שגיאה: {e}")
        return []

def create_affiliate_link(product_url):
    try:
        response = requests.get("https://aliexpress-datahub.p.rapidapi.com/item_affiliate_link", headers={"X-RapidAPI-Key": RAPIDAPI_KEY, "X-RapidAPI-Host": "aliexpress-datahub.p.rapidapi.com"}, params={"url": product_url, "trackingId": ALIEXPRESS_TRACKING_ID}, timeout=10)
        return response.json().get("result", {}).get("promotionUrl", product_url)
    except:
        return product_url

def generate_marketing_text(product):
    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        message = client.messages.create(model="claude-sonnet-4-20250514", max_tokens=300, messages=[{"role": "user", "content": f"כתוב פוסט שיווקי קצר בעברית לקבוצת פייסבוק עבור: {product['title']}, מחיר: ${product['price']}, מקורי: ${product['original_price']}. 3-4 משפטים, אימוג'י, קריאה לפעולה. ללא לינק."}])
        return message.content[0].text
    except Exception as e:
        return f"🔥 דיל מטורף! {product['title']}\n💰 רק ${product['price']}\n🛒 לחצו על הלינק!"

def send_approval_email(post_id, product, marketing_text, affiliate_link):
    if not SENDER_EMAIL or not SENDER_PASSWORD:
        return​​​​​​​​​​​​​​​​
