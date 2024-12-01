import logging
import random
import json
import os
from pyrogram import Client, filters
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from pytz import timezone
import google.generativeai as genai
from flask import Flask
from threading import Thread
from pyrogram import utils

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Replace these with environment variables
API_ID = int(os.getenv("API_ID", "25833520"))  # Replace with your Telegram API ID
API_HASH = os.getenv("API_HASH", "7d012a6cbfabc2d0436d7a09d8362af7")  # Replace with your Telegram API hash
BOT_TOKEN = os.getenv("BOT_TOKEN", "7112230953:AAHOEjToGy4jipliOK2NBiu6ai8gNoWv5tg")  # Replace with your bot token
GOOGLE_AI_API_KEY = os.getenv("GOOGLE_AI_API_KEY", "")
WEB_JSON_FILE_PATH = "web.json"  # Path to web.json in your repo
genai.configure(api_key=GOOGLE_AI_API_KEY)

# Initialize the Pyrogram client
app = Client("bible_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Scheduler for daily tasks
scheduler = AsyncIOScheduler()

# Initialize Flask app for deployment
flask_app = Flask(__name__)

# Timezone for scheduling
IST = timezone("Asia/Kolkata")  # Adjust the timezone as required

# Fix peer type issues in Pyrogram
def get_peer_type_new(peer_id: int) -> str:
    peer_id_str = str(peer_id)
    if not peer_id_str.startswith("-"):
        return "user"
    elif peer_id_str.startswith("-100"):
        return "channel"
    else:
        return "chat"

utils.get_peer_type = get_peer_type_new

# Helper function to load Bible data
def load_bible_data():
    """Load Bible data from web.json."""
    try:
        if os.path.exists(WEB_JSON_FILE_PATH):
            with open(WEB_JSON_FILE_PATH, 'r') as f:
                return json.load(f)
        else:
            logger.error(f"{WEB_JSON_FILE_PATH} not found.")
            return None
    except Exception as e:
        logger.exception("Error loading Bible data")
        return None

# Fetch a random Bible verse
def get_random_verse():
    """Fetch a random verse from the Bible data."""
    data = load_bible_data()
    if data and "verses" in data:
        verse = random.choice(data["verses"])
        return f"{verse['book_name']} {verse['chapter']}:{verse['verse']} - {verse['text']}"
    return "John 3:16 - For God so loved the world..."

# Fetch explanation for a verse using Google AI Studio
async def get_bible_explanation(verse):
    """Fetch an explanation for the verse using Google AI's Gemini API."""
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(
            f"Explain this Bible verse in 2-3 lines and in a compassionate and uplifting way:\n\n{verse}"
        )
        explanation = response.text.strip()
        if explanation and len(explanation.split()) > 5:
            return explanation
        logger.warning("Incomplete or invalid explanation received.")
    except Exception as e:
        logger.exception(f"Error fetching explanation: {e}")

    return (
        "This verse offers timeless wisdom, encouraging reflection on spiritual truths and their application to life."
    )

# Send a reply with a picture from the environment variable
async def reply_with_image(client, chat_id, text):
    """Send a text reply with an accompanying random image."""
    image_links = os.getenv("RANDOM_IMAGES", "").split(",")  # Get the image links from env variable
    if image_links:
        image_path = random.choice(image_links)  # Pick a random image from the list
        try:
            await client.send_photo(chat_id, photo=image_path, caption=text)
        except Exception as e:
            logger.warning(f"Error sending image: {e}")
            await client.send_message(chat_id, text)
    else:
        logger.warning("No image links found in the environment variable.")
        await client.send_message(chat_id, text)

# Helper function to log user messages and bot responses
async def log_to_channel(client, user_message, bot_response):
    """Log user messages and bot responses to the specified log channel."""
    log_channel_id = os.getenv("LOG_CHANNEL_ID")  # Get the log channel ID from environment variable
    if log_channel_id:
        log_text = f"User Message: {user_message}\nBot Response: {bot_response}"
        await client.send_message(log_channel_id, log_text)
    else:
        logger.warning("LOG_CHANNEL_ID not set in environment variables.")

# Command: /start
@app.on_message(filters.command("start"))
async def start(client, message):
    """Schedule a daily Bible verse at 9 AM."""
    chat_id = message.chat.id

    def send_daily_verse():
        app.loop.create_task(send_morning_verse(chat_id))

    scheduler.add_job(
        send_daily_verse,
        CronTrigger(hour=13, minute=0, timezone=IST),  # Adjusted to IST (Indian Standard Time)
        id=str(chat_id),
        replace_existing=True,
    )

    await message.reply_text("You’re now subscribed to daily Bible verses! 🎉")

# Command: /randomverse
@app.on_message(filters.command("randomverse"))
async def random_verse(client, message):
    """Send a random Bible verse."""
    try:
        verse = get_random_verse()
        explanation = await get_bible_explanation(verse)
        text = f"📖 **Here’s a random Bible verse:**\n\n_{verse}_\n\n💡 **Explanation:**\n{explanation}"
        await reply_with_image(client, message.chat.id, text)
        
        # Log the user message and bot response
        await log_to_channel(client, "Random verse requested", text)
    except Exception as e:
        logger.exception("Failed to fetch random verse")
        

# Handle user messages
@app.on_message(filters.text & ~filters.regex("^/"))
async def handle_text(client, message):
    """Handle user text messages and suggest an uplifting verse."""
    try:
        user_message = message.text
        prompt = f"Suggest an uplifting Bible verse in 3-4 lines related to this: {user_message}..... and explain it in a compassionate and uplifting way."
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        
        result = response.text.strip()
        if result:
            if ' - ' in result:
                verse, explanation = result.split(' - ', 1)
            else:
                verse = result
                explanation = "No explanation provided."
            
            if explanation == "No explanation provided." or len(explanation.split()) < 3:
                explanation = "This verse offers timeless wisdom, encouraging reflection on spiritual truths and their application to life."
            
            text = f"✨ **Listen Dear:**\n\n{verse}\n\n😌😌"
            await reply_with_image(client, message.chat.id, text)
            
            await log_to_channel(client, user_message, text)
        else:
            await message.reply_text("Sorry, I couldn’t find a verse for you. Please try again later.")
    except Exception as e:
        logger.exception("Failed to handle user text message")
        

# Send a morning verse
async def send_morning_verse(chat_id):
    """Send a morning Bible verse."""
    try:
        verse = get_random_verse()
        explanation = await get_bible_explanation(verse)
        text = f"🌅 **Good Morning!**\n\n📖 **Verse:**\n_{verse}_\n\n💡 **Explanation:**\n{explanation}"
        await reply_with_image(app, chat_id, text)
    except Exception as e:
        logger.exception("Error sending morning verse")
        await app.send_message(chat_id, "Sorry, I couldn’t fetch the verse this morning. Please try again later.")

# Command: /help
@app.on_message(filters.command("help"))
async def help_command(client, message):
    """Provide help information."""
    await message.reply_text(
        "Here are the available commands:\n"
        "/start - Subscribe to daily Bible verses at 9 AM\n"
        "/randomverse - Get a random Bible verse\n"
        "Send any text to get an uplifting verse and explanation!"
    )

# Flask route for Render deployment
@flask_app.route("/")
def home():
    return "Bible Bot is running!"

# Run Flask in a separate thread to avoid blocking Pyrogram's event loop
def run_flask():
    flask_app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))

# Run the bot and Flask in separate threads
if __name__ == "__main__":
    scheduler.start()

    # Run Flask in a separate thread
    flask_thread = Thread(target=run_flask)
    flask_thread.start()

    # Run the bot (Pyrogram)
    app.run()
