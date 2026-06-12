# ticket_help_group_bot.py
# Бот заявок для групп: владелец сам подключает группу, и заявки приходят ему
# Установка: pip install pyTelegramBotAPI

import json
import os
from datetime import datetime

import telebot
from telebot import types

TOKEN = os.getenv("TOKEN")

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

DATA_DIR = "data"
GROUPS_FILE = os.path.join(DATA_DIR, "groups.json")
TICKETS_FILE = os.path.join(DATA_DIR, "tickets.json")

user_states = {}
owner_states = {}


def ensure_files():
    os.makedirs(DATA_DIR, exist_ok=True)

    if not os.path.exists(GROUPS_FILE):
        with open(GROUPS_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f, ensure_ascii=False, indent=2)

    if not os.path.exists(TICKETS_FILE):
        with open(TICKETS_FILE, "w", encoding="utf-8") as f:
            json.dump({"last_id": 565, "tickets": {}}, f, ensure_ascii=False, indent=2)


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
    kb.add(types.InlineKeyboardButton("👑 Я владелец группы", callback_data="owner_start"))
    kb.add(types.InlineKeyboardButton("📝 Создать заявку", callback_data="ticket_start"))
    kb.add(types.InlineKeyboardButton("📋 Мои заявки", callback_data="my_tickets"))
    return kb


def categories_menu():
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🚫 Жалоба", callback_data="cat_Жалоба"))
    kb.add(types.InlineKeyboardButton("⚠️ Проблема", callback_data="cat_Проблема"))
    kb.add(types.InlineKeyboardButton("💡 Предложение", callback_data="cat_Предложение"))
    kb.add(types.InlineKeyboardButton("❓ Другое", callback_data="cat_Другое"))
    return kb


def admin_buttons(ticket_id):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("💬 Ответить", callback_data=f"reply_{ticket_id}"))
    kb.add(types.InlineKeyboardButton("✅ Закрыть", callback_data=f"close_{ticket_id}"))
    return kb


def groups_keyboard_for_user(user_id):
    groups = load_json(GROUPS_FILE)
    kb = types.InlineKeyboardMarkup()

    found = False
    for group_id, info in groups.items():
        if info.get("owner_id") == user_id:
            kb.add(types.InlineKeyboardButton(info.get("group_title", "Группа"), callback_data=f"select_group_{group_id}"))
            found = True

    return kb if found else None


@bot.message_handler(commands=["start"])
def start(message):
    text = (
        "👋 <b>TicketHelpBot</b>\n\n"
        "Этот бот помогает группам принимать заявки и жалобы.\n\n"
        "👑 Если ты владелец группы — нажми «Я владелец группы».\n"
        "📝 Если хочешь отправить заявку — нажми «Создать заявку»."
    )
    bot.send_message(message.chat.id, text, reply_markup=main_menu())


@bot.message_handler(commands=["setup"])
def setup_group(message):
    if message.chat.type not in ["group", "supergroup"]:
        bot.send_message(message.chat.id, "⚠️ Команду /setup нужно написать именно в группе.")
        return

    try:
        member = bot.get_chat_member(message.chat.id, message.from_user.id)
        if member.status not in ["creator", "administrator"]:
            bot.reply_to(message, "❌ Настраивать бота может только владелец или админ группы.")
            return
    except Exception:
        bot.reply_to(message, "❌ Не смог проверить права. Дай боту админку в группе.")
        return

    groups = load_json(GROUPS_FILE)

    groups[str(message.chat.id)] = {
        "group_id": message.chat.id,
        "group_title": message.chat.title,
        "owner_id": message.from_user.id,
        "owner_username": message.from_user.username,
        "created_at": datetime.now().strftime("%d.%m.%Y %H:%M")
    }

    save_json(GROUPS_FILE, groups)

    bot.reply_to(
        message,
        f"✅ <b>Группа подключена!</b>\n\n"
        f"📌 Группа: {message.chat.title}\n"
        f"👑 Владелец заявок: @{message.from_user.username if message.from_user.username else message.from_user.first_name}\n\n"
        f"Теперь заявки из этой группы будут приходить тебе в личку."
    )


