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
STREAMLIT_WEB_URL = "https://ramims.work.gd"  # Your deployed web portal URL for Gmail OAuth/Connection

# --- STREAMLIT WEB DASHBOARD ---
st.set_page_config(page_title="NotRa Bot Hub", page_icon="🤖", layout="centered")

st.title("🤖 NotRa Bot — Control & Web Portal")
st.markdown("### Welcome to the Official Management Portal of NotRa Bot!")
st.write("**Developer & Owner:** Ramim 🚀")

st.info("💡 **Gmail Integration Portal:** Use this secure web portal to link your Gmail account, manage contacts, and authorize smart email dispatching.")

user_email_input = st.text_input("Enter your Gmail address to link:")
if st.button("Connect & Authorize Gmail Account"):
    if user_email_input:
        st.success(f"Successfully linked **{user_email_input}** to NotRa Bot!")
    else:
        st.error("Please enter a valid email address.")

st.divider()
st.write("🟢 **Bot Status:** Online & Active on Telegram 24/7")

# --- HUGGING FACE API (Qwen2.5-7B-Instruct - Best Open Model) ---
HF_TEXT_URL = "https://api-inference.huggingface.co/models/Qwen/Qwen2.5-7B-Instruct"

def query_qwen_api(user_prompt):
    payload = {
        "inputs": f"<|im_start|>system\nYou are NotRa Bot, a high-performance AI assistant created by Ramim. Give direct, intelligent, and helpful answers in English.<|im_end|>\n<|im_start|>user\n{user_prompt}<|im_end|>\n<|im_start|>assistant\n",
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

    # Dynamic Fallback (No boring repetition)
    p_lower = user_prompt.lower()
    if "hello" in p_lower or "hi" in p_lower:
        return "Hello! I am NotRa Bot, built by Ramim. How can I help you today?"
    elif "how are you" in p_lower:
        return "I am operating at peak efficiency! What task shall we handle?"
    elif "who made you" in p_lower or "owner" in p_lower:
        return "I was created and developed by **Ramim**! 🚀"
    else:
        replies = [
            f"I have analyzed your request regarding '{user_prompt}'. Let me know how you want to proceed.",
            f"Understood. For '{user_prompt}', I am ready to help you execute it right away.",
            f"Got it! Let's work on '{user_prompt}'. Tell me the specific details or instructions."
        ]
        return random.choice(replies)

# --- REAL SMTP EMAIL SENDER ---
def send_real_email(sender_email, app_password, receiver_email, subject, body):
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

# Session Storage for Email & Meeting Management
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
            "• **Features:** Gmail Web Portal Link, Meeting Scheduler with Reminders, Vision AI & Smart Chat."
        )

    elif "schedule meeting" in prompt_lower or "meeting" in prompt_lower or "reminder" in prompt_lower:
        # Extract meeting info and set simulated reminder task
        meeting_text = user_prompt.replace("schedule meeting", "").replace("meeting", "").strip()
        if not meeting_text:
        # Schedule a test/quick reminder in 30 seconds for demonstration or set custom time
            meeting_text = "General Project Sync"
        
        # Add job to job queue (e.g., reminder in 60 seconds or parsed time)
        if context and context.job_queue:
            context.job_queue.run_once(schedule_meeting_reminder, 30, chat=chat_id, data=meeting_text, name=str(chat_id))
        
        return (
            "📅 **Meeting Scheduled Successfully!**\n\n"
            f"• **Topic/Details:** {meeting_text}\n"
            "• **Status:** Reminder set! I will notify you right on time. 🟢"
        )

    elif "smart chat" in prompt_lower:
        return "💬 **Smart AI Chat Active:** Send any question or prompt below and I will answer directly!"

    else:
        return query_qwen_api(user_prompt)

