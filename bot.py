import logging
import random
import json
from datetime import datetime
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
)
import requests
from apscheduler.schedulers.background import BackgroundScheduler
from pymongo import MongoClient

HUGGING_FACE_API_TOKEN = "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"

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load KJV Bible Data
with open("kjv.json") as f:
    BIBLE = json.load(f)

# MongoDB Setup (Free Tier on MongoDB Atlas recommended)
MONGO_URI = "mongodb+srv://bible:bible@cluster0.uc77o.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
db_client = MongoClient(MONGO_URI)
db = db_client["bible_bot"]
users = db["users"]

# Scheduler Setup
scheduler = BackgroundScheduler()
scheduler.start()

# Logging Channel ID
LOG_CHANNEL_ID = -1002351224104  # Replace with your actual channel ID

# Helper Functions
def get_random_verse():
    """Fetch a random Bible verse."""
    book = random.choice(list(BIBLE.keys()))
    chapter = random.choice(list(BIBLE[book].keys()))
    verse = random.choice(list(BIBLE[book][chapter].keys()))
    text = BIBLE[book][chapter][verse]
    timestamp = datetime.now().strftime("%H:%M")
    return f"{text} ({timestamp})", book, chapter, verse

def explain_verse(verse_text, tone="calm"):
    """Generate an explanation for a verse using Hugging Face API."""
    headers = {
        "Authorization": f"Bearer {HUGGING_FACE_API_TOKEN}"
    }
    payload = {
        "inputs": f"Explain this Bible verse in a {tone} way: {verse_text}",
        "parameters": {"max_length": 100}
    }
    try:
        response = requests.post(
            "https://api-inference.huggingface.co/models/distilgpt2", 
            headers=headers, 
            json=payload
        )
        response.raise_for_status()  # Will raise an HTTPError if the response code is not 200
        return response.json()[0]["generated_text"]
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to generate explanation: {e}")
        return "Sorry, I couldn't generate an explanation right now."

async def log_message(context, user_id, user_message, bot_reply):
    """Log user messages and bot replies to the specified channel."""
    try:
        await context.bot.send_message(
            chat_id=LOG_CHANNEL_ID,
            text=f"**User ID**: {user_id}\n"
                 f"**User Message**: {user_message}\n"
                 f"**Bot Reply**: {bot_reply}"
        )
    except Exception as e:
        logger.error(f"Failed to log message: {e}")

# Command Handlers
async def start(update: Update, context):
    """Start command handler."""
    user = update.effective_user
    if not users.find_one({"user_id": user.id}):
        users.insert_one({"user_id": user.id, "username": user.username, "morning_subscribed": True})
    await update.message.reply_text(
        "Welcome to the KJV Bible Bot! Feel free to ask questions or share your feelings, and I'll reply with a Bible verse!"
    )

async def random_verse(update: Update, context):
    """Send a random Bible verse."""
    verse, book, chapter, verse_number = get_random_verse()
    context.user_data["last_verse"] = (verse, book, chapter, verse_number)
    await update.message.reply_text(verse)
    await log_message(context, update.effective_user.id, "/random", verse)

async def plain_text_response(update: Update, context):
    """Handle plain text messages with Bible verses and explanations."""
    user_message = update.message.text
    # Find a random verse
    verse, book, chapter, verse_number = get_random_verse()
    explanation = explain_verse(verse, tone="calm")
    response = f"{verse}\n\n{explanation}"
    await update.message.reply_text(response)
    # Log the interaction
    await log_message(context, update.effective_user.id, user_message, response)

# Scheduler Job
def send_morning_verses():
    """Send morning verses to all subscribed users."""
    subscribed_users = users.find({"morning_subscribed": True})
    verse, book, chapter, verse_number = get_random_verse()
    for user in subscribed_users:
        try:
            context.bot.send_message(
                chat_id=user["user_id"],
                text=f"Good morning! Here's your verse:\n{verse}\n{book} {chapter}:{verse_number}"
            )
        except Exception as e:
            logger.error(f"Error sending verse to {user['user_id']}: {e}")

# Add Job to Scheduler
scheduler.add_job(send_morning_verses, "cron", hour=8, minute=0)

# Main Function
if __name__ == "__main__":
    app = ApplicationBuilder().token("YOUR_BOT_API_TOKEN_HERE").build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("random", random_verse))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, plain_text_response))

    logger.info("Bot started.")
    app.run_polling()
