import os
import time
import uuid
import schedule
import requests
import anthropic
import sendgrid
from sendgrid.helpers.mail import Mail
from flask import Flask
from datetime import datetime
import threading

RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
FACEBOOK_ACCESS_TOKEN = os.environ.get("FACEBOOK_ACCESS_TOKEN", "")
FACEBOOK_USER_TOKEN = os.environ.get("FACEBOOK_USER_TOKEN", "")
APPROVAL_EMAIL = os.environ.get("APPROVAL_EMAIL", "")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "adircohen8684@gmail.com")
SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY", "")
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
    url = "https://aliexpress-true-api.p.rapidapi.com/api/v3/products"
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
        "ship_to_country": "IL",
        "sort": "SALE_PRICE_ASC"
    }
    try:
        response = requests.get(url, headers=headers, params=params, timeout=15)
        data = response.json()
        items = data.get("products", {}).get("product", [])
        print(f"📦 נמצאו {len(items)} פריטים")
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
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
