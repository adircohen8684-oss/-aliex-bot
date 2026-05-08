import os
import anthropic
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

HTML = """<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>יוצר פוסטים</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Heebo:wght@400;700;900&display=swap');
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family:'Heebo',sans-serif; background:#0f0f0f; color:#fff; min-height:100vh; display:flex; align-items:center; justify-content:center; padding:20px; }
.container { width:100%; max-width:600px; }
h1 { font-size:2rem; font-weight:900; text-align:center; margin-bottom:8px; background:linear-gradient(135deg,#ff6b35,#f7931e); -webkit-background-clip:text; -webkit-text-fill-color:transparent; }
p.sub { text-align:center; color:#888; margin-bottom:30px; }
.card { background:#1a1a1a; border:1px solid #2a2a2a; border-radius:16px; padding:24px; }
label { display:block; color:#aaa; font-size:0.85rem; margin-bottom:8px; }
input,textarea { width:100%; padding:14px 16px; background:#0f0f0f; border:1px solid #333; border-radius:10px; color:#fff; font-size:1rem; font-family:'Heebo',sans-serif; margin-bottom:16px; }
input { direction:ltr; }
textarea { direction:rtl; resize:vertical; min-height:80px; }
button { width:100%; padding:16px; background:linear-gradient(135deg,#ff6b35,#f7931e); border:none; border-radius:10px; color:#fff; font-size:1.1rem; font-weight:700; font-family:'Heebo',sans-serif; cursor:pointer; margin-bottom:10px; }
button:disabled { opacity:0.5; }
.copy-btn { background:#28a745; }
.loading { text-align:center; color:#ff6b35; padding:20px; display:none; }
.result { margin-top:24px; display:none; }
.post-box { background:#0f0f0f; border:1px solid #333; border-radius:10px; padding:16px; font-size:1rem; line-height:1.7; white-space:pre-wrap; direction:rtl; min-height:120px; }
.spinner { display:inline-block; width:20px; height:20px; border:2px solid #ff6b35; border-top-color:transparent; border-radius:50%; animation:spin 0.8s linear infinite; margin-left:8px; vertical-align:middle; }
@keyframes spin { to { transform:rotate(360deg); } }
</style>
</head>
<body>
<div class="container">
  <h1>🛒 יוצר פוסטים</h1>
  <p class="sub">הדבק קישור ופרטי מוצר וקבל פוסט שיווקי</p>
  <div class="card">
    <label>קישור השותפים</label>
    <input type="text" id="urlInput" placeholder="https://s.click.aliexpress.com/e/..." />
    <label>פרטי המוצר</label>
    <textarea id="info" placeholder="שם המוצר, מחיר, תיאור קצר"></textarea>
    <button id="btn" onclick="generate()">✨ צור פוסט</button>
    <div class="loading" id="loading"><span class="spinner"></span> יוצר...</div>
    <div class="result" id="result">
      <label>הפוסט שלך:</label>
      <div class="post-box" id="postBox"></div>
      <button class="copy-btn" onclick="copyPost()">📋 העתק פוסט</button>
    </div>
  </div>
</div>
<script>
async function generate() {
  const url = document.getElementById('urlInput').value.trim();
  const info = document.getElementById('info').value.trim();
  if (!url) { alert('הכנס קישור'); return; }
  document.getElementById('btn').disabled = true;
  document.getElementById('loading').style.display = 'block';
  document.getElementById('result').style.display = 'none';
  const res = await fetch('/generate', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({url,info})});
  const data = await res.json();
  document.getElementById('btn').disabled = false;
  document.getElementById('loading').style.display = 'none';
  if (data.post) {
    document.getElementById('postBox').textContent = data.post;
    document.getElementById('result').style.display = 'block';
  } else { alert('שגיאה, נסה שוב'); }
}
function copyPost() {
  navigator.clipboard.writeText(document.getElementById('postBox').textContent).then(() => {
    const b = document.querySelector('.copy-btn');
    b.textContent = '✅ הועתק!';
    setTimeout(() => b.textContent = '📋 העתק פוסט', 2000);
  });
}
</script>
</body>
</html>"""

@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/generate", methods=["POST"])
def generate():
    data = request.json
    url = data.get("url", "")
    info = data.get("info", "מוצר מאליאקספרס")
    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        msg = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            messages=[{"role":"user","content":f"אתה מומחה שיווק ישראלי. פרטי המוצר: {info}. קישור: {url}. כתוב פוסט שיווקי מושך בעברית לפייסבוק: שורה ראשונה חזקה, 3-4 משפטים עם אימוג'י, הדגש חיסכון, תחושת דחיפות, סיים עם 'לרכישה: {url}'. כתוב רק את הפוסט."}]
        )
        return jsonify({"post": msg.content[0].text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

