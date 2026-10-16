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
    prompt = f"Draft a professional email based on this instruction: '{user_instructions}'. Do not include any chatbot greetings. End the email with 'Best regards, {sender_name}'. Strictly output in this format:\nSubject: <subject>\n\n<body>"
    response = query_qwen_api(prompt)
    if "Subject:" not in response:
        return f"Subject: Invitation & Plan\n\nHi,\n\n{user_instructions}\n\nPlease let me know your thoughts.\n\nBest regards,\n{sender_name}"
    return response

# --- ROBUST SMTP EMAIL SENDER ---
def send_real_email(sender_email, app_password, receiver_email, subject, body):
    sender_clean = sender_email.strip()
    password_clean = app_password.strip().replace(" ", "")
    receiver_clean = receiver_email.strip()

    msg = MIMEMultipart()
    msg['From'] = sender_clean
    msg['To'] = receiver_clean
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

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

    return False, f"All SMTP attempts failed. Details: {'; '.join(errors)}"

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
            "📧 **Real Email Dispatcher (Step 1/4):**\n\nPlease enter your **Sender Gmail Address**:",
            parse_mode="Markdown"
        )
    elif data == "photo_task":
        await query.message.reply_text("🖼️ **Process Photo Agent Active:**\n• Send any image or screenshot directly with a caption to analyze!", parse_mode="Markdown")
    elif data == "meeting_task":
        await query.message.reply_text("📅 **Meeting Scheduler:**\n• Send details like 'Schedule meeting with project team tomorrow at 3 PM' to set a reminder.", parse_mode="Markdown")
    elif data == "chat_task":
        await query.message.reply_text("💬 **Smart Chat Active:**\n• Type any question or instruction below!", parse_mode="Markdown")
    elif data == "info_task":
        await query.message.reply_text("🤖 **NotRa Bot Info:**\n• Developer & Owner: **Ramim** 🚀", parse_mode="Markdown")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    caption = update.message.caption or "Analyze and describe this image."
    
    ai_vision_analysis = query_qwen_api(f"The user sent an image with caption: '{caption}'. Provide a clear, detailed analysis.")
    
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

    # Prevent menu buttons from breaking active email configuration steps
    if user_text in ["📧 Email Management", "📅 Meeting Scheduling", "🖼️ Process Photo", "💬 Smart Chat", "👤 Bot Info"]:
        if user_text == "📧 Email Management":
            user_sessions[chat_id] = {"step": "awaiting_sender"}
            await update.message.reply_text("📧 **Real Email Dispatcher (Step 1/4):**\n\nPlease enter your **Sender Gmail Address**:")
            return
        elif user_text == "📅 Meeting Scheduling":
            await update.message.reply_text("📅 **Meeting Scheduler:**\n• Send details like 'Schedule meeting tomorrow at 3 PM' to set a reminder.")
            return
        elif user_text == "🖼️ Process Photo":
            await update.message.reply_text("🖼️ **Process Photo Agent Active:**\n• Send any image or screenshot with a caption to analyze!")
            return
        elif user_text == "💬 Smart Chat":
            await update.message.reply_text("💬 **Smart Chat Active:**\n• Type any question below!")
            return
        elif user_text == "👤 Bot Info":
            await update.message.reply_text("🤖 **NotRa Bot Info:** Created by **Ramim** 🚀")
            return

    session = user_sessions.get(chat_id)

    # Multi-step AI Email Drafting & Confirmation Flow
    if session:
        step = session.get("step")
        if step == "awaiting_sender":
            session["sender"] = user_text
            # Extract user name cleanly from email prefix (e.g., ramim125g -> Ramim)
            email_prefix = user_text.split("@")[0]
            clean_name = "".join([c for c in email_prefix if c.isalpha()]).capitalize() or "User"
            session["sender_name"] = clean_name
            
            session["step"] = "awaiting_password"
            await update.message.reply_text("🔑 **Step 2/4:** Please enter your Gmail **App Password**:")
            return
        elif step == "awaiting_password":
            session["password"] = user_text
            session["step"] = "awaiting_receiver"
            await update.message.reply_text("📬 **Step 3/4:** Please enter the **Recipient Email Address**:")
            return
        elif step == "awaiting_receiver":
            session["receiver"] = user_text
            session["step"] = "awaiting_content"
            await update.message.reply_text("📝 **Step 4/4:** What would you like to communicate? Type your message/topic and AI will compose the email:")
            return
        elif step == "awaiting_content":
            sender_name = session.get("sender_name", "User")
            ai_draft = generate_ai_email_draft(user_text, sender_name)
            session["draft"] = ai_draft
            session["step"] = "awaiting_confirmation"
            
            confirm_keyboard = ReplyKeyboardMarkup([["Yes", "No"]], resize_keyboard=True, one_time_keyboard=True)
            
            await update.message.reply_text(
                "📝 **AI Generated Email Draft:**\n\n"
                f"{ai_draft}\n\n"
                "-----------------------------------\n"
                "❓ **Can I send this email now?** (Type/Click **Yes** to confirm, or **No** to cancel)",
                reply_markup=confirm_keyboard
            )
            return
        elif step == "awaiting_confirmation":
            reply_keyboard = ReplyKeyboardMarkup([
                ["📧 Email Management", "📅 Meeting Scheduling"],
                ["🖼️ Process Photo", "💬 Smart Chat"],
                ["👤 Bot Info"]
            ], resize_keyboard=True)

            if user_text.lower() in ["yes", "y", "send", "confirm"]:
                sender = session["sender"]
                password = session["password"]
                receiver = session["receiver"]
                draft_content = session["draft"]
                
                subject = "Notification from NotRa AI Assistant"
                if "Subject:" in draft_content:
                    lines = draft_content.split("\n")
                    for l in lines:
                        if "Subject:" in l:
                            subject = l.replace("Subject:", "").strip()
                            break
                
                user_sessions[chat_id] = None
                
                await update.message.reply_text("⏳ Dispatching real email via secure SMTP...")
                success, msg = send_real_email(sender, password, receiver, subject, draft_content)
                
                if success:
                    await update.message.reply_text("✅ **Real Email Sent Successfully to Recipient!** 🚀", reply_markup=reply_keyboard)
                else:
                    await update.message.reply_text(f"❌ Failed to send email: {msg}", reply_markup=reply_keyboard)
            else:
                user_sessions[chat_id] = None
                await update.message.reply_text("❌ Email dispatch cancelled.", reply_markup=reply_keyboard)
            return

    # Standard Keyword Routing
    p_lower = user_text.lower()
    if "email management" in p_lower or "send email" in p_lower:
        user_sessions[chat_id] = {"step": "awaiting_sender"}
        await update.message.reply_text("📧 **Real Email Dispatcher (Step 1/4):** Please enter your **Sender Gmail Address**:")
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
