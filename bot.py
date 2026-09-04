import os
import logging
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from math import radians, cos, sin, asin, sqrt
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, ChatJoinRequestHandler, filters, ContextTypes

# Setup loguri profesionale
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# CONFIGURAȚIE SECURIZATĂ (Preluată din Render Environment Variables)
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
TARGET_LAT = float(os.environ.get("TARGET_LAT", 46.9142))  # Coordonate Băcioi
TARGET_LON = float(os.environ.get("TARGET_LON", 28.8878))  # Coordonate Băcioi
ALLOWED_RADIUS_KM = float(os.environ.get("ALLOWED_RADIUS_KM", 15.0)) # Rază de 15km
PORT = int(os.environ.get("PORT", 10000))
CHANNEL_INVITE_LINK = os.environ.get("CHANNEL_LINK", "https://t.me")

# Dicționar global pentru a stoca utilizatorii verificați și timpul verificării
VERIFIED_USERS = {}

def haversine(lon1, lat1, lon2, lat2):
    """Calculează distanța exactă în kilometri dintre două coordonate GPS"""
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a)) 
    return c * 6371

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mesaj de pornire curat, trimis direct utilizatorului când dă click pe link-ul botului"""
    keyboard = [[KeyboardButton(text="📍 Trimite Locația Curentă", request_location=True)]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    await update.message.reply_text(
        "👋 **Salut!** Pentru a primi acces pe canalul nostru local, trebuie să verificăm că ești din zonă.\n\n"
        "Te rugăm să apeși pe butonul de mai jos pentru a trimite locația ta curentă.",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Procesează coordonatele trimise și validează utilizatorul pe bază de ID unic"""
    user_id = update.effective_user.id
    location = update.message.location
    
    # Calculăm distanța față de centrul stabilit (Băcioi)
    distance = haversine(location.longitude, location.latitude, TARGET_LON, TARGET_LAT)
    logger.info(f"Utilizatorul {user_id} a trimis locația. Distanța: {distance:.2f} km.")
    
    if distance <= ALLOWED_RADIUS_KM:
        # Salvăm ID-ul utilizatorului și timestamp-ul curent în baza de date locală
        VERIFIED_USERS[user_id] = time.time()
        
        await update.message.reply_text(
            f"✅ **Locație confirmată cu succes!** Ești în zona permisă.\n\n"
            f"Apasă pe link-ul de mai jos pentru a trimite cererea de intrare pe canal:\n"
            f"👉 {CHANNEL_INVITE_LINK}\n\n"
            "_*Notă: Botul te va accepta automat în canal în câteva secunde după ce ai trimis cererea! Link-ul este valabil doar pentru contul tău._",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode="Markdown",
            disable_web_page_preview=True
        )
    else:
        await update.message.reply_text(
            "❌ **Acces Respins.** Ne pare rău, ești în afara razei permise pentru acest canal local.",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode="Markdown"
        )

async def auto_approve_join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sistemul Antiglonț: Interceptează cererea din canal și lasă doar ID-ul aprobat"""
    join_request = update.chat_join_request
    user_id = join_request.from_user.id
    chat_id = join_request.chat.id
    
    current_time = time.time()
    
    # Verificăm dacă ID-ul unic se află în lista celor verificați și dacă verificarea s-a făcut în ultimele 10 minute
    if user_id in VERIFIED_USERS and (current_time - VERIFIED_USERS[user_id] < 600):
        try:
            await context.bot.approve_chat_join_request(chat_id=chat_id, user_id=user_id)
            logger.info(f"🛡️ SCUT: Botul l-a aprobat AUTOMAT pe utilizatorul autorizat {user_id}.")
            # Ștergem ID-ul din listă după ce a intrat cu succes pentru securitate maximă
            del VERIFIED_USERS[user_id]
        except Exception as e:
            logger.error(f"Eroare la aprobarea automată: {e}")
    else:
        # Dacă ID-ul NU a fost verificat (a primit link-ul furat), botul îi dă REJECT instant la ușă
        try:
            await context.bot.decline_chat_join_request(chat_id=chat_id, user_id=user_id)
            logger.warning(f"🚨 ALERTĂ FRAUDĂ: Botul a RESPINS utilizatorul neautorizat {user_id} (Link furat).")
        except Exception as e:
            logger.error(f"Eroare la respingerea utilizatorului neautorizat: {e}")

# SERVER WEB INTEGRAT PENTRU PASAREA CONTROALELOR RENDER (PASTREAZĂ SERVICIUL GRATUIT)
class RenderHealthServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"Scutul de securitate locala este activ si ruleaza 24/7!")

def run_web_server():
    server = HTTPServer(('0.0.0.0', PORT), RenderHealthServer)
    server.serve_forever()

def main():
    # Pornim serverul de păcălire a verificărilor Render în fundal
    web_thread = threading.Thread(target=run_web_server, daemon=True)
    web_thread.start()

    # Pornim motorul principal al botului de Telegram
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.LOCATION, handle_location))
    app.add_handler(ChatJoinRequestHandler(auto_approve_join_request))
    
    logger.info("Botul pornește bucla de monitorizare securizată...")
    app.run_polling()

if __name__ == '__main__':
    main()
