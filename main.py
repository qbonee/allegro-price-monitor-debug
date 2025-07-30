import os
import json
import requests
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")
EMAIL_FROM = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_RECEIVERS = os.getenv("EMAIL_RECEIVER").split(",")

API_URL = "https://api.allegro.pl"
TOKEN_URL = "https://allegro.pl/auth/oauth/token"

def get_token():
    auth = requests.auth.HTTPBasicAuth(CLIENT_ID, CLIENT_SECRET)
    response = requests.post(TOKEN_URL, auth=auth, data={"grant_type": "client_credentials"})
    response.raise_for_status()
    return response.json()["access_token"]

def get_price(offer_id, token):
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.allegro.public.v1+json"
    }
    url = f"{API_URL}/offers/{offer_id}"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        return float(data["sellingMode"]["price"]["amount"])
    return None

def send_email(subject, body):
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = EMAIL_FROM
    msg["To"] = ", ".join(EMAIL_RECEIVERS)

    with smtplib.SMTP(os.getenv("EMAIL_HOST"), int(os.getenv("EMAIL_PORT"))) as server:
        server.starttls()
        server.login(EMAIL_FROM, EMAIL_PASSWORD)
        server.send_message(msg)

def check_all_products():
    token = get_token()
    alerts = []
    for file in os.listdir("products"):
        if file.endswith(".json"):
            print(f"🔍 Przetwarzam plik: {file}")
            with open(os.path.join("products", file)) as f:
                config = json.load(f)
            product_name = file.replace(".json", "")
            min_price = config["min_price"]
            for offer_id in config["offers"]:
                print(f"➡️  Sprawdzam ofertę: {offer_id}")
                price = get_price(offer_id, token)
                if price is not None:
                    print(f"📦 Produkt: {product_name}, Aukcja: {offer_id}, Cena: {price}, Min: {min_price}")
                    if price < min_price:
                        print("⚠️  Cena poniżej progu! Generuję alert.")
                        alerts.append(
                            f"Produkt: {product_name}\n"
                            f"Aukcja: https://allegro.pl/oferta/{offer_id}\n"
                            f"Cena aktualna: {price:.2f} zł\n"
                            f"Minimalna cena: {min_price:.2f} zł\n"
                        )
                else:
                    print(f"❌ Nie udało się pobrać ceny dla aukcji {offer_id}")

    if alerts:
        body = "\n\n".join(alerts)
        send_email("Przekroczono minimalną cenę!!!", body)
        print("📨 Alert wysłany na maila.")
    else:
        print("✅ Wszystkie ceny OK.")

if __name__ == "__main__":
    check_all_products()