@bot.message_handler(commands=["support"])
def support_group(message):
    if message.chat.type not in ["group", "supergroup"]:
        start(message)
        return

    groups = load_json(GROUPS_FILE)
    if str(message.chat.id) not in groups:
        bot.reply_to(message, "⚠️ Эта группа ещё не подключена. Админ должен написать /setup в группе.")
        return

    bot_username = bot.get_me().username
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("📝 Создать заявку", url=f"https://t.me/{bot_username}?start=ticket_{message.chat.id}"))

    bot.reply_to(
        message,
        "🛠 <b>Есть проблема или жалоба?</b>\n\n"
        "Нажми кнопку ниже и создай заявку.",
        reply_markup=kb
    )


@bot.callback_query_handler(func=lambda call: call.data == "owner_start")
def owner_start(call):
    bot.answer_callback_query(call.id)
    bot.send_message(
        call.message.chat.id,
        "👑 <b>Как подключить группу:</b>\n\n"
        "1. Добавь этого бота в свою группу.\n"
        "2. Дай ему админку.\n"
        "3. В группе напиши команду:\n\n"
        "<code>/setup</code>\n\n"
        "После этого все заявки из этой группы будут приходить тебе."
    )


@bot.callback_query_handler(func=lambda call: call.data == "ticket_start")
def ticket_start(call):
    kb = groups_keyboard_for_user(call.from_user.id)

    groups = load_json(GROUPS_FILE)
    public_kb = types.InlineKeyboardMarkup()

    for group_id, info in groups.items():
        public_kb.add(types.InlineKeyboardButton(info.get("group_title", "Группа"), callback_data=f"user_group_{group_id}"))

    if not groups:
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "⚠️ Пока нет подключенных групп.")
        return

    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, "📌 Выберите группу, куда отправить заявку:", reply_markup=public_kb)


@bot.callback_query_handler(func=lambda call: call.data.startswith("user_group_"))
def choose_group_for_ticket(call):
    group_id = call.data.replace("user_group_", "")

    groups = load_json(GROUPS_FILE)
    if group_id not in groups:
        bot.answer_callback_query(call.id, "Группа не найдена")
        return

    user_states[call.from_user.id] = {
        "step": "category",
        "group_id": group_id
    }

    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, "📌 Выберите тип заявки:", reply_markup=categories_menu())


@bot.callback_query_handler(func=lambda call: call.data.startswith("cat_"))
def choose_category(call):
    if call.from_user.id not in user_states:
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "Сначала нажмите «Создать заявку».")
        return

    category = call.data.replace("cat_", "")
    user_states[call.from_user.id]["step"] = "text"
    user_states[call.from_user.id]["category"] = category

    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, "✍️ Теперь опишите проблему одним сообщением.")


@bot.message_handler(func=lambda message: message.from_user.id in user_states)
def create_ticket_text(message):
    state = user_states.get(message.from_user.id)

    if state.get("step") != "text":
        return

    groups = load_json(GROUPS_FILE)
    group_id = state["group_id"]
    group = groups.get(group_id)

    if not group:
        bot.send_message(message.chat.id, "❌ Группа не найдена.")
        user_states.pop(message.from_user.id, None)
        return

    tickets_data = load_json(TICKETS_FILE)
    tickets_data["last_id"] += 1
    ticket_id = tickets_data["last_id"]

    username = f"@{message.from_user.username}" if message.from_user.username else "Без username"

    ticket = {
        "id": ticket_id,
        "group_id": group_id,
        "group_title": group["group_title"],
        "owner_id": group["owner_id"],
        "user_id": message.from_user.id,
        "username": username,
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
        f"📌 Группа: {ticket['group_title']}\n"
        f"📂 Тип: {ticket['category']}\n"
        f"📝 Текст: {ticket['text']}\n"
        f"⏳ Статус: На рассмотрении"
    )

    owner_text = (
        f"🚨 <b>Новая заявка #{ticket_id}</b>\n\n"
        f"📌 <b>Группа:</b> {ticket['group_title']}\n"
        f"👤 <b>От:</b> {ticket['username']}\n"
        f"📂 <b>Тип:</b> {ticket['category']}\n"
        f"🕐 <b>Дата:</b> {ticket['created_at']}\n\n"
        f"📝 <b>Текст:</b>\n{ticket['text']}"
    )

    try:
        bot.send_message(group["owner_id"], owner_text, reply_markup=admin_buttons(ticket_id))
    except Exception:
        bot.send_message(
            message.chat.id,
            "⚠️ Заявка создана, но владелец должен сначала написать боту /start, чтобы бот мог отправлять ему сообщения."
        )


