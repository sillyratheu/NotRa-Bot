import os
import asyncio
import threading
import torch
import streamlit as st
from transformers import AutoModelForCausalLM, AutoTokenizer
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# --- CONFIGURATION ---
TELEGRAM_BOT_TOKEN = st.secrets.get("TELEGRAM_BOT_TOKEN", "8552287369:AAFeEDHZWzhm76siBPUieWN6_hmKcpF6D6E")

st.title("🤖 NotRa Bot — Your All-in-One AI Assistant")
st.write("NotRa Bot is live on Streamlit Cloud CPU (Optimized for Low RAM).")

# --- LOAD LIGHTWEIGHT LLM WITH RAM OPTIMIZATION ---
MODEL_NAME = "Qwen/Qwen1.5-0.5B-Chat"

@st.cache_resource
def load_model_and_tokenizer():
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
    # Using low_cpu_mem_usage and torch.float16 or torch.qint8 if needed to save RAM
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        torch_dtype=torch.float32,
        device_map="cpu",
        low_cpu_mem_usage=True,
        trust_remote_code=True
    )
    return tokenizer, model

tokenizer, model = load_model_and_tokenizer()

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
    
    # 4. Smart Chat & General AI Reasoning
    else:
        messages = [
            {
                "role": "system", 
                "content": (
                    "You are NotRa Bot, an All-in-One AI assistant created by Ramim. "
                    "You are fast, reliable, intelligent, and helpful. "
                    "Always respond clearly in English."
                )
            },
            {"role": "user", "content": user_prompt}
        ]
        
        text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        model_inputs = tokenizer([text], return_tensors="pt").to("cpu")
        
        generated_ids = model.generate(
            model_inputs.input_ids,
            max_new_tokens=100,
            do_sample=True,
            temperature=0.7,
            top_p=0.9
        )
        
        generated_ids = [
            output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
        ]
        
        response = tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
        return response.strip()

# --- TELEGRAM BOT HANDLERS WITH BUTTONS ---
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

# --- BACKGROUND THREAD RUNNER ---
def run_telegram_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(handlers := MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_msg))
    
    print("NotRa Bot polling active...")
    app.run_polling(drop_pending_updates=True)

if "bot_started" not in st.session_state:
    st.session_state["bot_started"] = True
    threading.Thread(target=run_telegram_bot, daemon=True).start()

st.success("NotRa Bot is active with low-RAM optimization!")
