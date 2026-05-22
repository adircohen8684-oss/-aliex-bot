import os
import re
import requests
import anthropic
from flask import Flask, request, jsonify, render_template_string
 
app = Flask(__name__)
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
 
def get_product_data(url):
    result = {"image": None, "price": None, "sales": None, "rating": None}
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        session = requests.Session()
        r = session.get(url, headers=headers, timeout=15, allow_redirects=True)
        html = r.text
 
        img_patterns = [
            r'property="og:image"\s+content="([^"]+)"',
            r'content="([^"]+)"\s+property="og:image"',
            r'"image"\s*:\s*"(https://ae\d+\.alicdn\.com[^"]+)"',
        ]
        for pattern in img_patterns:
            match = re.search(pattern, html)
            if match:
                img = match.group(1)
                if img.startswith("http"):
                    result["image"] = img
                    break
 
        price_patterns = [
            r'"minActivityAmount"\s*:\s*\{"value"\s*:\s*"([^"]+)"',
            r'"price"\s*:\s*\{"minPrice"\s*:\s*"([^"]+)"',
            r'class="[^"]*price[^"]*"[^>]*>\s*US\s*\$\s*([\d.]+)',
            r'"salePrice"\s*:\s*"([^"]+)"',
            r'og:price:amount["\s]+content="([^"]+)"',
        ]
        for pattern in price_patterns:
            match = re.search(pattern, html)
            if match:
                result["price"] = match.group(1)
                break
 
        sales_patterns = [
            r'"formatTradeCount"\s*:\s*"([^"]+)"',
            r'"tradeCount"\s*:\s*(\d+)',
            r'([\d,]+)\s+sold',
            r'"soldOut"\s*:\s*false[^}]*"orders"\s*:\s*(\d+)',
        ]
        for pattern in sales_patterns:
            match = re.search(pattern, html)
            if match:
                result["sales"] = match.group(1)
                break
 
        rating_patterns = [
            r'"averageStar"\s*:\s*"([^"]+)"',
            r'"starRating"\s*:\s*"([^"]+)"',
            r'"ratingScore"\s*:\s*"([^"]+)"',
            r'"rating"\s*:\s*([\d.]+)',
        ]
        for pattern in rating_patterns:
            match = re.search(pattern, html)
            if match:
                result["rating"] = match.group(1)
                break
 
    except Exception as e:
        print("Product data fetch error:", e)
    return result
 