@bot.callback_query_handler(func=lambda call: call.data.startswith("reply_"))
def reply_ticket(call):
    ticket_id = call.data.replace("reply_", "")
    tickets_data = load_json(TICKETS_FILE)
    ticket = tickets_data["tickets"].get(ticket_id)

    if not ticket or ticket["owner_id"] != call.from_user.id:
        bot.answer_callback_query(call.id, "Нет доступа")
        return

    owner_states[call.from_user.id] = {
        "step": "reply",
        "ticket_id": ticket_id
    }

    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, f"💬 Напиши ответ пользователю по заявке #{ticket_id}.")


@bot.message_handler(func=lambda message: message.from_user.id in owner_states)
def send_reply(message):
    state = owner_states.get(message.from_user.id)
    ticket_id = state["ticket_id"]

    tickets_data = load_json(TICKETS_FILE)
    ticket = tickets_data["tickets"].get(ticket_id)

    if not ticket:
        bot.send_message(message.chat.id, "❌ Заявка не найдена.")
        owner_states.pop(message.from_user.id, None)
        return

    bot.send_message(
        ticket["user_id"],
        f"💬 <b>Ответ по заявке #{ticket_id}</b>\n\n"
        f"{message.text}"
    )

    ticket["status"] = "Ответ отправлен"
    save_json(TICKETS_FILE, tickets_data)

    owner_states.pop(message.from_user.id, None)
    bot.send_message(message.chat.id, f"✅ Ответ по заявке #{ticket_id} отправлен.")


@bot.callback_query_handler(func=lambda call: call.data.startswith("close_"))
def close_ticket(call):
    ticket_id = call.data.replace("close_", "")
    tickets_data = load_json(TICKETS_FILE)
    ticket = tickets_data["tickets"].get(ticket_id)

    if not ticket or ticket["owner_id"] != call.from_user.id:
        bot.answer_callback_query(call.id, "Нет доступа")
        return

    ticket["status"] = "Закрыта"
    save_json(TICKETS_FILE, tickets_data)

    bot.send_message(ticket["user_id"], f"✅ <b>Заявка #{ticket_id} закрыта.</b>")
    bot.answer_callback_query(call.id, "Заявка закрыта")


@bot.callback_query_handler(func=lambda call: call.data == "my_tickets")
def my_tickets(call):
    tickets_data = load_json(TICKETS_FILE)

    my = []
    for ticket in tickets_data["tickets"].values():
        if ticket["user_id"] == call.from_user.id:
            my.append(ticket)

    if not my:
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "📋 У вас пока нет заявок.")
        return

    text = "📋 <b>Ваши заявки:</b>\n\n"
    for ticket in my[-5:]:
        text += (
            f"🟡 <b>Заявка #{ticket['id']}</b>\n"
            f"📌 Группа: {ticket['group_title']}\n"
            f"📂 Тип: {ticket['category']}\n"
            f"⏳ Статус: {ticket['status']}\n\n"
        )

    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, text)


if __name__ == "__main__":
    ensure_files()
    print("TicketHelpBot запущен...")
    bot.infinity_polling(skip_pending=True)
