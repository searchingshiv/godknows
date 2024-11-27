import openai
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import random, os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get the environment variables using os.getenv
# TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Now you can use these variables securely
openai.api_key = OPENAI_API_KEY
# Define bot token
TELEGRAM_BOT_TOKEN = '7112230953:AAF4TdvJqCFV7bVXLsU9ITXVeNUik2ZJnSQ'

# Initialize the bot
updater = Updater(token=TELEGRAM_BOT_TOKEN, use_context=True)
dp = updater.dispatcher

# Log user messages and bot responses to a channel
LOG_CHANNEL = '@yourlogchannel'

def log_to_channel(message, reply):
    """Logs the user message and bot reply to the channel"""
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    log_message = f"User: {message}\nBot: {reply}"
    bot.send_message(chat_id=LOG_CHANNEL, text=log_message)

# Send a random Bible verse
def get_random_bible_verse():
    bible_verses = [
        # List of Bible verses
        "John 3:16 - For God so loved the world...",
        "Philippians 4:13 - I can do all things through Christ who strengthens me.",
        # Add more verses
    ]
    return random.choice(bible_verses)

# Get Bible verse explanation using OpenAI
def get_bible_explanation(verse):
    prompt = f"Explain the meaning of the Bible verse: {verse}"
    response = openai.Completion.create(
        engine="text-davinci-003", prompt=prompt, max_tokens=150
    )
    return response.choices[0].text.strip()

# Handle text messages
def handle_message(update, context):
    user_message = update.message.text
    bot = context.bot
    user_id = update.message.chat_id

    if user_message.lower() in ["happy", "sad", "confused"]:  # Example feelings
        verse = get_random_bible_verse()
        explanation = get_bible_explanation(verse)
        reply = f"Feeling {user_message}? Here's a verse for you: {verse}\nExplanation: {explanation}"
    else:
        verse = get_random_bible_verse()
        explanation = get_bible_explanation(verse)
        reply = f"Here's a verse for you: {verse}\nExplanation: {explanation}"

    bot.send_message(chat_id=user_id, text=reply)
    log_to_channel(user_message, reply)

# Send a scheduled Bible verse every morning
def send_morning_verse(context):
    bot = context.bot
    chat_id = context.job.context
    verse = get_random_bible_verse()
    explanation = get_bible_explanation(verse)
    bot.send_message(chat_id=chat_id, text=f"Good morning! Here's your Bible verse: {verse}\nExplanation: {explanation}")

def start(update, context):
    user_id = update.message.chat_id
    context.job_queue.run_daily(send_morning_verse, time=datetime.time(7, 0, 0), context=user_id)
    update.message.reply_text("Welcome! I will send you a Bible verse every morning.")

def random_verse(update, context):
    verse = get_random_bible_verse()
    explanation = get_bible_explanation(verse)
    update.message.reply_text(f"Here's a random Bible verse: {verse}\nExplanation: {explanation}")

# Add handlers
dp.add_handler(CommandHandler("start", start))
dp.add_handler(CommandHandler("randomverse", random_verse))
dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

# Start the bot
updater.start_polling()
updater.idle()
