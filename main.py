import os
import logging
import sqlite3
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

# ================== НАСТРОЙКИ ==================
# Bothost.ru автоматически подставит токен из своих настроек
TOKEN = os.environ.get('BOT_TOKEN')
ADMIN_ID = 463971755  # Ваш ID, который уже прописан

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# ================== БАЗА ДАННЫХ ==================
DB_NAME = 'messages.db'

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS messages
                 (id INTEGER PRIMARY KEY, user_id INTEGER, message_text TEXT,
                  timestamp DATETIME, replied INTEGER DEFAULT 0)''')
    conn.commit()
    conn.close()

def save_message(user_id, text):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('INSERT INTO messages (user_id, message_text, timestamp) VALUES (?, ?, ?)',
              (user_id, text, datetime.now()))
    msg_id = c.lastrowid
    conn.commit()
    conn.close()
    return msg_id

def get_user_by_msg(msg_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT user_id FROM messages WHERE id=?', (msg_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

# ================== КОМАНДЫ БОТА ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id == ADMIN_ID:
        await update.message.reply_text('👑 Вы администратор.')
    else:
        await update.message.reply_text('🤫 Напишите анонимное сообщение.')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id == ADMIN_ID:
        return

    text = update.message.text
    msg_id = save_message(user.id, text)

    keyboard = [[InlineKeyboardButton("💬 Ответить", callback_data=f'reply_{msg_id}')]]
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f'📨 Сообщение #{msg_id}:\n{text}',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    await update.message.reply_text('✅ Отправлено!')

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data.startswith('reply_'):
        msg_id = int(query.data.split('_')[1])
        context.user_data['replying_to'] = msg_id
        await query.edit_message_text(f'Введите ответ на сообщение #{msg_id}:')

async def handle_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'replying_to' in context.user_data:
        msg_id = context.user_data['replying_to']
        reply_text = update.message.text
        user_id = get_user_by_msg(msg_id)

        if user_id:
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f'💌 Ответ:\n{reply_text}'
                )
                await update.message.reply_text('✅ Ответ отправлен!')
                del context.user_data['replying_to']
            except:
                await update.message.reply_text('❌ Ошибка отправки.')

# ================== ЗАПУСК ==================
def main():
    init_db()
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler('start', start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & filters.User(ADMIN_ID), handle_reply))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.User(ADMIN_ID), handle_message))

    print("🤖 Бот запущен!")
    app.run_polling()

if _name_ == '_main_':
    main()
