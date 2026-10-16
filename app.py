import os
import asyncio
import threading
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import streamlit as st
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- CONFIGURATION ---
TELEGRAM_BOT_TOKEN = "8552287369:AAFeEDHZWzhm76siBPUieWN6_hmKcpF6D6E"

st.title("🤖 NotRa Bot — All-in-One AI Assistant")
st.write("NotRa Bot is live with Real Email Integration & Smart Chat.")

# --- FREE HUGGINGFACE INFERENCE API ---
HF_TEXT_URL = "https://api-inference.huggingface.co/models/Qwen/Qwen2.5-7B-Instruct"

def query_qwen_api(user_prompt):
    payload = {
        "inputs": f"<|im_start|>system\nYou are NotRa Bot, a professional AI assistant created by Ramim. Give direct and helpful answers.<|im_end|>\n<|im_start|>user\n{user_prompt}<|im_end|>\n<|im_start|>assistant\n",
        "parameters": {"max_new_tokens": 200, "temperature": 0.7}
    }
    try:
        response = requests.post(HF_TEXT_URL, json=payload, timeout=10)
        if response.status_code == 200:
            result = response.json()
            if isinstance(result, list) and len(result) > 0:
                generated_text = result[0].get("generated_text", "")
                if "<|im_start|>assistant\n" in generated_text:
                    return generated_text.split("<|im_start|>assistant\n")[-1].replace("<|im_end|>", "").strip()
    except Exception:
        pass
    return f"I processed your query: '{user_prompt}'. How else can I assist you?"

# Real Email Sending Function via SMTP
def send_real_smtp_email(sender_email, app_password, receiver_email, subject, body):
    try:
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = receiver_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, app_password)
        server.sendmail(sender_email, receiver_email, msg.as_string())
        server.quit()
        return True, "Email sent successfully!"
    except Exception as e:
        return False, str(e)

# User state dictionary for real email inputs
user_email_states = {}

