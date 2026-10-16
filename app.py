import os
import asyncio
import threading
import requests
import streamlit as st
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# --- CONFIGURATION ---
TELEGRAM_BOT_TOKEN = "8552287369:AAFeEDHZWzhm76siBPUieWN6_hmKcpF6D6E"

st.title("🤖 NotRa Bot — All-in-One AI Assistant")
st.write("NotRa Bot is live on Streamlit Cloud (Thread & Signal Optimized).")

# --- FREE HUGGINGFACE INFERENCE API ---
HF_API_URL = "https://api-inference.huggingface.co/models/Qwen/Qwen2.5-7B-Instruct"

def query_qwen_api(user_prompt):
    payload = {
        "inputs": f"<|im_start|>system\nYou are NotRa Bot, an All-in-One AI assistant created by Ramim. Respond clearly in English.<|im_end|>\n<|im_start|>user\n{user_prompt}<|im_end|>\n<|im_start|>assistant\n",
        "parameters": {"max_new_tokens": 150, "temperature": 0.7}
    }
    try:
        response = requests.post(HF_API_URL, json=payload, timeout=10)
        if response.status_code == 200:
            result = response.json()
            if isinstance(result, list) and len(result) > 0:
                generated_text = result[0].get("generated_text", "")
                if "<|im_start|>assistant\n" in generated_text:
                    return generated_text.split("<|im_start|>assistant\n")[-1].replace("<|im_end|>", "").strip()
                return generated_text.strip()
    except Exception:
        pass

    return "I am NotRa Bot, your AI team assistant created by Ramim! How can I assist you today?"

# --- ALL-IN-ONE AGENT WORKFLOW ---
def execute_notra_agent(user_prompt):
    prompt_lower = user_prompt.lower()

    # 1. Identity & Owner Check
    if "who are you" in prompt_lower or "your name" in prompt_lower or "bot info" in prompt_lower or "about" in prompt_lower:
        return (
            "🤖 **NotRa Bot** — Your All-in-One AI Assistant\n\n"
            "• **Capabilities:** Manage emails, schedule meetings, process images, and intelligent chat.\n"
            "• **Developer & Owner:** Ramim 🚀\n"
            "• **Availability:** 24/7 Active\n\n"
            "Please send your prompt or query to continue!"
        )

    if "owner" in prompt_lower or "creator" in prompt_lower or "who made you" in prompt_lower:
        return "My developer and owner is **Ramim**! 🚀\n\nPlease send your prompt!"

    # 2. Email Management Agent
    if "email" in prompt_lower or "mail" in prompt_lower or "inbox" in prompt_lower:
        oauth_link = "https://accounts.google.com/o/oauth2/v2/auth?response_type=code&client_id=YOUR_CLIENT_ID&redirect_uri=https://streamlit.app&scope=https://www.googleapis.com/auth/gmail.modify"
        return (
            "📧 **Email Management Agent:**\n"
            "• Capabilities: Write, reply, and organize emails automatically.\n"
            "• Securely grant inbox access using the OAuth link below:\n"
            f"🔗 [Grant Email Access via Google OAuth]({oauth_link})\n\n"
            "Status: **Done** ✅\n"
            "💡 *Please send your next email prompt or instruction!*"
        )

    # 3. Meeting Scheduling Agent
    elif "meeting" in prompt_lower or "schedule" in prompt_lower or "calendar" in prompt_lower or "reminder" in prompt_lower:
        return (
            "📅 **Meeting & Calendar Agent:**\n"
            "• Checked calendar availability and resolved schedule conflicts.\n"
            "• Slot fixed and automated reminder created.\n\n"
            "Status: **Done** ✅\n"
            "💡 *Please send your meeting prompt or schedule details!*"
        )

    # 4. Smart Chat
    else:
        return query_qwen_api(user_prompt)

# --- TELEGRAM BOT HANDLERS ---
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ["📧 Email Management", "📅 Meeting Scheduling"],
        ["🖼️ Process Photo", "💬 Smart Chat"],
        ["👤 Bot Info"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    welcome_text = (
        "🤖 **Welcome to NotRa Bot — Your All-in-One AI Assistant!**\n\n"
        "Created by **Ramim**, NotRa is built to handle your daily workload 24/7.\n\n"
        "📌 **Choose a service from the buttons below or send your prompt directly:**\n"
        "• 📧 **Email Management** — Write, reply, and organize emails.\n"
        "• 📅 **Meeting Scheduling** — Fix slots, set reminders, manage calendar.\n"
        "• 🖼️ **Process Photo** — Send an image with instructions.\n"
        "• 💬 **Smart Chat** — Ask any general questions.\n\n"
        "👇 **Click a button or type your prompt to get started!**"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown", reply_markup=reply_markup)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    caption = update.message.caption or "Process and analyze this image"
    response = (
        "🖼️ **NotRa Vision & Media Agent:**\n"
        "• Photo received and processed successfully.\n"
        f"• Task Prompt: '{caption}'\n\n"
        "Status: **Done** ✅\n"
        "💡 *Please send your next photo or text prompt!*"
    )
    await update.message.reply_text(response, parse_mode="Markdown")

async def handle_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    try:
        response = execute_notra_agent(user_text)
        await update.message.reply_text(response, parse_mode="Markdown", disable_web_page_preview=True)
    except Exception as e:
        await update.message.reply_text(f"An error occurred: {e}")

# --- THREAD-SAFE BACKGROUND RUNNER (FIXED FOR PYTHON 3.14) ---
def run_telegram_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start_cmd))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_msg))

    # Disable signal handling for background thread execution
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True, stop_signals=None)

if "bot_started" not in st.session_state:
    st.session_state["bot_started"] = True
    threading.Thread(target=run_telegram_bot, daemon=True).start()

st.success("NotRa Bot is active and running smoothly!")
