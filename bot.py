import os
import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from math import radians, cos, sin, asin, sqrt
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
TARGET_LAT = float(os.environ.get("TARGET_LAT", 46.9142))  # Băcioi
TARGET_LON = float(os.environ.get("TARGET_LON", 28.8878))  # Băcioi
ALLOWED_RADIUS_KM = float(os.environ.get("ALLOWED_RADIUS_KM", 15.0))
PORT = int(os.environ.get("PORT", 10000))

# AICI PUI LINK-UL NORMAL AL CANALULUI TĂU PRIVATE (CEL FĂRĂ APROBARE)
CHANNEL_INVITE_LINK = os.environ.get("CHANNEL_LINK", "https://t.me")

def haversine(lon1, lat1, lon2, lat2):
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a)) 
    return c * 6371

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Când omul dă click pe link-ul botului, îi cere direct locația fără text complicat"""
    keyboard = [[KeyboardButton(text="📍 Verifică Locația / Verify Location", request_location=True)]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text(
        "Salut! Pentru a intra pe canalul nostru local, apasă pe butonul de mai jos pentru a trimite locația curentă.\n\n"
        "Hi! To join our local community, press the button below to verify your location.",
        reply_markup=reply_markup
    )

async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    location = update.message.location
    distance = haversine(location.longitude, location.latitude, TARGET_LON, TARGET_LAT)
    
    if distance <= ALLOWED_RADIUS_KM:
        await update.message.reply_text(
            f"✅ Locație confirmată! Ești în zonă. Apasă pe link-ul de mai jos pentru a intra pe canal:\n\n👉 {CHANNEL_INVITE_LINK}",
            reply_markup=ReplyKeyboardRemove(),
            disable_web_page_preview=True
        )
    else:
        await update.message.reply_text(
            "❌ Ne pare rău, ești în afara razei permise pentru acest canal local.",
            reply_markup=ReplyKeyboardRemove()
        )

class WebhookServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"Bot is active!")

def run_web_server():
    server = HTTPServer(('0.0.0.0', PORT), WebhookServer)
    server.serve_forever()

def main():
    web_thread = threading.Thread(target=run_web_server, daemon=True)
    web_thread.start()

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.LOCATION, handle_location))
    app.run_polling()

if __name__ == '__main__':
    main()