HTML = (
    "<!DOCTYPE html>"
    "<html lang='he' dir='rtl'>"
    "<head>"
    "<meta charset='UTF-8'>"
    "<meta name='viewport' content='width=device-width, initial-scale=1.0'>"
    "<title>יוצר פוסטים חכם</title>"
    "<style>"
    "* { margin:0; padding:0; box-sizing:border-box; }"
    "body { font-family: Arial, sans-serif; background:#111; color:#fff; padding:20px; }"
    ".container { max-width:620px; margin:auto; }"
    "h2 { text-align:center; margin-bottom:20px; font-size:1.4rem; color:#f7931e; }"
    "label { display:block; margin-bottom:6px; color:#aaa; font-size:0.9rem; }"
    "input, textarea { width:100%; padding:12px; margin-bottom:16px; background:#1c1c1c; border:1px solid #333; border-radius:8px; color:#fff; font-size:1rem; font-family:Arial; }"
    "textarea { min-height:80px; resize:vertical; }"
    ".btn-main { width:100%; padding:14px; font-size:1rem; font-weight:bold; background:linear-gradient(135deg,#ff6b35,#f7931e); border:none; border-radius:8px; color:#fff; cursor:pointer; }"
    ".btn-main:disabled { opacity:0.5; }"
    ".section { margin-top:24px; }"
    ".section h3 { font-size:1rem; color:#f7931e; margin-bottom:8px; }"
    ".box { background:#1c1c1c; border:1px solid #333; border-radius:8px; padding:14px; white-space:pre-wrap; line-height:1.6; font-size:0.95rem; min-height:80px; }"
    ".copy-btn { margin-top:8px; width:100%; padding:10px; background:#28a745; border:none; border-radius:8px; color:#fff; font-size:0.95rem; cursor:pointer; font-family:Arial; }"
    ".loading { text-align:center; color:#f7931e; padding:20px; display:none; }"
    ".product-img { width:100%; max-width:300px; border-radius:8px; margin:10px auto 16px; display:block; }"
    ".product-stats { background:#1c1c1c; border:1px solid #333; border-radius:8px; padding:12px; margin-bottom:16px; display:none; }"
    ".stat { display:inline-block; margin-left:16px; font-size:0.9rem; color:#aaa; }"
    ".stat span { color:#f7931e; font-weight:bold; }"
    "</style>"
    "</head>"
    "<body>"
    "<div class='container'>"
    "<h2>✍️ יוצר פוסטים חכם</h2>"
    "<label>קישור שותפים מאלי אקספרס</label>"
    "<input id='url' type='text' placeholder='https://s.click.aliexpress.com/e/...' />"
    "<label>תיאור המוצר (שם ומה הוא עושה)</label>"
    "<textarea id='info' placeholder='לדוגמה: אוזניות בלוטות עם ביטול רעשים, סוללה 30 שעות'></textarea>"
    "<button class='btn-main' id='btn' onclick='generate()'>✨ צור פוסט</button>"
    "<div class='loading' id='loading'>שולף פרטי מוצר ויוצר פוסט...</div>"
    "<div id='result' style='display:none'>"
    "<div id='stats' class='product-stats'>"
    "<div class='stat'>מחיר: <span id='statPrice'>-</span></div>"
    "<div class='stat'>מכירות: <span id='statSales'>-</span></div>"
    "<div class='stat'>דירוג: <span id='statRating'>-</span></div>"
    "</div>"
    "<div class='section'>"
    "<h3>📌 פוסט לפרסום:</h3>"
    "<div id='imgArea'></div>"
    "<div class='box' id='post'></div>"
    "<button class='copy-btn' onclick='copyText(\"post\", this)'>📋 העתק פוסט</button>"
    "</div>"
    "<div class='section'>"
    "<h3>💬 תגובה ראשונה (עם הקישור):</h3>"
    "<div class='box' id='comment'></div>"
    "<button class='copy-btn' onclick='copyText(\"comment\", this)'>📋 העתק תגובה</button>"
    "</div>"
    "</div>"
    "</div>"
    "<script>"
    "async function generate() {"
    "  const url = document.getElementById('url').value.trim();"
    "  const info = document.getElementById('info').value.trim();"
    "  if (!url) { alert('אנא הכנס קישור'); return; }"
    "  document.getElementById('btn').disabled = true;"
    "  document.getElementById('loading').style.display = 'block';"
    "  document.getElementById('result').style.display = 'none';"
    "  try {"
    "    const res = await fetch('/generate', {"
    "      method: 'POST',"
    "      headers: {'Content-Type': 'application/json'},"
    "      body: JSON.stringify({ url, info })"
    "    });"
    "    const data = await res.json();"
    "    if (data.post) {"
    "      document.getElementById('post').innerText = data.post;"
    "      document.getElementById('comment').innerText = data.comment;"
    "      const imgArea = document.getElementById('imgArea');"
    "      if (data.image) {"
    "        imgArea.innerHTML = \"<img src='\" + data.image + \"' class='product-img' />\";"
    "      } else { imgArea.innerHTML = ''; }"
    "      const stats = document.getElementById('stats');"
    "      if (data.price || data.sales || data.rating) {"
    "        stats.style.display = 'block';"
    "        document.getElementById('statPrice').innerText = data.price ? '$' + data.price : 'לא נמצא';"
    "        document.getElementById('statSales').innerText = data.sales || 'לא נמצא';"
    "        document.getElementById('statRating').innerText = data.rating ? data.rating + ' ⭐' : 'לא נמצא';"
    "      }"
    "      document.getElementById('result').style.display = 'block';"
    "    } else { alert('שגיאה, נסה שוב'); }"
    "  } catch(e) { alert('שגיאה: ' + e.message); }"
    "  document.getElementById('btn').disabled = false;"
    "  document.getElementById('loading').style.display = 'none';"
    "}"
    "function copyText(id, btn) {"
    "  const text = document.getElementById(id).innerText;"
    "  navigator.clipboard.writeText(text).then(() => {"
    "    btn.innerText = '✅ הועתק!';"
    "    setTimeout(() => btn.innerText = id === 'post' ? '📋 העתק פוסט' : '📋 העתק תגובה', 2000);"
    "  });"
    "}"
    "</script>"
    "</body>"
    "</html>"
)
 
@app.route("/")
def index():
    return render_template_string(HTML)
 
@app.route("/generate", methods=["POST"])
def generate():
    data = request.json
    info = data.get("info", "")
    url = data.get("url", "")
 
    product_data = get_product_data(url)
 
    extra_info = ""
    if product_data["price"]:
        extra_info += "מחיר: $" + product_data["price"] + ". "
    if product_data["sales"]:
        extra_info += "מכירות: " + str(product_data["sales"]) + ". "
    if product_data["rating"]:
        extra_info += "דירוג: " + str(product_data["rating"]) + " כוכבים. "
 
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
 
    system = "אתה כותב פוסטים לפייסבוק בעברית. כתוב רק את טקסט הפוסט עצמו, ללא הסברים, ללא כותרות, ללא הנחיות."
 
    prompt = (
        "כתוב פוסט קצר בעברית על המוצר הבא, כאילו אתה חבר שמספר לחברים שלו על משהו שגילית.\n\n"
        "הפוסט חייב:\n"
        "1. להתחיל בשאלה שמושכת תשומת לב\n"
        "2. לספר קצר על החוויה עם המוצר\n"
        "3. לציין את המחיר האמיתי אם ידוע\n"
        "4. לסיים בשאלה שמזמינה תגובות כמו: 'מי כבר ניסה? ספרו לי בתגובות'\n"
        "5. שורה ריקה ואז: הלינק בתגובה הראשונה למי שרוצה לבדוק\n\n"
        "המוצר: " + info + "\n"
        + (extra_info if extra_info else "") +
        "\n\nכתוב רק את הפוסט, קצר ומושך."
    )
 
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        system=system,
        messages=[{"role": "user", "content": prompt}]
    )
 
    post_text = msg.content[0].text + "\n\n" + url
    comment = "זה הדגם שעליו דיברתי, כולל משלוח לישראל\n" + url
 
    return jsonify({
        "post": post_text,
        "comment": comment,
        "image": product_data["image"],
        "price": product_data["price"],
        "sales": product_data["sales"],
        "rating": product_data["rating"]
    })
 
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
 