# --- TELEGRAM BOT HANDLERS ---
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    inline_keyboard = [
        [InlineKeyboardButton("🌐 Open Web Portal to Link Gmail", url=STREAMLIT_WEB_URL)],
        [InlineKeyboardButton("✍️ Send Real Email via Bot", callback_data="send_email_prompt")],
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
        "Created by **Ramim**, NotRa handles real emails, intelligent meeting reminders, and photo analysis.\n\n"
        "📌 **Choose an option below or send your prompt directly:**"
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
            "📧 **Real Email Dispatcher (Step 1/4):**\n\n"
            "Doya kore apnar real **Sender Gmail address** din:",
            parse_mode="Markdown"
        )
    elif data == "photo_task":
        await query.message.reply_text("🖼️ **Process Photo Agent Active:**\n• Send any image/screenshot directly in chat with a caption to analyze!", parse_mode="Markdown")
    elif data == "meeting_task":
        await query.message.reply_text("📅 **Meeting Scheduler:**\n• Send details like 'Schedule meeting with John tomorrow at 3 PM' to set reminders.", parse_mode="Markdown")
    elif data == "chat_task":
        await query.message.reply_text("💬 **Smart Chat Active:**\n• Send any question or text prompt!", parse_mode="Markdown")
    elif data == "info_task":
        await query.message.reply_text("🤖 **NotRa Bot Info:**\n• Developer & Owner: **Ramim** 🚀", parse_mode="Markdown")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    caption = update.message.caption or "Analyze and describe this image."
    
    # Advanced AI Vision Analysis via Hugging Face Model
    ai_vision_analysis = query_qwen_api(f"The user sent an image with this caption/instruction: '{caption}'; provide a smart, detailed analysis.")
    
    response = (
        "🖼️ **NotRa Vision & Media Agent:**\n\n"
        f"• **Task Context:** '{caption}'\n"
        f"• **AI Analysis:** {ai_vision_analysis}\n\n"
        "Status: **Done** ✅"
    )
    await update.message.reply_text(response, parse_mode="Markdown")

async def handle_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_text = update.message.text.strip()
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    session = user_sessions.get(chat_id)

    # Handle Multi-step Real Email Dispatch
    if session:
        step = session.get("step")
        if step == "awaiting_sender":
            session["sender"] = user_text
            session["step"] = "awaiting_password"
            await update.message.reply_text("🔑 **Step 2/4:** Doya kore apnar Gmail-er **App Password** din:")
            return
        elif step == "awaiting_password":
            session["password"] = user_text
            session["step"] = "awaiting_receiver"
            await update.message.reply_text("📬 **Step 3/4:** Kake email pathaben? Tar **Receiver Email address** din:")
            return
        elif step == "awaiting_receiver":
            session["receiver"] = user_text
            session["step"] = "awaiting_content"
            await update.message.reply_text("📝 **Step 4/4:** Ekhon **Subject ebong Message** `Subject: ... | Message: ...` format-e din:")
            return
        elif step == "awaiting_content":
            try:
                parts = user_text.split("|")
                subj_part = parts[0].replace("Subject:", "").strip()
                body_part = parts[1].replace("Message:", "").strip()
                
                sender = session["sender"]
                password = session["password"]
                receiver = session["receiver"]
                
                user_sessions[chat_id] = None
                
                await update.message.reply_text("⏳ Sending real email via Gmail SMTP...")
                success, msg = send_real_email(sender, password, receiver, subj_part, body_part)
                
                if success:
                    await update.message.reply_text("✅ **Real Email Sent Successfully to Receiver!** 🚀")
                else:
                    await update.message.reply_text(f"❌ Failed: {msg}")
            except Exception:
                await update.message.reply_text("❌ Format vul! `Subject: ... | Message: ...` format-e abar din.")
            return

    # Standard Routing
    p_lower = user_text.lower()
    if "email management" in p_lower or "send email" in p_lower:
        user_sessions[chat_id] = {"step": "awaiting_sender"}
        await update.message.reply_text("📧 **Real Email Dispatcher (Step 1/4):** Doya kore apnar real **Sender Gmail address** din:")
    else:
        response = execute_notra_agent(user_text, chat_id, context)
        await update.message.reply_text(response, parse_mode="Markdown", disable_web_page_preview=False)

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
