from flask import Flask, request, jsonify
import psycopg2
import os
import hashlib
import secrets
from email_utils import send_email

app = Flask(__name__)

# 🔐 PostgreSQL-Konfiguration aus Umgebungsvariablen
DB_CONFIG = {
    'dbname': os.environ['DB_NAME'],
    'user': os.environ['DB_USER'],
    'password': os.environ['DB_PASSWORD'],
    'host': os.environ['DB_HOST'],
    'port': os.environ.get('DB_PORT', 5432)
}

# 🔐 Admin-Zugriffstoken
ADMIN_TOKEN = "$TefanTux240192"

def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)

@app.route('/')
def index():
    return "Via Lumina Backend (PostgreSQL verbunden)"

@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    email = data.get('email')
    country = data.get('country')
    postcode = data.get('postcode')

    if not email or not country or not postcode:
        return jsonify({'error': 'Missing fields'}), 400

    raw_token = f"{email}-{secrets.token_hex(16)}"
    token = hashlib.sha256(raw_token.encode()).hexdigest()

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute('''
            INSERT INTO members (email, country, postcode, confirmed, token)
            VALUES (%s, %s, %s, %s, %s)
        ''', (email, country, postcode, False, token))
        conn.commit()
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        return jsonify({'error': 'Email already registered'}), 409
    finally:
        cur.close()
        conn.close()

    confirm_url = f"https://via-lumina-backend.onrender.com/api/confirm?email={email}&token={token}"

    subject = "Bestätige deine Anmeldung bei Via Lumina"
    plain_text = f"Bitte bestätige deine Anmeldung:\n{confirm_url}"
    html_content = f"""
    <p>Bitte bestätige deine Anmeldung bei <strong>Via Lumina</strong>:</p>
    <p><a href="{confirm_url}">{confirm_url}</a></p>
    """

    send_email(email, subject, plain_text, html_content)

    return jsonify({'message': 'Bitte bestätige deine E-Mail.'}), 201

@app.route('/api/confirm', methods=['GET'])
def confirm_email():
    email = request.args.get('email')
    token = request.args.get('token')

    if not email or not token:
        return "<h1>Ungültiger Link</h1>", 400

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM members WHERE email = %s AND token = %s', (email, token))
    user = cur.fetchone()

    if not user:
        cur.close()
        conn.close()
        return "<h1>Bestätigung fehlgeschlagen</h1>", 404

    cur.execute('UPDATE members SET confirmed = TRUE WHERE email = %s', (email,))
    conn.commit()
    cur.close()
    conn.close()

    return """
    <html>
      <head>
        <meta http-equiv="refresh" content="0; URL='https://www.via-lumina.org/bestaetigt.html'" />
      </head>
      <body>
        <p>Du wirst weitergeleitet…</p>
      </body>
    </html>
    """

@app.route('/api/members', methods=['GET'])
def get_members():
    token = request.args.get('access_token')
    if token != ADMIN_TOKEN:
        return jsonify({'error': 'Zugriff verweigert'}), 403

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, email, country, postcode, confirmed FROM members")
    rows = cur.fetchall()
    cur.close()
    conn.close()

    members = [
        {
            'id': r[0],
            'email': r[1],
            'country': r[2],
            'postcode': r[3],
            'confirmed': r[4]
        } for r in rows
    ]

    return jsonify({'members': members})

@app.route('/api/init-db', methods=['POST'])
def init_db():
    token = request.args.get('access_token')
    if token != ADMIN_TOKEN:
        return jsonify({'error': 'Zugriff verweigert'}), 403

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute('''
            CREATE TABLE IF NOT EXISTS members (
                id SERIAL PRIMARY KEY,
                email TEXT NOT NULL UNIQUE,
                country TEXT NOT NULL,
                postcode TEXT NOT NULL,
                confirmed BOOLEAN DEFAULT FALSE,
                token TEXT
            );
        ''')
        conn.commit()
        return jsonify({'message': 'Tabelle "members" wurde erfolgreich erstellt.'}), 201

    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500

    finally:
        cur.close()
        conn.close()

# Render-Port Setup
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
