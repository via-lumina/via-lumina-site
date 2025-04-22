
from flask import Flask, request, jsonify
import sqlite3
import os

app = Flask(__name__)
DATABASE = os.path.join(os.path.dirname(__file__), '..', 'data', 'via_lumina.db')

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    email = data.get('email')
    country = data.get('country')
    postcode = data.get('postcode')

    if not email or not country or not postcode:
        return jsonify({'error': 'Missing fields'}), 400

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute('INSERT INTO members (email, country, postcode) VALUES (?, ?, ?)', 
                    (email, country, postcode))
        conn.commit()
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Email already registered'}), 409
    finally:
        conn.close()

    return jsonify({'message': 'Member registered successfully'}), 201

@app.route('/')
def index():
    return "Via Lumina Backend API"

if __name__ == '__main__':
    import os
    from email_utils import send_email
port = int(os.environ.get("PORT", 5000))
app.run(host="0.0.0.0", port=port)

