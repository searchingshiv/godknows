import logging
import random
import json
import os
import aiohttp
import datetime
from pyrogram import Client, filters
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import google.generativeai as genai

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Replace these with your tokens and API keys
API_ID = 25833520  # Replace with your Telegram API ID
API_HASH = "7d012a6cbfabc2d0436d7a09d8362af7"  # Replace with your Telegram API hash
BOT_TOKEN = "7112230953:AAHPPXd8-2_H1jJ1S1hYP2CuR7HOPx9LyuM"  # Replace with your bot token
GOOGLE_AI_API_KEY = "AIzaSyCagXIk1RudmoinloSRyLasw21Vo2-pzhQ"
WEB_JSON_FILE_PATH = "web.json"  # Path to web.json in your repo
genai.configure(api_key=GOOGLE_AI_API_KEY)
# Initialize the Pyrogram client
app = Client("bible_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Scheduler for daily tasks
scheduler = AsyncIOScheduler()

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
        # Use the Gemini model to generate content
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(f"Explain this Bible verse in one or two sentences in cherish way:\n\n{verse}")
        
        explanation = response.text.strip()
        if explanation and len(explanation.split()) > 5:
            return explanation
        logger.warning("Incomplete or invalid explanation received.")
    except Exception as e:
        logger.exception(f"Error fetching explanation: {e}")

    # Fallback explanation if the API fails
    return (
        "This verse offers timeless wisdom, encouraging reflection on spiritual truths and their application to life."
    )

# Command: /start
@app.on_message(filters.command("start"))
async def start(client, message):
    """Schedule a daily Bible verse at 9 AM."""
    chat_id = message.chat.id

    def send_daily_verse():
        app.loop.create_task(send_morning_verse(chat_id))

    # Add the daily task to the scheduler
    scheduler.add_job(
        send_daily_verse,
        CronTrigger(hour=9, minute=0, timezone="UTC"),  # Adjust timezone if necessary
        id=str(chat_id),
        replace_existing=True,
    )

    await message.reply_text("You will receive a Bible verse every morning at 9 AM.")

# Command: /randomverse
@app.on_message(filters.command("randomverse"))
async def random_verse(client, message):
    """Send a random Bible verse."""
    try:
        verse = get_random_verse()
        explanation = await get_bible_explanation(verse)
        await message.reply_text(f"Here's a random Bible verse:\n\n{verse}\n\nExplanation: {explanation}")
    except Exception as e:
        logger.exception("Failed to fetch random verse")
        await message.reply_text("Sorry, I couldn't fetch a verse right now. Please try again later.")

# Handle user messages
@app.on_message(filters.text & ~filters.regex("^/"))
async def handle_text(client, message):
    """Handle user text messages and suggest an uplifting verse."""
    try:
        user_message = message.text
        # Request the AI to suggest a relevant uplifting Bible verse based on user input
        prompt = f"Suggest an uplifting Bible verse related to this: {user_message} and explain it in cherish way."
        
        # Call Gemini API to generate an uplifting verse and explanation
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        
        # Extract the verse and explanation from the AI's response
        result = response.text.strip()
        if result:
            # Split the response into the verse and explanation (assuming the format is "Verse - Explanation")
            verse, explanation = result.split(' - ', 1) if ' - ' in result else (result, "No explanation provided.")
            # Send the uplifting verse and its explanation to the user
            await message.reply_text(f"Here’s an uplifting verse for you:\n\n{verse}\n\nExplanation: {explanation}")
        else:
            await message.reply_text("Sorry, I couldn't find an uplifting verse for you. Please try again later.")
    except Exception as e:
        logger.exception("Failed to handle user text message")
        await message.reply_text("Sorry, I couldn't process your message. Please try again later.")

# Send a morning verse
async def send_morning_verse(chat_id):
    """Send a morning Bible verse."""
    try:
        verse = get_random_verse()
        explanation = await get_bible_explanation(verse)
        await app.send_message(chat_id, f"Good morning! Here's your Bible verse:\n\n{verse}\n\nExplanation: {explanation}")
    except Exception as e:
        logger.exception("Error sending morning verse")
        await app.send_message(chat_id, "Sorry, I couldn't fetch the verse this morning. Please try again later.")

# Command: /help
@app.on_message(filters.command("help"))
async def help_command(client, message):
    """Provide help information."""
    await message.reply_text(
        "/start - Schedule daily Bible verses at 9 AM\n"
        "/randomverse - Get a random Bible verse\n"
        "Send any text to get an explanation of a verse."
    )

# Start the bot
if __name__ == "__main__":
    scheduler.start()
    app.run()
