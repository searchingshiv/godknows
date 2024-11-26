import logging
import random
import json
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from transformers import pipeline
from apscheduler.schedulers.background import BackgroundScheduler
from pymongo import MongoClient

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load KJV Bible Data
with open("kjv.json") as f:  # Ensure you have the KJV Bible in JSON format
    BIBLE = json.load(f)

# Initialize AI Model
ai_model = pipeline("text-generation", model="distilgpt2")

# MongoDB Setup (Free Tier on MongoDB Atlas recommended)
MONGO_URI = "mongodb+srv://your_username:your_password@cluster0.mongodb.net/?retryWrites=true&w=majority"
db_client = MongoClient(MONGO_URI)
db = db_client["bible_bot"]
users = db["users"]

# Scheduler Setup
scheduler = BackgroundScheduler()
scheduler.start()

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
    """Generate an explanation for a verse in a given tone."""
    prompt = f"Explain this Bible verse in a {tone} and emotional way: {verse_text}"
    response = ai_model(prompt, max_length=100, num_return_sequences=1)
    return response[0]["generated_text"]

# Command Handlers
async def start(update: Update, context):
    """Start command handler."""
    user = update.effective_user
    if not users.find_one({"user_id": user.id}):
        users.insert_one({"user_id": user.id, "username": user.username, "morning_subscribed": True})
    await update.message.reply_text(
        "Welcome to the KJV Bible Bot! Use /help to see available commands."
    )

async def help_command(update: Update, context):
    """Help command handler."""
    await update.message.reply_text(
        "/start - Start the bot\n"
        "/random - Get a random Bible verse\n"
        "/explain - Get an explanation for the last verse\n"
        "/subscribe - Subscribe to morning verses\n"
        "/unsubscribe - Unsubscribe from morning verses"
    )

async def random_verse(update: Update, context):
    """Send a random Bible verse."""
    verse, book, chapter, verse_number = get_random_verse()
    context.user_data["last_verse"] = (verse, book, chapter, verse_number)
    await update.message.reply_text(verse)

async def explain(update: Update, context):
    """Explain the last sent verse."""
    if "last_verse" not in context.user_data:
        await update.message.reply_text("No verse to explain. Use /random first.")
        return
    verse, _, _, _ = context.user_data["last_verse"]
    explanation = explain_verse(verse, tone="calm")
    await update.message.reply_text(explanation)

async def subscribe(update: Update, context):
    """Subscribe user to morning verses."""
    user_id = update.effective_user.id
    users.update_one({"user_id": user_id}, {"$set": {"morning_subscribed": True}}, upsert=True)
    await update.message.reply_text("You are now subscribed to morning verses!")

async def unsubscribe(update: Update, context):
    """Unsubscribe user from morning verses."""
    user_id = update.effective_user.id
    users.update_one({"user_id": user_id}, {"$set": {"morning_subscribed": False}})
    await update.message.reply_text("You have unsubscribed from morning verses.")

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
    app = ApplicationBuilder().token("YOUR_TELEGRAM_BOT_TOKEN").build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("random", random_verse))
    app.add_handler(CommandHandler("explain", explain))
    app.add_handler(CommandHandler("subscribe", subscribe))
    app.add_handler(CommandHandler("unsubscribe", unsubscribe))

    logger.info("Bot started.")
    app.run_polling()
