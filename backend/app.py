from flask import Flask, request, jsonify
import psycopg2
import requests
import os
import secrets
import hashlib
from email_utils import send_email

app = Flask(__name__, static_url_path='/static', static_folder='static')

DB_CONFIG = {
    'dbname': os.environ['DB_NAME'],
    'user': os.environ['DB_USER'],
    'password': os.environ['DB_PASSWORD'],
    'host': os.environ['DB_HOST'],
    'port': os.environ.get('DB_PORT', 5432)
}

ADMIN_TOKEN = "$TefanTux240192"
SVG_WIDTH = 2754
SVG_HEIGHT = 1398

def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)

def lonlat_to_svg_coords(lon, lat):
    x = (lon + 180) * (SVG_WIDTH / 360)
    y = (90 - lat) * (SVG_HEIGHT / 180)
    return round(x, 2), round(y, 2)

def get_coords_from_nominatim(postcode, country):
    url = f"https://nominatim.openstreetmap.org/search?postalcode={postcode}&country={country}&format=json"
    headers = {'User-Agent': 'via-lumina-bot'}
    response = requests.get(url, headers=headers)
    data = response.json()
    if data:
        lat = float(data[0]['lat'])
        lon = float(data[0]['lon'])
        return lat, lon
    return None, None

@app.route('/')
def index():
    return "Via Lumina Backend aktiv"

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
        cur.execute("""
            INSERT INTO members (email, country, postcode, confirmed, token)
            VALUES (%s, %s, %s, %s, %s)
        """, (email, country, postcode, False, token))
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
    html_content = f"<p>Bitte bestätige deine Anmeldung bei <strong>Via Lumina</strong>:</p><p><a href='{confirm_url}'>{confirm_url}</a></p>"

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
    cur.execute("SELECT * FROM members WHERE email = %s AND token = %s", (email, token))
    user = cur.fetchone()

    if not user:
        cur.close()
        conn.close()
        return "<h1>Bestätigung fehlgeschlagen</h1>", 404

    cur.execute("UPDATE members SET confirmed = TRUE WHERE email = %s", (email,))
    conn.commit()
    cur.close()
    conn.close()

    return '''
    <html>
      <head>
        <meta http-equiv="refresh" content="0; URL='https://www.via-lumina.org/bestaetigt.html'" />
      </head>
      <body>
        <p>Du wirst weitergeleitet...</p>
      </body>
    </html>
    '''

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

@app.route('/api/lichtpunkte', methods=['GET'])
def api_lichtpunkte():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT country, postcode FROM members WHERE confirmed = TRUE")
    results = cur.fetchall()
    cur.close()
    conn.close()

    lichtpunkte = []
    for country, postcode in results:
        lat, lon = get_coords_from_nominatim(postcode, country)
        if lat and lon:
            lichtpunkte.append({
                'country': country,
                'postcode': postcode,
                'lat': lat,
                'lon': lon
            })

    return jsonify({'lichtpunkte': lichtpunkte})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
