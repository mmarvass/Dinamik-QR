import io
import os
import sqlite3
from flask import Flask, render_template_string, redirect, request, send_file

app = Flask(__name__)
app.secret_key = "gizli_anahtar_qr_panel"

SUNUCU_ADRESI = os.getenv("RENDER_EXTERNAL_URL", "http://localhost:5000")
DB_NAME = "qrcodes.db"


def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS qrcodes (
            code_id TEXT PRIMARY KEY,
            target_url TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()


def get_all_codes():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT code_id, target_url FROM qrcodes')
    rows = cursor.fetchall()
    conn.close()
    return dict(rows)


def get_target_url(code_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT target_url FROM qrcodes WHERE code_id = ?', (code_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None


def add_or_update_code(code_id, target_url):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO qrcodes (code_id, target_url)
        VALUES (?, ?)
        ON CONFLICT(code_id) DO UPDATE SET target_url=excluded.target_url
    ''', (code_id, target_url))
    conn.commit()
    conn.close()


def delete_code(code_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM qrcodes WHERE code_id = ?', (code_id,))
    conn.commit()
    conn.close()


HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <title>Dinamik QR & Data Matrix Paneli</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 30px; background-color: #f4f6f9; }
        .container { max-width: 950px; margin: auto; background: white; padding: 25px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h2 { color: #333; margin-top: 0; }
        .form-group { margin-bottom: 15px; }
        label { display: block; margin-bottom: 5px; font-weight: bold; }
        input[type="text"], input[type="url"] { width: 100%; padding: 10px; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box; }
        button { background-color: #28a745; color: white; border: none; padding: 10px 15px; border-radius: 4px; cursor: pointer; font-size: 16px; }
        button:hover { background-color: #218838; }
        table { width: 100%; border-collapse: collapse; margin-top: 25px; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background-color: #007bff; color: white; }
        .btn-link { padding: 6px 10px; color: white; text-decoration: none; border-radius: 3px; font-size: 12px; display: inline-block; margin-right: 3px; }
        .btn-qr { background-color: #17a2b8; }
        .btn-dm { background-color: #6f42c1; }
        .btn-delete { background-color: #dc3545; }
        .badge { background-color: #e9ecef; color: #495057; padding: 3px 8px; border-radius: 4px; font-size: 12px; }
    </style>
</head>
<body>
<div class="container">
    <h2>🚀 Dinamik QR & Data Matrix Paneli <span class="badge">Canlı Sistem</span></h2>

    <form action="/kaydet" method="POST">
        <div class="form-group">
            <label>Kod Kimliği (ID):</label>
            <input type="text" name="code_id" placeholder="ör: katalog-2026" required>
        </div>
        <div class="form-group">
            <label>Hedef Adres (URL):</label>
            <input type="url" name="target_url" placeholder="https://www.siteniz.com" required>
        </div>
        <button type="submit">💾 Veritabanına Kaydet</button>
    </form>

    <hr style="margin-top: 30px;">

    <h3>Kalıcı Dinamik Kodlar</h3>
    <table>
        <thead>
            <tr>
                <th>Kod ID</th>
                <th>Hedef Adres</th>
                <th>İndir / Görüntüle</th>
                <th>İşlem</th>
            </tr>
        </thead>
        <tbody>
            {% for code_id, target_url in database.items() %}
            <tr>
                <td><strong>{{ code_id }}</strong></td>
                <td><a href="{{ target_url }}" target="_blank">{{ target_url }}</a></td>
                <td>
                    <a href="/generate/qr/{{ code_id }}" target="_blank" class="btn-link btn-qr">📱 QR Kod</a>
                    <a href="/generate/datamatrix/{{ code_id }}" target="_blank" class="btn-link btn-dm">🔳 Data Matrix</a>
                </td>
                <td>
                    <a href="/sil/{{ code_id }}" class="btn-link btn-delete" onclick="return confirm('Bu kaydı silmek istediğinize emin misiniz?')">Sil</a>
                </td>
            </tr>
            {% else %}
            <tr>
                <td colspan="4" style="text-align: center; color: #777;">Henüz kayıtlı bir kod bulunmuyor. Eklemek için yukarıdaki formu kullanabilirsiniz.</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>
</body>
</html>
"""


@app.route('/')
def index():
    database = get_all_codes()
    return render_template_string(HTML_TEMPLATE, database=database)


@app.route('/kaydet', methods=['POST'])
def kaydet():
    code_id = request.form.get('code_id').strip()
    target_url = request.form.get('target_url').strip()
    if code_id and target_url:
        add_or_update_code(code_id, target_url)
    return redirect('/')


@app.route('/sil/<code_id>')
def sil(code_id):
    delete_code(code_id)
    return redirect('/')


@app.route('/r/<code_id>')
def yonlendir(code_id):
    hedef_url = get_target_url(code_id)
    if hedef_url:
        return redirect(hedef_url, code=302)
    return "Geçersiz veya silinmiş kod!", 404


@app.route('/generate/qr/<code_id>')
def qr_uret(code_id):
    import qrcode
    sabit_link = f"{SUNUCU_ADRESI}/r/{code_id}"
    img = qrcode.make(sabit_link)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return send_file(buffer, mimetype='image/png')


@app.route('/generate/datamatrix/<code_id>')
def datamatrix_uret(code_id):
    import segno
    sabit_link = f"{SUNUCU_ADRESI}/r/{code_id}"
    dm = segno.make(sabit_link, micro=False)
    buffer = io.BytesIO()
    dm.save(buffer, kind='png', scale=8)
    buffer.seek(0)
    return send_file(buffer, mimetype='image/png')


init_db()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)