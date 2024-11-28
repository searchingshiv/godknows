import logging
import random
import json
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes
from telegram.ext.filters import TEXT

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Replace these with your Telegram bot token
TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
WEB_JSON_FILE_PATH = "web.json"  # Path to the web.json file in your repo

# Helper function to send error messages
async def send_error_message(update: Update, context: ContextTypes.DEFAULT_TYPE, error_message: str):
    """Send an error message to the user."""
    try:
        await update.message.reply_text(f"Sorry, an error occurred:\n\n{error_message}")
    except Exception as e:
        # In case replying fails, log the error
        logger.error(f"Failed to send error message: {e}")

# Fetch the web.json file from local file system
async def fetch_bible_data():
    """Fetch the Bible data (web.json) from the local file system."""
    try:
        if os.path.exists(WEB_JSON_FILE_PATH):
            with open(WEB_JSON_FILE_PATH, 'r') as f:
                data = json.load(f)
                return data
        else:
            logger.error(f"{WEB_JSON_FILE_PATH} not found.")
            return None
    except Exception as e:
        logger.error(f"Error reading the Bible data from file: {e}")
        return None

# Fetch a random Bible verse from the web.json data
async def get_random_bible_verse():
    """Fetch a random Bible verse from the web.json."""
    data = await fetch_bible_data()
    if data and 'verses' in data:
        verse = random.choice(data['verses'])
        book_name = verse['book_name']
        chapter = verse['chapter']
        verse_number = verse['verse']
        text = verse['text']
        return f"{book_name} {chapter}:{verse_number} - {text}"
    else:
        return "Sorry, I couldn't fetch a Bible verse at this time."

# Start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command handler."""
    await update.message.reply_text(
        "Welcome to the Bible Bot! Use /randomverse to get a random Bible verse or send any text to get an explanation."
    )

# Random verse command handler
async def random_verse(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /randomverse command."""
    try:
        verse = await get_random_bible_verse()
        await update.message.reply_text(f"Here's a random Bible verse:\n\n{verse}")
    except Exception as e:
        logger.exception("Failed to fetch random verse.")
        await send_error_message(update, context, "Sorry, I couldn't fetch a random verse right now. Please try again later.")

# Handle user text messages (for verse explanations)
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle user text messages."""
    try:
        user_message = update.message.text
        # Implement logic to explain the verse if necessary (e.g., using a Hugging Face API or a predefined explanation)
        explanation = f"Explanation for: {user_message}"  # Placeholder explanation
        await update.message.reply_text(f"Here's an explanation:\n\n{explanation}")
    except Exception as e:
        logger.exception("Failed to handle text message.")
        await send_error_message(update, context, "Sorry, I couldn't process your message. Please try again later.")

# Help command handler
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    await update.message.reply_text(
        "/start - Start the bot and get instructions\n"
        "/randomverse - Get a random Bible verse\n"
        "Send any text to get an explanation."
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
