import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.base import JobLookupError
from datetime import time
import random
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Define bot token
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
HUGGINGFACE_API_TOKEN = os.getenv("HUGGINGFACE_API_TOKEN")  # Use correct env var for token

# Initialize the bot application
application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
job_queue = application.job_queue  # Initialize the JobQueue

# Get a random Bible verse from a free API
def get_random_bible_verse():
    try:
        response = requests.get("https://labs.bible.org/api/?passage=random&type=json")
        if response.status_code == 200:
            data = response.json()[0]
            verse = f"{data['bookname']} {data['chapter']}:{data['verse']} - {data['text']}"
            return verse
        else:
            return "John 3:16 - For God so loved the world..."
    except Exception as e:
        print(f"Error fetching Bible verse: {e}")
        return "John 3:16 - For God so loved the world..."

# Get a Bible verse explanation dynamically using free AI
def get_bible_explanation(verse):
    prompt = f"Explain the meaning of the Bible verse: {verse}"
    try:
        response = requests.post(
            "https://api-inference.huggingface.co/models/bigscience/bloom",
            headers={"Authorization": f"Bearer {HUGGINGFACE_API_TOKEN}"},
            json={"inputs": prompt},
        )
        if response.status_code == 200:
            generated_text = response.json().get("generated_text", "")
            return generated_text or "This verse reminds us to reflect on God's love and teachings."
        else:
            return "This verse reminds us to reflect on God's love and teachings."
    except Exception as e:
        print(f"Error generating explanation: {e}")
        return "This verse reminds us to reflect on God's love and teachings."

# Handle text messages
async def handle_message(update: Update, context):
    user_message = update.message.text
    bot = context.bot
    user_id = update.message.chat_id

    verse = get_random_bible_verse()
    explanation = get_bible_explanation(verse)
    reply = f"Here's a verse for you: {verse}\nExplanation: {explanation}"

    await bot.send_message(chat_id=user_id, text=reply)

# Send a scheduled Bible verse every morning
async def send_morning_verse(context):
    chat_id = context.job.data["chat_id"]  # Extract chat_id from job.data
    bot = context.bot
    verse = get_random_bible_verse()
    explanation = get_bible_explanation(verse)
    await bot.send_message(chat_id=chat_id, text=f"Good morning! Here's your Bible verse: {verse}\nExplanation: {explanation}")

# Start command handler
async def start(update: Update, context):
    user_id = update.message.chat_id
    try:
        job_queue.run_daily(
            send_morning_verse,
            time=time(7, 0, 0),
            data={"chat_id": user_id},  # Pass chat_id using job.data
        )
        await update.message.reply_text("Welcome! I will send you a Bible verse every morning.")
    except JobLookupError:
        await update.message.reply_text("You are already subscribed for daily Bible verses.")

# Random verse command handler
async def random_verse(update: Update, context):
    verse = get_random_bible_verse()
    explanation = get_bible_explanation(verse)
    await update.message.reply_text(f"Here's a random Bible verse: {verse}\nExplanation: {explanation}")

# Add handlers to the application
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("randomverse", random_verse))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# Start the bot
if __name__ == "__main__":
    application.run_polling()
