import os
import logging
from math import radians, cos, sin, asin, sqrt
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import Application, ChatJoinRequestHandler, MessageHandler, filters, ContextTypes

# Setup logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# CONFIGURATION (Loaded from environment variables for security)
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
TARGET_LAT = float(os.environ.get("TARGET_LAT", 46.9142))  # Default: Băcioi
TARGET_LON = float(os.environ.get("TARGET_LON", 28.8878))  # Default: Băcioi
ALLOWED_RADIUS_KM = float(os.environ.get("ALLOWED_RADIUS_KM", 15.0)) # 15km Radius

def haversine(lon1, lat1, lon2, lat2):
    """Calculate the great circle distance between two points on the earth."""
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a)) 
    r = 6371 # Radius of earth in kilometers
    return c * r

async def handle_join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Triggered when someone clicks your private link request"""
    join_request = update.chat_join_request
    user_id = join_request.from_user.id
    chat_id = join_request.chat.id
    
    # Store user details temporarily
    context.bot_data[f"user_{user_id}"] = chat_id
    logger.info(f"Join request received from user {user_id} for chat {chat_id}")

    # Build the location sharing button
    keyboard = [[KeyboardButton(text="📍 Distribue Locația / Share Location", request_location=True)]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text="Salut! Pentru a te alătura canalului nostru local, te rugăm să îți verifici locația curentă.\n\n"
                 "Hi! To join our local community, please verify your current location by pressing the button below.",
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Could not send DM to user {user_id}: {e}")

async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processes user's shared GPS coordinates"""
    user_id = update.effective_user.id
    location = update.message.location
    
    chat_id = context.bot_data.get(f"user_{user_id}")
    if not chat_id:
        await update.message.reply_text("Nu am găsit nicio cerere de înscriere activă. / No active join request found.")
        return

    distance = haversine(location.longitude, location.latitude, TARGET_LON, TARGET_LAT)
    logger.info(f"User {user_id} is {distance:.2f} km away from target location.")

    if distance <= ALLOWED_RADIUS_KM:
        try:
            # Approve user into channel
            await context.bot.approve_chat_join_request(chat_id=chat_id, user_id=user_id)
            await update.message.reply_text(
                "✅ Locație confirmată! Cererea ta a fost aprobată. Bine ai venit pe canal!\n\n"
                "✅ Location verified! Your request has been approved. Welcome to the channel!",
                reply_markup=ReplyKeyboardRemove()
            )
            # Clean data
            del context.bot_data[f"user_{user_id}"]
        except Exception as e:
            logger.error(f"Failed to approve user {user_id}: {e}")
    else:
        await update.message.reply_text(
            f"❌ Ne pare rău, ești în afara razei permise pentru acest grup local.\n\n"
            f"❌ Sorry, you are outside the permitted radius for this local group.",
            reply_markup=ReplyKeyboardRemove()
        )

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(ChatJoinRequestHandler(handle_join_request))
    app.add_handler(MessageHandler(filters.LOCATION, handle_location))
    logger.info("Bot is starting up...")
    app.run_polling()

if __name__ == '__main__':
    main()
