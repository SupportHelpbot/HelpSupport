# ticket_help_bot.py
# Бот заявок/тикетов для Telegram групп
# Установка: pip install pyTelegramBotAPI

import json
import os
from datetime import datetime

import telebot
from telebot import types

TOKEN = "ВСТАВЬ_ТОКЕН_БОТА"
ADMIN_ID = 123456789  # ВСТАВЬ СВОЙ TELEGRAM ID

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

DATA_DIR = "data"
TICKETS_FILE = os.path.join(DATA_DIR, "tickets.json")
USERS_FILE = os.path.join(DATA_DIR, "users.json")

user_states = {}
admin_reply_states = {}


def ensure_files():
    os.makedirs(DATA_DIR, exist_ok=True)

    if not os.path.exists(TICKETS_FILE):
        with open(TICKETS_FILE, "w", encoding="utf-8") as f:
            json.dump({"last_id": 565, "tickets": {}}, f, ensure_ascii=False, indent=2)

    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f, ensure_ascii=False, indent=2)


def load_json(path):
    ensure_files()
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    ensure_files()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main_menu():
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("📝 Создать заявку", callback_data="create_ticket"))
    kb.add(types.InlineKeyboardButton("📋 Мои заявки", callback_data="my_tickets"))
    kb.add(types.InlineKeyboardButton("ℹ️ Помощь", callback_data="help"))
    return kb


def categories_menu():
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🚫 Жалоба", callback_data="cat_Жалоба"))
    kb.add(types.InlineKeyboardButton("⚠️ Проблема", callback_data="cat_Проблема"))
    kb.add(types.InlineKeyboardButton("💡 Предложение", callback_data="cat_Предложение"))
    kb.add(types.InlineKeyboardButton("❓ Другое", callback_data="cat_Другое"))
    kb.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="back_start"))
    return kb


def ticket_admin_buttons(ticket_id):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("💬 Ответить", callback_data=f"admin_reply_{ticket_id}"))
    kb.add(types.InlineKeyboardButton("✅ Закрыть", callback_data=f"admin_close_{ticket_id}"))
    kb.add(types.InlineKeyboardButton("❌ Отклонить", callback_data=f"admin_reject_{ticket_id}"))
    return kb


@bot.message_handler(commands=["start"])
def start(message):
    users = load_json(USERS_FILE)
    users[str(message.from_user.id)] = {
        "username": message.from_user.username,
        "first_name": message.from_user.first_name,
        "last_seen": datetime.now().strftime("%d.%m.%Y %H:%M")
    }
    save_json(USERS_FILE, users)

    text = (
        "👋 <b>Добро пожаловать в TicketHelpBot</b>\n\n"
        "Здесь можно создать заявку, жалобу или вопрос для администрации группы.\n\n"
        "Выберите действие:"
    )
    bot.send_message(message.chat.id, text, reply_markup=main_menu())


@bot.message_handler(commands=["support", "help"])
def support_in_group(message):
    if message.chat.type in ["group", "supergroup"]:
        bot_username = bot.get_me().username
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("📩 Открыть поддержку", url=f"https://t.me/{bot_username}?start=support"))
        bot.reply_to(
            message,
            "🛠 <b>Нужна помощь?</b>\n\nНажмите кнопку ниже и создайте заявку в личке бота.",
            reply_markup=kb
        )
    else:
        start(message)


@bot.callback_query_handler(func=lambda call: call.data == "back_start")
def back_start(call):
    bot.edit_message_text(
        "👋 <b>TicketHelpBot</b>\n\nВыберите действие:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=main_menu()
    )


@bot.callback_query_handler(func=lambda call: call.data == "help")
def help_button(call):
    bot.answer_callback_query(call.id)
    bot.send_message(
        call.message.chat.id,
        "ℹ️ <b>Помощь</b>\n\n"
        "1. Нажмите «Создать заявку».\n"
        "2. Выберите тип проблемы.\n"
        "3. Опишите ситуацию.\n"
        "4. Админ получит заявку и сможет ответить."
    )


@bot.callback_query_handler(func=lambda call: call.data == "create_ticket")
def create_ticket(call):
    bot.edit_message_text(
        "📌 <b>Выберите тип заявки:</b>",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=categories_menu()
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("cat_"))
def choose_category(call):
    category = call.data.replace("cat_", "")
    user_states[call.from_user.id] = {
        "step": "waiting_text",
        "category": category
    }

    bot.answer_callback_query(call.id)
    bot.send_message(
        call.message.chat.id,
        f"✍️ <b>Тип заявки:</b> {category}\n\n"
        "Теперь опишите проблему одним сообщением."
    )


