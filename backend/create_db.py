import sqlite3
import os

# Pfad zur Datenbank festlegen (im Ordner /data)
db_folder = os.path.join(os.path.dirname(__file__), '..', 'data')
os.makedirs(db_folder, exist_ok=True)
db_path = os.path.join(db_folder, 'via_lumina.db')

# Verbindung herstellen
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Tabelle erstellen (falls nicht vorhanden)
cur.execute('''
CREATE TABLE IF NOT EXISTS members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    country TEXT NOT NULL,
    postcode TEXT NOT NULL,
    confirmed BOOLEAN DEFAULT 0,
    token TEXT
)
''')

conn.commit()
conn.close()

print("Datenbank erfolgreich erstellt und Tabelle 'members' eingerichtet.")
