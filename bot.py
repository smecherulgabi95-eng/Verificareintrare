import os
import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from math import radians, cos, sin, asin, sqrt
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import Application, ChatJoinRequestHandler, MessageHandler, filters, ContextTypes

# Setup logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# CONFIGURATION
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
TARGET_LAT = float(os.environ.get("TARGET_LAT", 46.9142))  # Băcioi
TARGET_LON = float(os.environ.get("TARGET_LON", 28.8878))  # Băcioi
ALLOWED_RADIUS_KM = float(os.environ.get("ALLOWED_RADIUS_KM", 15.0))
PORT = int(os.environ.get("PORT", 10000)) # Render passes a port variable automatically

def haversine(lon1, lat1, lon2, lat2):
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a)) 
    return c * 6371

async def handle_join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    join_request = update.chat_join_request
    user_id = join_request.from_user.id
    context.bot_data[f"user_{user_id}"] = join_request.chat.id
    keyboard = [[KeyboardButton(text="📍 Distribue Locația / Share Location", request_location=True)]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text="Salut! Pentru a te alătura canalului nostru local, te rugăm să îți verifici locația curentă.\n\nHi! To join our local community, please verify your current location.",
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Could not send DM: {e}")

async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    location = update.message.location
    chat_id = context.bot_data.get(f"user_{user_id}")
    if not chat_id:
        return
    distance = haversine(location.longitude, location.latitude, TARGET_LON, TARGET_LAT)
    if distance <= ALLOWED_RADIUS_KM:
        try:
            await context.bot.approve_chat_join_request(chat_id=chat_id, user_id=user_id)
            await update.message.reply_text("✅ Locație confirmată! Cererea ta a fost aprobată.\n\n✅ Location verified! Welcome!", reply_markup=ReplyKeyboardRemove())
            del context.bot_data[f"user_{user_id}"]
        except Exception as e:
            logger.error(f"Failed approval: {e}")
    else:
        await update.message.reply_text("❌ Ne pare rău, ești în afara razei permise.\n\n❌ Sorry, you are outside the permitted radius.", reply_markup=ReplyKeyboardRemove())

# DUMMY WEB SERVER TO TRICK RENDER HEALTH CHECKS
class WebhookServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"Bot is active and running cleanly!")

def run_web_server():
    server = HTTPServer(('0.0.0.0', PORT), WebhookServer)
    logger.info(f"Web server trick running on port {PORT}")
    server.serve_forever()

def main():
    # Start web server thread first so Render sees an active webpage port
    web_thread = threading.Thread(target=run_web_server, daemon=True)
    web_thread.start()

    # Start Telegram background bot loop
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(ChatJoinRequestHandler(handle_join_request))
    app.add_handler(MessageHandler(filters.LOCATION, handle_location))
    logger.info("Bot is starting up...")
    app.run_polling()

if __name__ == '__main__':
    main()
