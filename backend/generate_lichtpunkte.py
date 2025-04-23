import psycopg2
import requests
import os
from flask import Flask, request, jsonify

app = Flask(__name__)

DB_CONFIG = {
    'dbname': os.environ['DB_NAME'],
    'user': os.environ['DB_USER'],
    'password': os.environ['DB_PASSWORD'],
    'host': os.environ['DB_HOST'],
    'port': os.environ.get('DB_PORT', 5432)
}

SVG_WIDTH = 2754
SVG_HEIGHT = 1398
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), '../assets/lichtpunkte.svg')

ADMIN_TOKEN = "$TefanTux240192"

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
        return lonlat_to_svg_coords(lon, lat)
    return None, None

def generate_svg():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT country, postcode FROM members WHERE confirmed = TRUE")
    results = cur.fetchall()
    conn.close()

    circles = []
    for country, postcode in results:
        cx, cy = get_coords_from_nominatim(postcode, country)
        if cx and cy:
            circles.append(f'''
<circle cx="{cx}" cy="{cy}" r="1.0" fill="#f4b400" filter="url(#glow)">
  <title>{postcode}, {country} – Ein Ort, an dem das Licht weiterlebt.</title>
</circle>
''')

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("<svg xmlns='http://www.w3.org/2000/svg' width='2754' height='1398'>\n")
        f.write("<defs><filter id='glow'><feGaussianBlur stdDeviation='2.5' result='glow'/></filter></defs>\n")
        f.writelines(circles)
        f.write("</svg>")

@app.route("/api/generate-lichtpunkte", methods=["POST"])
def api_generate_lichtpunkte():
    token = request.args.get("access_token")
    if token != ADMIN_TOKEN:
        return jsonify({"error": "Zugriff verweigert"}), 403

    try:
        generate_svg()
        return jsonify({"status": "fertig"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
