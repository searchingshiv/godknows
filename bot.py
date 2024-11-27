import logging
import random
import requests
from telegram import Update, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    InlineQueryHandler,
)
import google.generativeai as genai  # Google Generative AI Library

# Logging setup
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG)

# API Keys (Replace with actual keys)
GOOGLE_AI_API_KEY = "AIzaSyDDYYI_AoAEztLU6GyQ09xhXK4g-VBKN9k"
BIBLE_API_ENDPOINT = "https://bible-api.com"  # Using base URL
TELEGRAM_BOT_TOKEN = "7112230953:AAFUPLFTb3z3BMpuwjVnnc1sLkTwBu--8Gc"
LOG_CHANNEL_ID = "-1002351224104"

# Configure Google Generative AI
genai.configure(api_key=GOOGLE_AI_API_KEY)

# List of Bible books (simplified list for demonstration, expand as needed)
bible_books = [
    "Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy", "Joshua", "Judges",
    "Psalms", "Proverbs", "Isaiah", "Matthew", "Mark", "Luke", "John", "Acts", "Romans"
]

# Fetch a random verse from Bible API (randomly choosing book, chapter, and verse)
def get_random_verse():
    book = random.choice(bible_books)
    chapter = random.randint(1, 50)  # Example: Choose a random chapter between 1 and 50
    verse = random.randint(1, 30)  # Example: Choose a random verse between 1 and 30

    # Construct the API URL for the random verse
    url = f"{BIBLE_API_ENDPOINT}/{book}+{chapter}:{verse}"
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        return data['reference'], data['text']
    return "John 3:16", "For God so loved the world..."  # Default fallback

# AI-based explanation using Google Generative AI
def get_ai_explanation(verse_text):
    try:
        response = genai.generate_text(
            model="gemini-1.5-flash",  # Use appropriate model
            prompt=f"Explain this Bible verse: {verse_text}",
        )
        return response.candidates[0].output  # Return the explanation from AI
    except Exception as e:
        logging.error(f"Error generating AI explanation: {e}")
        return "Explanation not available."

# Handle user messages
async def handle_message(update: Update, context):
    user_message = update.message.text
    # Log the user message
    await context.bot.send_message(chat_id=LOG_CHANNEL_ID, text=f"User: {user_message}")
    
    # Fetch a relevant Bible verse
    verse, verse_text = get_random_verse()
    explanation = get_ai_explanation(verse_text)
    
    # Respond to the user
    response = f"📖 *{verse}*\n_{verse_text}_\n\n💡 *Explanation:*\n{explanation}"
    await update.message.reply_text(response, parse_mode="Markdown")
    # Log bot's response
    await context.bot.send_message(chat_id=LOG_CHANNEL_ID, text=f"Bot: {response}")

# Inline Query Handler
async def inline_query(update: Update, context):
    query = update.inline_query.query
    if query == "":
        return
    verse, verse_text = get_random_verse()
    results = [
        InlineQueryResultArticle(
            id="1",
            title=verse,
            input_message_content=InputTextMessageContent(f"📖 *{verse}*\n_{verse_text}_", parse_mode="Markdown")
        )
    ]
    await update.inline_query.answer(results)

# Read Bible Command (for specific chapters)
async def read_bible(update: Update, context):
    chapter = " ".join(context.args) or "Genesis 1"
    response = requests.get(f"{BIBLE_API_ENDPOINT}/read?chapter={chapter}")
    if response.status_code == 200:
        chapter_text = response.json().get("text", "Chapter not available.")
        await update.message.reply_text(f"📖 *{chapter}*\n{chapter_text}", parse_mode="Markdown")
    else:
        await update.message.reply_text("Could not fetch the requested chapter.")

# Start the bot with polling
def start_bot():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CommandHandler("read", read_bible))
    application.add_handler(InlineQueryHandler(inline_query))

    # Start polling for updates
    application.run_polling()

if __name__ == "__main__":
    # Start the bot
    start_bot()
