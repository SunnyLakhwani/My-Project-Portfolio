import os
import string
import random
from datetime import datetime
from flask import Flask, request, jsonify, redirect, render_template_string
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# ── MySQL connection ──────────────────────────────────────
# ── SQLite connection (NO INSTALL NEEDED) ─────────────────
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///site.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'snipurl-secret')

db = SQLAlchemy(app)


# ── Model ─────────────────────────────────────────────────
class URL(db.Model):
    __tablename__ = 'urls'
    id           = db.Column(db.Integer, primary_key=True, autoincrement=True)
    original_url = db.Column(db.Text, nullable=False)
    short_code   = db.Column(db.String(10), unique=True, nullable=False)
    click_count  = db.Column(db.Integer, default=0)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id':           self.id,
            'original_url': self.original_url,
            'short_code':   self.short_code,
            'short_url':    f"http://localhost:5000/{self.short_code}",
            'click_count':  self.click_count,
            'created_at':   self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }


# ── Helper ────────────────────────────────────────────────
def generate_code(length=6):
    chars = string.ascii_letters + string.digits
    while True:
        code = ''.join(random.choices(chars, k=length))
        if not URL.query.filter_by(short_code=code).first():
            return code


# ── HTML Frontend ─────────────────────────────────────────
HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>SnipURL</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: 'Segoe UI', sans-serif; background: #0f172a; color: #e2e8f0; }
    header { background: #1e293b; padding: 20px 40px; border-bottom: 1px solid #334155; }
    header h1 { color: #38bdf8; font-size: 1.6rem; }
    header p  { color: #94a3b8; font-size: 0.85rem; margin-top: 4px; }
    .wrap { max-width: 740px; margin: 56px auto; padding: 0 20px; }
    .card { background: #1e293b; border-radius: 14px; padding: 32px; border: 1px solid #334155; }
    .row  { display: flex; gap: 10px; margin-top: 10px; }
    input { flex: 1; padding: 13px 16px; border-radius: 9px; border: 1px solid #475569;
            background: #0f172a; color: #f1f5f9; font-size: 1rem; outline: none; }
    input:focus { border-color: #38bdf8; }
    button { padding: 13px 24px; background: #38bdf8; color: #0f172a;
             border: none; border-radius: 9px; font-weight: 700; cursor: pointer; }
    button:hover { background: #7dd3fc; }
    .result { margin-top: 20px; padding: 16px; background: #0f172a;
              border-radius: 9px; border: 1px solid #334155; display: none; }
    .result p { font-size: 0.82rem; color: #94a3b8; }
    .result a { color: #38bdf8; font-size: 1.1rem; font-weight: 600; word-break: break-all; }
    .err  { color: #f87171; font-size: 0.86rem; margin-top: 10px; }
    .tbl  { margin-top: 38px; }
    .tbl h3 { font-size: 0.82rem; color: #64748b; text-transform: uppercase;
              letter-spacing: .07em; margin-bottom: 12px; }
    table { width: 100%; border-collapse: collapse; font-size: 0.83rem; }
    th { padding: 9px 12px; background: #0f172a; color: #64748b;
         border-bottom: 1px solid #334155; text-align: left; }
    td { padding: 9px 12px; border-bottom: 1px solid #1e293b; color: #cbd5e1; }
    td a { color: #38bdf8; text-decoration: none; }
    .badge { background: #0c4a6e; color: #7dd3fc; padding: 2px 9px;
             border-radius: 20px; font-size: 0.76rem; font-weight: 600; }
    .clk   { background: #14532d; color: #86efac; padding: 2px 9px;
             border-radius: 20px; font-size: 0.76rem; }
  </style>
</head>
<body>
<header><h1>✂️ SnipURL</h1><p>Shorten any URL — fast, clean &amp; trackable.</p></header>
<div class="wrap">
  <div class="card">
    <h2 style="font-size:1rem;color:#f1f5f9">Paste your long URL</h2>
    <div class="row">
      <input type="url" id="urlInput" placeholder="https://example.com/very/long/link" />
      <button onclick="shorten()">Shorten →</button>
    </div>
    <div class="result" id="res">
      <p>Your short URL:</p>
      <a id="link" href="#" target="_blank"></a><br>
      <button style="margin-top:10px;padding:7px 16px;font-size:.8rem;background:#1e40af;color:#bfdbfe"
              onclick="copy()">📋 Copy</button>
    </div>
    <p class="err" id="err"></p>
  </div>

  <div class="tbl">
    <h3>📊 Recent URLs</h3>
    <table>
      <thead><tr><th>Code</th><th>Original URL</th><th>Clicks</th><th>Created</th></tr></thead>
      <tbody id="tbody"></tbody>
    </table>
  </div>
</div>

<script>
async function shorten() {
  const url = document.getElementById('urlInput').value.trim();
  document.getElementById('err').textContent = '';
  document.getElementById('res').style.display = 'none';
  if (!url) { document.getElementById('err').textContent = 'Enter a URL first.'; return; }
  const r = await fetch('/api/shorten', { method:'POST',
    headers:{'Content-Type':'application/json'}, body:JSON.stringify({url}) });
  const d = await r.json();
  if (!r.ok) { document.getElementById('err').textContent = d.error; return; }
  document.getElementById('link').href = d.short_url;
  document.getElementById('link').textContent = d.short_url;
  document.getElementById('res').style.display = 'block';
  load();
}
function copy() { navigator.clipboard.writeText(document.getElementById('link').href); }
async function load() {
  const d = await (await fetch('/api/urls')).json();
  document.getElementById('tbody').innerHTML = d.length
    ? d.map(u=>`<tr>
        <td><span class="badge">${u.short_code}</span></td>
        <td><a href="${u.original_url}" target="_blank">${u.original_url.substring(0,50)}${u.original_url.length>50?'...':''}</a></td>
        <td><span class="clk">👁 ${u.click_count}</span></td>
        <td>${u.created_at}</td></tr>`).join('')
    : '<tr><td colspan="4" style="text-align:center;color:#475569;padding:18px">No URLs yet.</td></tr>';
}
load();
</script>
</body></html>
"""


# ── Routes ────────────────────────────────────────────────
@app.route('/')
def index():
    return render_template_string(HTML)

@app.route('/api/shorten', methods=['POST'])
def shorten():
    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({'error': 'Provide a URL in the request body.'}), 400
    url = data['url'].strip()
    if not url.startswith(('http://', 'https://')):
        return jsonify({'error': 'URL must start with http:// or https://'}), 400
    existing = URL.query.filter_by(original_url=url).first()
    if existing:
        return jsonify(existing.to_dict()), 200
    new = URL(original_url=url, short_code=generate_code())
    db.session.add(new)
    db.session.commit()
    return jsonify(new.to_dict()), 201

@app.route('/<code>')
def redirect_url(code):
    entry = URL.query.filter_by(short_code=code).first()
    if not entry:
        return jsonify({'error': 'Not found.'}), 404
    entry.click_count += 1
    db.session.commit()
    return redirect(entry.original_url)

@app.route('/api/urls')
def list_urls():
    rows = URL.query.order_by(URL.created_at.desc()).limit(20).all()
    return jsonify([r.to_dict() for r in rows])

@app.route('/api/urls/<code>', methods=['DELETE'])
def delete_url(code):
    entry = URL.query.filter_by(short_code=code).first()
    if not entry:
        return jsonify({'error': 'Not found.'}), 404
    db.session.delete(entry)
    db.session.commit()
    return jsonify({'message': f'Deleted "{code}".'})


# ── Run ───────────────────────────────────────────────────
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print("✅ URL Shortener — SQLite ready & tables created.")
        print("🌐 Running at: http://localhost:5000")
    app.run(debug=True, port=5000)