from flask import Flask, request, jsonify
import sqlite3
import os
import hashlib
import secrets
from email_utils import send_email

app = Flask(__name__)
DATABASE = os.path.join(os.path.dirname(__file__), '..', 'data', 'via_lumina.db')

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    return "Via Lumina Backend API"

@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    email = data.get('email')
    country = data.get('country')
    postcode = data.get('postcode')

    if not email or not country or not postcode:
        return jsonify({'error': 'Missing fields'}), 400

    # Token generieren
    raw_token = f"{email}-{secrets.token_hex(16)}"
    token = hashlib.sha256(raw_token.encode()).hexdigest()

    # In DB speichern (confirmed = False)
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute('INSERT INTO members (email, country, postcode, confirmed, token) VALUES (?, ?, ?, ?, ?)',
                    (email, country, postcode, False, token))
        conn.commit()
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Email already registered'}), 409
    finally:
        conn.close()

    # Bestätigungslink erstellen
    confirm_url = f"https://via-lumina-backend.onrender.com/api/confirm?email={email}&token={token}"

    # E-Mail versenden
    subject = "Bestätige deine Anmeldung bei Via Lumina"
    plain_text = (
        f"Du hast dich bei Via Lumina registriert.\n\n"
        f"Bitte bestätige deine Anmeldung, indem du auf diesen Link klickst:\n{confirm_url}\n\n"
        f"Falls du dich nicht registriert hast, kannst du diese E-Mail ignorieren."
    )
    html_content = f"""
    <p>Du hast dich bei <strong>Via Lumina</strong> registriert.</p>
    <p>Bitte bestätige deine Anmeldung:</p>
    <p><a href="{confirm_url}">{confirm_url}</a></p>
    <p>Falls du dich nicht registriert hast, kannst du diese E-Mail ignorieren.</p>
    """

    send_email(email, subject, plain_text, html_content)

    return jsonify({'message': 'Bitte bestätige deine E-Mail. Eine Nachricht wurde gesendet.'}), 201

@app.route('/api/confirm', methods=['GET'])
def confirm_email():
    email = request.args.get('email')
    token = request.args.get('token')

    if not email or not token:
        return "<h1>Ungültiger Bestätigungslink</h1>", 400

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM members WHERE email = ? AND token = ?', (email, token))
    user = cur.fetchone()

    if not user:
        conn.close()
        return "<h1>Bestätigung fehlgeschlagen</h1>", 404

    cur.execute('UPDATE members SET confirmed = 1 WHERE email = ?', (email,))
    conn.commit()
    conn.close()

    # Clientseitige Weiterleitung
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

# Render-Port Setup
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
