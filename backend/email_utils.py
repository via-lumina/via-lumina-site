import os
from dotenv import load_dotenv
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Lade Umgebungsvariablen (nur lokal relevant)
load_dotenv()

SMTP_SERVER = 'smtp.zoho.eu'
SMTP_PORT = 465  # SSL Port
SMTP_USER = 'noreply@via-lumina.org'
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

# Debug-Ausgabe
print(f"[email_utils] SMTP_PASSWORD geladen: {SMTP_PASSWORD is not None}")

def send_email(to_email, subject, plain_text, html_content=None):
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = SMTP_USER
    msg['To'] = to_email

    part1 = MIMEText(plain_text, 'plain')
    msg.attach(part1)

    if html_content:
        part2 = MIMEText(html_content, 'html')
        msg.attach(part2)

    try:
        print(f"[email_utils] Sende E-Mail an: {to_email}")
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, to_email, msg.as_string())
        print("[email_utils] E-Mail erfolgreich versendet.")
        return True
    except Exception as e:
        print(f"[email_utils] Fehler beim E-Mail-Versand: {e}")
        return False
