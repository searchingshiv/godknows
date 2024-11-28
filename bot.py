import logging
import random
import json
import os
import datetime
import aiohttp
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes
from telegram.ext.filters import TEXT

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Replace these with your tokens
TELEGRAM_BOT_TOKEN = "7112230953:AAFCXqfbPPKDjyhqMR2kB79-va6r41hL5k4"
GOOGLE_AI_API_KEY = "AIzaSyCdocRvo6hW-BwramnILdHzej6LHUDMoAc"
WEB_JSON_FILE_PATH = "web.json"  # Path to web.json in your repo

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
    """Fetch an explanation for the verse using Google AI Studio API."""
    url = "https://aistudio.google.com/apikey"
    headers = {"Authorization": f"Bearer {GOOGLE_AI_API_KEY}"}
    payload = {
        "prompt": (
            f"Provide a concise and insightful explanation for the following Bible verse:\n\n"
            f"{verse}\n\n"
            "The explanation should be clear, meaningful, and limited to one or two sentences."
        ),
        "max_tokens": 100,
    }

    for attempt in range(3):  # Retry logic
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        explanation = data.get("choices", [{}])[0].get("text", "").strip()

                        # Validate explanation
                        if explanation and len(explanation.split()) > 5:
                            return explanation
                        logger.warning("Incomplete or invalid explanation received.")
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1}: Error fetching explanation: {e}")

    # Fallback explanation
    return (
        "This verse offers timeless wisdom, encouraging reflection on spiritual truths and their application to life."
    )

# Send a morning verse
async def send_morning_verse(context: ContextTypes.DEFAULT_TYPE):
    """Send a morning Bible verse."""
    chat_id = context.job.context
    try:
        verse = get_random_verse()
        explanation = await get_bible_explanation(verse)
        await context.bot.send_message(chat_id=chat_id, text=f"Good morning! Here's your Bible verse:\n\n{verse}\n\nExplanation: {explanation}")
    except Exception as e:
        logger.exception("Error sending morning verse")
        await context.bot.send_message(chat_id=chat_id, text="Sorry, I couldn't fetch the verse this morning. Please try again later.")

# Start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command to schedule daily Bible verses."""
    try:
        chat_id = update.message.chat_id
        # Schedule a daily verse at 9 AM
        context.job_queue.run_daily(
            callback=send_morning_verse,
            time=datetime.time(hour=9, minute=0),
            context=chat_id,
            name=f"morning_verse_{chat_id}",
        )
        await update.message.reply_text("You will receive a Bible verse every morning at 9 AM.")
    except Exception as e:
        logger.exception("Error scheduling daily verse")
        await update.message.reply_text("Failed to schedule daily Bible verses. Please try again.")

# Random verse command handler
async def random_verse(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /randomverse command."""
    try:
        verse = get_random_verse()
        explanation = await get_bible_explanation(verse)
        await update.message.reply_text(f"Here's a random Bible verse:\n\n{verse}\n\nExplanation: {explanation}")
    except Exception as e:
        logger.exception("Failed to fetch random verse")
        await update.message.reply_text("Sorry, I couldn't fetch a verse right now. Please try again later.")

# Handle user text messages
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle user text messages."""
    try:
        user_message = update.message.text
        response = await get_bible_explanation(user_message)
        await update.message.reply_text(f"Here's an explanation:\n\n{response}")
    except Exception as e:
        logger.exception("Failed to handle text message")
        await update.message.reply_text("Sorry, I couldn't process your message. Please try again later.")

# Help command handler
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    await update.message.reply_text(
        "/start - Schedule daily Bible verses at 9 AM\n"
        "/randomverse - Get a random Bible verse\n"
        "Send any text to get an explanation of a verse."
    )

# Main function to run the bot
def main():
    """Run the bot."""
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("randomverse", random_verse))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(TEXT, handle_text))

    # Start the bot
    application.run_polling()

if __name__ == "__main__":
    main()
