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
import asyncio

HUGGING_FACE_API_TOKEN = "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"

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load KJV Bible Data
with open("kjv.json") as f:
    BIBLE = json.load(f)

# MongoDB Setup
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
    book_data = random.choice(BIBLE)
    book_name = book_data["abbrev"]
    chapters = book_data["chapters"]
    chapter_index = random.randint(0, len(chapters) - 1)
    verses = chapters[chapter_index]
    verse_index = random.randint(0, len(verses) - 1)
    verse_text = verses[verse_index]
    return f"{verse_text}", book_name, chapter_index + 1, verse_index + 1

def analyze_tone(user_message):
    """Analyze the tone of the user's message."""
    headers = {"Authorization": f"Bearer {HUGGING_FACE_API_TOKEN}"}
    payload = {"inputs": f"Analyze the sentiment of this text: {user_message}"}
    try:
        response = requests.post(
            "https://api-inference.huggingface.co/models/facebook/bart-large-mnli",
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        # Example tone labels; refine based on the API response structure
        labels = response.json()["labels"]
        if "sad" in labels:
            return "sadness"
        elif "happy" in labels:
            return "joy"
        elif "frustrated" in labels:
            return "frustration"
        elif "lonely" in labels:
            return "loneliness"
        elif "hopeful" in labels:
            return "hopeful"
        else:
            return "neutral"
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to analyze tone: {e}")
        return "neutral"

def explain_verse(verse_text, tone="uplifting"):
    """Generate an explanation for a verse using Hugging Face API."""
    headers = {"Authorization": f"Bearer {HUGGING_FACE_API_TOKEN}"}
    payload = {
        "inputs": f"Explain this Bible verse in an {tone} way: {verse_text}",
        "parameters": {"max_length": 100},
    }
    try:
        response = requests.post(
            "https://api-inference.huggingface.co/models/distilgpt2",
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        return response.json()[0]["generated_text"]
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to generate explanation: {e}")
        return "I'm sorry, I couldn't generate an explanation at the moment."

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
        "🌟 Welcome to the KJV Bible Bot! 🌟\n\n"
        "Feel free to share your thoughts or ask questions, and I'll respond with a meaningful Bible verse to uplift your spirit."
    )

async def random_verse(update: Update, context):
    """Send a random Bible verse."""
    verse, book, chapter, verse_number = get_random_verse()
    context.user_data["last_verse"] = (verse, book, chapter, verse_number)
    reply = f"📖 **{book} {chapter}:{verse_number}**\n\n*{verse}*"
    await update.message.reply_text(reply)
    await log_message(context, update.effective_user.id, "/random", reply)

async def plain_text_response(update: Update, context):
    """Handle plain text messages with context-aware replies."""
    user_message = update.message.text
    tone = analyze_tone(user_message)  # Analyze user's message
    verse, book, chapter, verse_number = get_random_verse()
    
    # Tone-specific responses
    tone_map = {
        "sadness": "comforting",
        "joy": "celebratory",
        "frustration": "calming",
        "loneliness": "empathetic",
        "hopeful": "encouraging",
        "neutral": "informative",
    }
    explanation = explain_verse(verse, tone=tone_map.get(tone, "uplifting"))
    reply = (
        f"📖 **{book} {chapter}:{verse_number}**\n\n"
        f"*{verse}*\n\n"
        f"💡 *Reflection*: {explanation}"
    )
    await update.message.reply_text(reply)
    await log_message(context, update.effective_user.id, user_message, reply)

# Scheduler Job
async def send_morning_verses_async():
    """Send morning verses to all subscribed users."""
    subscribed_users = users.find({"morning_subscribed": True})
    verse, book, chapter, verse_number = get_random_verse()
    for user in subscribed_users:
        try:
            app = ApplicationBuilder().token("7112230953:AAGAzaUtko1v1hlH8--yoyu8g4uiOg1-DFA").build()
            await app.bot.send_message(
                chat_id=user["user_id"],
                text=(
                    "🌅 **Good Morning!** 🌅\n\n"
                    f"Here's your verse for today:\n\n"
                    f"📖 **{book} {chapter}:{verse_number}**\n\n"
                    f"*{verse}*"
                )
            )
        except Exception as e:
            logger.error(f"Error sending verse to {user['user_id']}: {e}")

# Wrapper for Async Function
def send_morning_verses_sync():
    asyncio.run(send_morning_verses_async())

# Add Job to Scheduler
scheduler.add_job(send_morning_verses_sync, "cron", hour=8, minute=0)

# Main Function
if __name__ == "__main__":
    app = ApplicationBuilder().token("7112230953:AAGAzaUtko1v1hlH8--yoyu8g4uiOg1-DFA").build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("random", random_verse))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, plain_text_response))
     port = int(os.environ.get("PORT", 8443))  # Default to 8443 for local testing
    app.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path="",
        webhook_url=f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME', 'localhost')}/{TOKEN}"
    )

    logger.info("Bot started.")
    app.run_polling()
