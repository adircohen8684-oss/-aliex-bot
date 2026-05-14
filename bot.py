import os
import anthropic
from flask import Flask, request, jsonify, render_template_string

app = Flask(name)
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

HTML = """
<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
<meta charset="UTF-8">
<title>יוצר פוסטים לקבוצת פייסבוק</title>
<style>
body { font-family: Arial; background:#111; color:#fff; padding:20px }
.container { max-width:600px; margin:auto }
input, textarea { width:100%; padding:12px; margin-bottom:12px }
button { padding:14px; width:100%; font-size:16px }
.box { background:#1c1c1c; padding:15px; margin-top:10px; white-space:pre-wrap }
</style>
</head>
<body>
<div class="container">
<h2>✍️ יוצר פוסטים חכם</h2>

<input id="url" placeholder="הדבק קישור שותפים מאלי אקספרס">
<textarea id="info" placeholder="תיאור קצר של המוצר"></textarea>

<button onclick="generate()">צור פוסט</button>

<div id="result" style="display:none">
<h3>📌 פוסט לפרסום:</h3>
<div class="box" id="post"></div>

<h3>💬 תגובה ראשונה:</h3>
<div class="box" id="comment"></div>
</div>
</div>

<script>
async function generate() {
  const url = document.getElementById("url").value;
  const info = document.getElementById("info").value;

  const res = await fetch("/generate", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({ url, info })
  });

  const data = await res.json();
  document.getElementById("post").innerText = data.post;
  document.getElementById("comment").innerText = data.comment;
  document.getElementById("result").style.display = "block";
}
</script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/generate", methods=["POST"])
def generate():
    data = request.json
    info = data.get("info", "")
    url = data.get("url", "")

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    prompt = f"""
אתה מנהל קבוצת פייסבוק ישראלית עם כ־4,600 חברים.
כתוב פוסט בעברית שנשמע כמו המלצה אישית ואמיתית,
לא כמו פרסומת ולא כמו חנות.

כללים:
- אל תכתוב מילים שיווקיות
- אל תיצור לחץ או דחיפות
- אל תכניס קישור לפוסט
- תתאר בעיה אמיתית שהמוצר פותר
- תציין למי זה מתאים ולמי פחות
- סיים במשפט: "הלינק בתגובה הראשונה למי שרוצה לבדוק"

פרטי המוצר:
{info}

כתוב רק את הפוסט.
"""

    msg = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}]
    )

    comment = f"""זה הדגם שעליו דיברתי,
כולל משלוח לישראל 👇
{url}"""

    return jsonify({
        "post": msg.content[0].text,
        "comment": comment
    })

if name == "main":
    app.run(host="0.0.0.0", port=5000)
