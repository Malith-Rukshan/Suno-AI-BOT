# © [2024] Malith-Rukshan. All rights reserved.
# Repository: https://github.com/Malith-Rukshan/Suno-AI-BOT

import asyncio
import logging
import os

from telegram.constants import ParseMode
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, CallbackQueryHandler, filters
import suno

# Configure logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)

# Disable SunoAI Logs
# logging.getLogger("SunoAI").setLevel(logging.WARNING)

# Initialize Suno AI Library
SUNO_COOKIE = os.getenv("SUNO_COOKIE")
client = suno.Suno(cookie=SUNO_COOKIE)

# Store user session data
chat_states = {}

# Keyboard options for user selection
def get_base_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎨 Custom", callback_data="custom")],
        [InlineKeyboardButton("🏞️ Default", callback_data="default")]
    ])

# Welcome message with Markdown
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    welcome_message = (
        "👋 Hello! Welcome to the *Suno AI Music Generator Bot*! 🎶\n\n"
        "👉 Use /generate to start creating your unique music track. 🚀\n"
        "👉 Use /credits to check your credits balance.\n\n"
        "📥 This bot utilizes the [SunoAI API](https://github.com/Malith-Rukshan/Suno-API). You can also deploy your own version of this bot! For more details, visit our [GitHub repo](https://github.com/Malith-Rukshan/Suno-AI-BOT)."
    )

    await update.message.reply_markdown(welcome_message,disable_web_page_preview=False)

# Handler for the get credits
async def credits_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    credit_info_message = (
        "*💰Credits Stat*\n\n"
        "ᗚ Available : {}\n"
        "ᗚ Usage : {}"
    )
    try:
        credits = await asyncio.to_thread(client.get_credits)
    except Exception as e:
        return await update.message.reply_text(f"⁉️ Failed to get credits info: {e}")
    await update.message.reply_text(credit_info_message.format(credits.credits_left,credits.monthly_usage),parse_mode=ParseMode.MARKDOWN)

# Handler for the generate command
async def generate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Select mode: custom or not. 🤔', reply_markup=get_base_keyboard())
    chat_states[update.effective_chat.id] = {}

# Command to cancel and clear state
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    if chat_id in chat_states:
        del chat_states[chat_id]
    await update.message.reply_text('Generation canceled. 🚫 You can start again with /generate.')

# Handler for button presses
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    chat_id = int(update.effective_chat.id)
    chat_states[chat_id]['mode'] = query.data

    if query.data == "custom":
        await query.message.reply_text("🎤 Send lyrics first.")
    else:
        await query.message.reply_text("🎤 Send song description.")
    return await context.application.bot.delete_message(chat_id=query.message.chat.id,message_id=query.message.message_id)
        

async def onMessage(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = int(update.effective_chat.id)
    # Collects lyrics from the user
    if chat_id in chat_states and 'mode' in chat_states[chat_id]:
        if not 'lyrics' in chat_states[chat_id]:
            chat_states[chat_id]['lyrics'] = update.message.text
        if chat_states[chat_id].get('mode') == 'custom':
            if not (chat_id in chat_states and 'tags' in chat_states[chat_id] and "Wait-for-tags" == chat_states[chat_id]['tags']):
                chat_states[chat_id]['tags'] = "Wait-for-tags"
                return await update.message.reply_text("🏷️ Now send tags.\n\nExample : Classical")
    
    # Collects tags (if custom) / generates music
    if chat_id in chat_states and 'lyrics' in chat_states[chat_id]:
        if chat_states[chat_id].get('mode') == 'custom':
            # Custom music generation logic
            chat_states[chat_id]['tags'] = update.message.text
            await update.message.reply_text("Generating your music... please wait. ⏳")
            try:
                prompt = f"{chat_states[chat_id]['lyrics']}"
                tags = f"{chat_states[chat_id]['tags']}"
                
                # Generate Custom Music
                songs = await asyncio.to_thread(
                    client.generate,
                    prompt=prompt,
                    tags=tags,
                    is_custom=True,
                    wait_audio=True)

                for song in songs:
                    file_path = await asyncio.to_thread(client.download,song=song)
                    await context.bot.send_audio(chat_id=chat_id, audio=open(file_path, 'rb'), thumbnail=open("thumb.jpg", 'rb'))
                    os.remove(file_path)
                del chat_states[chat_id]
            except Exception as e:
                await update.message.reply_text(f"⁉️ Failed to generate music: {e}")
        else:
            # Default music generation logic
            await update.message.reply_text("Generating your music... please wait. ⏳")
            try:
                prompt = f"{chat_states[chat_id]['lyrics']}"

                # Generate Music by Description
                songs = await asyncio.to_thread(
                    client.generate,
                    prompt=prompt, 
                    is_custom=False,
                    wait_audio=True)
                
                for song in songs:
                    file_path = await asyncio.to_thread(client.download,song=song)
                    await context.bot.send_audio(chat_id=chat_id, audio=open(file_path, 'rb'), thumbnail=open("thumb.jpg", 'rb'))
                    os.remove(file_path)
                del chat_states[chat_id]
            except Exception as e:
                await update.message.reply_text(f"⁉️ Failed to generate music: {e}")
        
        if chat_id in chat_states:
            del chat_states[chat_id]
    

def main():

    BOT_TOKEN = os.getenv("BOT_TOKEN")

    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("generate", generate))
    application.add_handler(CommandHandler("cancel", cancel))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, onMessage))
    application.add_handler(CommandHandler("credits", credits_command))

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()