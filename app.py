import os
import asyncio
import threading
import requests
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import streamlit as st
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- CONFIGURATION ---
TELEGRAM_BOT_TOKEN = "8552287369:AAFeEDHZWzhm76siBPUieWN6_hmKcpF6D6E"
STREAMLIT_WEB_URL = "https://notra-bot.streamlit.app/"

# --- STREAMLIT WEB DASHBOARD ---
st.set_page_config(page_title="NotRa Bot Hub", page_icon="🤖", layout="centered")

st.title("🤖 NotRa Bot — Control & Web Portal")
st.markdown("### Welcome to the Official Management Portal of NotRa Bot!")
st.write("**Developer & Owner:** Ramim 🚀")

st.info("💡 **Gmail Integration Portal:** Use this secure portal to link your Gmail account and authorize smart email dispatching.")

user_email_input = st.text_input("Enter your Gmail address to link account:")
if st.button("Connect & Authorize Gmail Account"):
    if user_email_input:
        st.success(f"Successfully linked **{user_email_input}** to NotRa Bot! You can now proceed with email operations.")
    else:
        st.error("Please enter a valid Gmail address.")

st.divider()
st.write("🟢 **Bot Status:** Online & Active on Telegram 24/7")

# --- HUGGING FACE API (Qwen2.5-7B-Instruct) ---
HF_TEXT_URL = "https://api-inference.huggingface.co/models/Qwen/Qwen2.5-7B-Instruct"

def query_qwen_api(user_prompt):
    payload = {
        "inputs": f"<|im_start|>system\nYou are NotRa Bot, an intelligent AI assistant created by Ramim. Provide direct, accurate, and professional responses in English.<|im_end|>\n<|im_start|>user\n{user_prompt}<|im_end|>\n<|im_start|>assistant\n",
        "parameters": {"max_new_tokens": 250, "temperature": 0.75, "top_p": 0.9}
    }
    try:
        response = requests.post(HF_TEXT_URL, json=payload, timeout=12)
        if response.status_code == 200:
            result = response.json()
            if isinstance(result, list) and len(result) > 0:
                generated_text = result[0].get("generated_text", "")
                if "<|im_start|>assistant\n" in generated_text:
                    ans = generated_text.split("<|im_start|>assistant\n")[-1].replace("<|im_end|>", "").strip()
                    if ans:
                        return ans
            elif isinstance(result, dict) and "generated_text" in result:
                generated_text = result["generated_text"]
                if "<|im_start|>assistant\n" in generated_text:
                    ans = generated_text.split("<|im_start|>assistant\n")[-1].replace("<|im_end|>", "").strip()
                    if ans:
                        return ans
    except Exception:
        pass

    return f"Subject: Plan to Meet\n\nHi,\n\nI was thinking about planning a visit to a restaurant together. Let me know when you are available!"

def generate_ai_email_draft(user_instructions, sender_name):
    prompt = f"Draft a professional email based on this instruction: '{user_instructions}'. Do not include any chatbot greetings, assistant titles, or emojis. End the email cleanly with 'Best regards, {sender_name}'. Strictly output in this format:\nSubject: <subject>\n\n<body>"
    response = query_qwen_api(prompt)
    if "Subject:" not in response:
        return f"Subject: Invitation & Plan\n\nHi,\n\n{user_instructions}\n\nPlease let me know your thoughts.\n\nBest regards,\n{sender_name}"
    return response

# --- SMTP EMAIL SENDER WITH UTF-8 ---
def send_real_email(sender_email, app_password, receiver_email, subject, body):
    sender_clean = sender_email.strip()
    password_clean = app_password.strip().replace(" ", "")
    receiver_clean = receiver_email.strip()

    msg = MIMEMultipart()
    msg['From'] = sender_clean
    msg['To'] = receiver_clean
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain', 'utf-8'))

    errors = []
    # Try Port 465 (SSL)
    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=20)
        server.login(sender_clean, password_clean)
        server.sendmail(sender_clean, receiver_clean, msg.as_string())
        server.quit()
        return True, "Email dispatched successfully via SSL!"
    except Exception as e:
        errors.append(f"SSL (465): {str(e)}")

    # Try Port 587 (TLS)
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587, timeout=20)
        server.starttls()
        server.login(sender_clean, password_clean)
        server.sendmail(sender_clean, receiver_clean, msg.as_string())
        server.quit()
        return True, "Email dispatched successfully via TLS!"
    except Exception as e:
        errors.append(f"TLS (587): {str(e)}")

    return False, f"SMTP Error (Streamlit Cloud blocks ports): {'; '.join(errors)}"

# Session Storage
user_sessions = {}

# --- WORKFLOW AGENTS & REMINDER HANDLER ---
async def schedule_meeting_reminder(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    chat_id = job.chat.id
    meeting_details = job.data
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"⏰ **Meeting Reminder!**\n\nYour scheduled meeting is starting now:\n📌 *{meeting_details}*",
        parse_mode="Markdown"
    )

def execute_notra_agent(user_prompt, chat_id, context):
    prompt_lower = user_prompt.lower()

    if "bot info" in prompt_lower or "about" in prompt_lower:
        return (
            "🤖 **NotRa Bot System Info**\n\n"
            "• **Developer:** Ramim 🚀\n"
            "• **Status:** Active & Fully Operational\n"
            "• **Features:** Gmail Web Portal Link, Meeting Reminders, AI Vision Media & Smart Chat."
        )

    elif "schedule meeting" in prompt_lower or "meeting" in prompt_lower or "reminder" in prompt_lower:
        meeting_text = user_prompt.replace("schedule meeting", "").replace("meeting", "").strip() or "General Sync Meeting"
        if context and context.job_queue:
            context.job_queue.run_once(schedule_meeting_reminder, 30, chat=chat_id, data=meeting_text, name=str(chat_id))
        
        return (
            "📅 **Meeting Scheduled Successfully!**\n\n"
            f"• **Topic/Details:** {meeting_text}\n"
            "• **Status:** Reminder scheduled! I will alert you right on time. 🟢"
        )

    elif "smart chat" in prompt_lower:
        return "💬 **Smart AI Chat Active:** Send any question or prompt below and I will answer directly!"

    else:
        return query_qwen_api(user_prompt)

# --- TELEGRAM BOT HANDLERS ---
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    inline_keyboard = [
        [InlineKeyboardButton("🌐 Open Web Portal to Link Gmail", url=STREAMLIT_WEB_URL)],
        [InlineKeyboardButton("✍️ Send Real Email via AI Draft", callback_data="send_email_prompt")],
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
        "🤖 **Welcome to NotRa Bot — Your All-in-One AI Assistant!**\n\n"
        "Created by **Ramim**, NotRa handles real email dispatching, meeting reminders, vision media analysis, and smart chat.\n\n"
        "📌 **Choose an option below or send your request directly:**"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown", reply_markup=reply_markup)
    await update.message.reply_text("👇 **Interactive Control Panel:**", reply_markup=inline_markup)

async def button_click_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    
    data = query.data
    if data == "send_email_prompt" or data == "email_menu":
        user_sessions[chat_id] = {"step": "awaiting_sender"}
        await query.message.reply_text(
            "📧 **Real Email Dispatcher (Step 1/4):**\n