@bot.message_handler(func=lambda message: message.from_user.id in user_states)
def ticket_text(message):
    state = user_states.get(message.from_user.id)

    if not state or state.get("step") != "waiting_text":
        return

    tickets_data = load_json(TICKETS_FILE)
    tickets_data["last_id"] += 1
    ticket_id = tickets_data["last_id"]

    username = f"@{message.from_user.username}" if message.from_user.username else "Без username"

    ticket = {
        "id": ticket_id,
        "user_id": message.from_user.id,
        "username": username,
        "first_name": message.from_user.first_name,
        "category": state["category"],
        "text": message.text,
        "status": "На рассмотрении",
        "created_at": datetime.now().strftime("%d.%m.%Y %H:%M")
    }

    tickets_data["tickets"][str(ticket_id)] = ticket
    save_json(TICKETS_FILE, tickets_data)

    user_states.pop(message.from_user.id, None)

    bot.send_message(
        message.chat.id,
        f"✅ <b>Заявка #{ticket_id} создана!</b>\n\n"
        f"📌 <b>Тип:</b> {ticket['category']}\n"
        f"📝 <b>Описание:</b> {ticket['text']}\n"
        f"⏳ <b>Статус:</b> На рассмотрении\n\n"
        "Ответ придёт сюда в бота.",
        reply_markup=main_menu()
    )

    admin_text = (
        f"🚨 <b>Новая заявка #{ticket_id}</b>\n\n"
        f"👤 <b>От:</b> {ticket['username']} | ID: <code>{ticket['user_id']}</code>\n"
        f"📌 <b>Тип:</b> {ticket['category']}\n"
        f"🕐 <b>Дата:</b> {ticket['created_at']}\n\n"
        f"📝 <b>Текст:</b>\n{ticket['text']}"
    )

    bot.send_message(ADMIN_ID, admin_text, reply_markup=ticket_admin_buttons(ticket_id))


@bot.callback_query_handler(func=lambda call: call.data == "my_tickets")
def my_tickets(call):
    tickets_data = load_json(TICKETS_FILE)
    user_id = call.from_user.id

    my = []
    for ticket in tickets_data["tickets"].values():
        if ticket["user_id"] == user_id:
            my.append(ticket)

    if not my:
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "📋 У вас пока нет заявок.")
        return

    text = "📋 <b>Ваши заявки:</b>\n\n"
    for ticket in my[-5:]:
        text += (
            f"🟡 <b>Заявка #{ticket['id']}</b>\n"
            f"📌 Тип: {ticket['category']}\n"
            f"⏳ Статус: {ticket['status']}\n\n"
        )

    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, text)


@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_reply_"))
def admin_reply(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "Нет доступа")
        return

    ticket_id = call.data.replace("admin_reply_", "")
    admin_reply_states[call.from_user.id] = ticket_id

    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, f"💬 Напишите ответ пользователю по заявке #{ticket_id}.")


@bot.message_handler(func=lambda message: message.from_user.id in admin_reply_states)
def send_admin_reply(message):
    ticket_id = admin_reply_states.get(message.from_user.id)
    tickets_data = load_json(TICKETS_FILE)

    ticket = tickets_data["tickets"].get(str(ticket_id))

    if not ticket:
        bot.send_message(message.chat.id, "❌ Заявка не найдена.")
        admin_reply_states.pop(message.from_user.id, None)
        return

    user_id = ticket["user_id"]

    bot.send_message(
        user_id,
        f"💬 <b>Ответ по заявке #{ticket_id}</b>\n\n"
        f"{message.text}"
    )

    ticket["status"] = "Ответ отправлен"
    save_json(TICKETS_FILE, tickets_data)

    admin_reply_states.pop(message.from_user.id, None)

    bot.send_message(message.chat.id, f"✅ Ответ по заявке #{ticket_id} отправлен.")


@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_close_"))
def admin_close(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "Нет доступа")
        return

    ticket_id = call.data.replace("admin_close_", "")
    tickets_data = load_json(TICKETS_FILE)

    ticket = tickets_data["tickets"].get(str(ticket_id))
    if not ticket:
        bot.answer_callback_query(call.id, "Заявка не найдена")
        return

    ticket["status"] = "Закрыта"
    save_json(TICKETS_FILE, tickets_data)

    bot.send_message(ticket["user_id"], f"✅ <b>Заявка #{ticket_id} закрыта.</b>")
    bot.answer_callback_query(call.id, "Заявка закрыта")


@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_reject_"))
def admin_reject(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "Нет доступа")
        return

    ticket_id = call.data.replace("admin_reject_", "")
    tickets_data = load_json(TICKETS_FILE)

    ticket = tickets_data["tickets"].get(str(ticket_id))
    if not ticket:
        bot.answer_callback_query(call.id, "Заявка не найдена")
        return

    ticket["status"] = "Отклонена"
    save_json(TICKETS_FILE, tickets_data)

    bot.send_message(ticket["user_id"], f"❌ <b>Заявка #{ticket_id} отклонена.</b>")
    bot.answer_callback_query(call.id, "Заявка отклонена")


if __name__ == "__main__":
    ensure_files()
    print("TicketHelpBot запущен...")
    bot.infinity_polling(skip_pending=True)
