import os
import re
import requests
import anthropic
from flask import Flask, request, jsonify, render_template_string
 
app = Flask(__name__)
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
 
def get_product_image(url):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "he-IL,he;q=0.9,en-US;q=0.8",
        }
        session = requests.Session()
        r = session.get(url, headers=headers, timeout=15, allow_redirects=True)
        html = r.text
        patterns = [
            r'property="og:image"\s+content="([^"]+)"',
            r'content="([^"]+)"\s+property="og:image"',
            r'"image"\s*:\s*"(https://ae\d+\.alicdn\.com[^"]+)"',
            r'src="(https://ae\d+\.alicdn\.com[^"]+\.jpg[^"]*)"',
            r'"mainImage"\s*:\s*\{[^}]*"imageUrl"\s*:\s*"([^"]+)"',
        ]
        for pattern in patterns:
            match = re.search(pattern, html)
            if match:
                img = match.group(1)
                if img.startswith("http"):
                    return img
    except Exception as e:
        print("Image fetch error:", e)
    return None
 
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
    ".no-img { color:#888; font-size:0.85rem; margin-bottom:10px; text-align:center; }"
    "</style>"
    "</head>"
    "<body>"
    "<div class='container'>"
    "<h2>✍️ יוצר פוסטים חכם</h2>"
    "<label>קישור שותפים מאלי אקספרס</label>"
    "<input id='url' type='text' placeholder='https://s.click.aliexpress.com/e/...' />"
    "<label>תיאור המוצר (שם, מחיר, מה הוא עושה)</label>"
    "<textarea id='info' placeholder='לדוגמה: אוזניות בלוטות, מחיר 18 דולר במקום 55, סוללה 30 שעות'></textarea>"
    "<button class='btn-main' id='btn' onclick='generate()'>✨ צור פוסט</button>"
    "<div class='loading' id='loading'>יוצר פוסט...</div>"
    "<div id='result' style='display:none'>"
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
    "      } else {"
    "        imgArea.innerHTML = \"<p class='no-img'>תמונה לא נמצאה - הוסף ידנית בפייסבוק</p>\";"
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
 
    image_url = get_product_image(url)
 
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
 
    prompt = (
        "אתה מנהל קבוצת פייסבוק ישראלית עם כ4600 חברים.\n"
        "כתוב פוסט בעברית שנשמע כמו המלצה אישית ואמיתית, לא כמו פרסומת.\n\n"
        "כללים:\n"
        "- אל תכתוב מילים שיווקיות\n"
        "- אל תיצור לחץ או דחיפות\n"
        "- אל תכניס קישור לפוסט\n"
        "- תתאר בעיה אמיתית שהמוצר פותר\n"
        "- תציין למי זה מתאים ולמי פחות\n"
        "- סיים במשפט: הלינק בתגובה הראשונה למי שרוצה לבדוק\n\n"
        "פרטי המוצר:\n"
        + info +
        "\n\nכתוב רק את הפוסט, ללא הסברים."
    )
 
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )
 
    post_text = msg.content[0].text + "\n\n" + url
    comment = "זה הדגם שעליו דיברתי, כולל משלוח לישראל\n" + url
 
    return jsonify({
        "post": post_text,
        "comment": comment,
        "image": image_url
    })
 
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
 
 