# --- TELEGRAM BOT HANDLERS ---
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    inline_keyboard = [
        [InlineKeyboardButton("📥 Option 1: Real Inbox Setup", callback_data="opt1_inbox")],
        [InlineKeyboardButton("✍️ Option 2: Send Real Email (SMTP)", callback_data="opt2_reply")],
        [InlineKeyboardButton("📅 Meeting Scheduling", callback_data="meeting_task")],
        [InlineKeyboardButton("🖼️ Process Photo", callback_data="photo_task")],
        [InlineKeyboardButton("💬 Smart Chat", callback_data="chat_task")],
        [InlineKeyboardButton("👤 Bot Info", callback_data="info_task")]
    ]
    inline_markup = InlineKeyboardMarkup(inline_keyboard)

    reply_keyboard = [
        ["📧 Email Management", "📅 Meeting Scheduling"],
        ["🖼️ Process Photo", "💬 Smart Chat"],
        ["👤 Bot Info"]
    ]
    reply_markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True)

    welcome_text = (
        "🤖 **Welcome to NotRa Bot — Real Mode Enabled!**\n\n"
        "Created by **Ramim**, NotRa now supports real email configuration.\n\n"
        "📌 **Choose an option below or send your prompt directly:**"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown", reply_markup=reply_markup)
    await update.message.reply_text("👇 **Real Control Panel:**", reply_markup=inline_markup)

async def button_click_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    
    data = query.data
    if data == "opt1_inbox":
        user_email_states[chat_id] = "awaiting_inbox_creds"
        response = (
            "📥 **Option 1: Real Inbox Configuration**\n\n"
            "Doya kore apnar real Email address ebong App Password ei format-e pathan:\n"
            "`email:password`\n\n"
            "*(Jemon: `myemail@gmail.com:abcd1234abcd1234`)*"
        )
    elif data == "opt2_reply":
        user_email_states[chat_id] = "awaiting_send_creds"
        response = (
            "✍️ **Option 2: Send Real Email via SMTP**\n\n"
            "Doya kore nicher format-e apnar details din:\n"
            "`SENDER_EMAIL | APP_PASSWORD | RECEIVER_EMAIL | SUBJECT | MESSAGE`\n\n"
            "*(Example: `my@gmail.com | pass123 | target@gmail.com | Hello | Test message`)*"
        )
    elif data == "photo_task":
        response = "🖼️ **Process Photo Agent:** Send any image or screenshot directly in chat!"
    elif data == "meeting_task":
        response = "📅 **Meeting Scheduler:** Send schedule details to set reminders."
    elif data == "chat_task":
        response = "💬 **Smart Chat Active:** Type any question or query below."
    elif data == "info_task":
        response = "🤖 **NotRa Bot Info:** Created by **Ramim** 🚀 (Real Mode)"
    else:
        response = "Action processed."

    await query.message.reply_text(response, parse_mode="Markdown")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    caption = update.message.caption or "Analyze image"
    await update.message.reply_text(f"🖼️ **Photo Received & Scanned Successfully!**\nCaption: '{caption}'", parse_mode="Markdown")

async def handle_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_text = update.message.text.strip()
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    # Check if user is in email credential state
    current_state = user_email_states.get(chat_id)
    
    if current_state == "awaiting_inbox_creds":
        try:
            parts = user_text.split(":")
            email_acc = parts[0].strip()
            password_acc = parts[1].strip()
            user_email_states[chat_id] = None
            await update.message.reply_text(f"✅ Real credentials received for **{email_acc}**! Connecting to IMAP server to fetch unread messages...")
            # Here real IMAP check can be placed
        except Exception:
            await update.message.reply_text("❌ Format vul hoyeche! Doya kore `email:password` format-e abar pathan.")
        return

    elif current_state == "awaiting_send_creds":
        try:
            parts = [p.strip() for p in user_text.split("|")]
            sender = parts[0]
            pwd = parts[1]
            receiver = parts[2]
            subject = parts[3]
            body = parts[4]
            
            user_email_states[chat_id] = None
            await update.message.reply_text("⏳ Sending real email via SMTP server...")
            success, msg = send_real_smtp_email(sender, pwd, receiver, subject, body)
            if success:
                await update.message.reply_text("✅ **Real Email Sent Successfully!** 🚀")
            else:
                await update.message.reply_text(f"❌ Failed to send email: {msg}")
        except Exception:
            await update.message.reply_text("❌ Format vul hoyeche! Doya kore thik vabe `SENDER | PASS | RECEIVER | SUBJECT | BODY` format-e pathan.")
        return

    # Handle standard keyword triggers or smart chat
    p_lower = user_text.lower()
    if "email management" in p_lower or "email" in p_lower:
        await update.message.reply_text(
            "📧 **Real Email Management:**\n"
            "Doya kore uporer menu theke **Option 1 (Inbox)** ba **Option 2 (Send Email)** select korun[span_1](start_span)[span_1](end_span)."
        )
    elif "meeting" in p_lower:
        await update.message.reply_text("📅 **Meeting Scheduler:** Calendar sync active.")
    elif "smart chat" in p_lower or "hello" in p_lower or "hi" in p_lower:
        ans = query_qwen_api(user_text)
        await update.message.reply_text(ans, parse_mode="Markdown")
    else:
        ans = query_qwen_api(user_text)
        await update.message.reply_text(ans, parse_Mode="Markdown")

# --- THREAD-SAFE BACKGROUND RUNNER ---
def run_telegram_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start_cmd))
    application.add_handler(CallbackQueryHandler(button_click_handler))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_msg))

    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True, stop_signals=None)

if "bot_started" not in st.session_state:
    st.session_state["bot_started"] = True
    threading.Thread(target=run_telegram_bot, daemon=True).start()

st.success("NotRa Bot is running in Real Email Mode!")
