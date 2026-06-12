# ticket_help_bot.py
# Telegram бот заявок для групп
# 1 группа = 1 владелец
# Подключение через уникальный код /connectXXXX
# Владелец бота может подключать любую группу даже без админки
# Без базы данных: всё хранится в JSON-файлах
#
# Render:
# Build Command: pip install pyTelegramBotAPI
# Start Command: python ticket_help_bot.py
#
# Environment Variables:
# TOKEN = токен бота от BotFather
# BOT_OWNER_ID = твой Telegram ID

import json
import os
import random
from datetime import datetime

import telebot
from telebot import types


TOKEN = os.getenv("TOKEN")
BOT_OWNER_ID = int(os.getenv("BOT_OWNER_ID", "0"))

if not TOKEN:
    raise ValueError("Не найден TOKEN. Добавь TOKEN в Environment Variables на Render.")

if ":" not in TOKEN:
    raise ValueError("TOKEN неправильный. В токене Telegram должно быть двоеточие, например 123456789:AA...")

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

DATA_DIR = "data"
GROUPS_FILE = os.path.join(DATA_DIR, "groups.json")
TICKETS_FILE = os.path.join(DATA_DIR, "tickets.json")
USERS_FILE = os.path.join(DATA_DIR, "users.json")
CONNECT_CODES_FILE = os.path.join(DATA_DIR, "connect_codes.json")

user_states = {}
owner_reply_states = {}


def ensure_files():
    os.makedirs(DATA_DIR, exist_ok=True)

    default_files = {
        GROUPS_FILE: {},
        USERS_FILE: {},
        CONNECT_CODES_FILE: {},
        TICKETS_FILE: {"last_id": 565, "tickets": {}}
    }

    for path, default_data in default_files.items():
        if not os.path.exists(path):
            with open(path, "w", encoding="utf-8") as f:
                json.dump(default_data, f, ensure_ascii=False, indent=2)


def load_json(path):
    ensure_files()
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    ensure_files()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def now_time():
    return datetime.now().strftime("%d.%m.%Y %H:%M")


def name_of(user):
    if user.username:
        return f"@{user.username}"
    return user.first_name or "Пользователь"


def is_bot_owner(user_id):
    return BOT_OWNER_ID != 0 and user_id == BOT_OWNER_ID


def save_user(user, role="member"):
    users = load_json(USERS_FILE)
    uid = str(user.id)

    old_role = users.get(uid, {}).get("role")
    final_role = old_role if old_role in ["bot_owner", "owner", "admin"] else role

    if is_bot_owner(user.id):
        final_role = "bot_owner"

    users[uid] = {
        "id": user.id,
        "name": name_of(user),
        "username": user.username,
        "role": final_role,
        "last_seen": now_time()
    }

    save_json(USERS_FILE, users)


def main_menu():
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("👑 Подключить группу", callback_data="connect_group"))
    kb.add(types.InlineKeyboardButton("📝 Создать заявку", callback_data="create_ticket"))
    kb.add(types.InlineKeyboardButton("📋 Мои заявки", callback_data="my_tickets"))
    kb.add(types.InlineKeyboardButton("⚙️ Мои группы", callback_data="my_groups_btn"))
    return kb


def categories_menu():
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🚫 Жалоба", callback_data="cat_Жалоба"))
    kb.add(types.InlineKeyboardButton("⚠️ Проблема", callback_data="cat_Проблема"))
    kb.add(types.InlineKeyboardButton("💡 Предложение", callback_data="cat_Предложение"))
    kb.add(types.InlineKeyboardButton("❓ Другое", callback_data="cat_Другое"))
    return kb


def owner_ticket_buttons(ticket_id):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("💬 Ответить", callback_data=f"owner_reply:{ticket_id}"))
    kb.add(types.InlineKeyboardButton("✅ Закрыть", callback_data=f"owner_close:{ticket_id}"))
    kb.add(types.InlineKeyboardButton("❌ Отклонить", callback_data=f"owner_reject:{ticket_id}"))
    return kb


def group_manage_buttons(group_id):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🚪 Отключить группу", callback_data=f"disconnect_group:{group_id}"))
    return kb


def create_connect_code(owner_id):
    codes = load_json(CONNECT_CODES_FILE)

    for code, info in list(codes.items()):
        if info["owner_id"] == owner_id:
            return code

    while True:
        code = str(random.randint(1000, 9999))
        if code not in codes:
            break

    codes[code] = {
        "owner_id": owner_id,
        "created_at": now_time()
    }

    save_json(CONNECT_CODES_FILE, codes)
    return code


def check_group_admin(chat_id, user_id):
    try:
        member = bot.get_chat_member(chat_id, user_id)
        return member.status in ["creator", "administrator"]
    except Exception:
        return False


def can_connect_group(chat_id, user_id):
    if is_bot_owner(user_id):
        return True
    return check_group_admin(chat_id, user_id)


def get_my_groups(user_id):
    groups = load_json(GROUPS_FILE)
    found = []

    for group_id, info in groups.items():
        if info.get("owner_id") == user_id or is_bot_owner(user_id):
            found.append((group_id, info))

    return found


@bot.message_handler(content_types=["new_chat_members"])
def bot_added_to_group(message):
    for member in message.new_chat_members:
        if member.id == bot.get_me().id:
            bot_username = bot.get_me().username
            kb = types.InlineKeyboardMarkup()
            kb.add(types.InlineKeyboardButton("👑 Подключить группу", url=f"https://t.me/{bot_username}?start=connect"))

            bot.send_message(
                message.chat.id,
                "👋 <b>TicketHelpBot</b>\n\n"
                "Этот бот помогает группе принимать:\n"
                "📝 заявки\n"
                "🚫 жалобы\n"
                "❓ вопросы\n"
                "💡 предложения\n\n"
                "Чтобы подключить группу:\n\n"
                "1. Владелец открывает бота в личке.\n"
                "2. Нажимает «👑 Подключить группу».\n"
                "3. Получает уникальную команду.\n"
                "4. Пишет эту команду здесь в группе.\n\n"
                "После подключения все заявки из этой группы будут приходить владельцу в личку.",
                reply_markup=kb
            )


@bot.message_handler(commands=["start"])
def start(message):
    save_user(message.from_user)

    bot.send_message(
        message.chat.id,
        "👋 <b>TicketHelpBot</b>\n\n"
        "Это бот для принятия заявок, жалоб, вопросов и предложений в Telegram-группах.\n\n"
        "Выберите действие:",
        reply_markup=main_menu()
    )


@bot.callback_query_handler(func=lambda call: call.data == "connect_group")
def connect_group_info(call):
    role = "bot_owner" if is_bot_owner(call.from_user.id) else "owner"
    save_user(call.from_user, role=role)

    code = create_connect_code(call.from_user.id)

    extra = ""
    if is_bot_owner(call.from_user.id):
        extra = "\n\n⭐ Ты владелец бота, поэтому можешь подключить группу даже без админки."

    bot.answer_callback_query(call.id)
    bot.send_message(
        call.message.chat.id,
        "👑 <b>Подключение группы</b>\n\n"
        "1. Добавь этого бота в группу.\n"
        "2. Напиши в группе команду:\n\n"
        f"<code>/connect{code}</code>\n\n"
        "📌 Это уникальный код именно для тебя.\n\n"
        "Обычный участник не сможет подключить группу.\n"
        "Подключить может админ группы или владелец бота."
        f"{extra}\n\n"
        "После подключения все заявки из этой группы будут приходить тебе."
    )


@bot.message_handler(func=lambda message: message.chat.type in ["group", "supergroup"] and message.text and message.text.startswith("/connect"))
def connect_group(message):
    save_user(message.from_user)

    code = message.text.replace("/connect", "").split()[0].strip()

    if not code:
        bot.reply_to(message, "⚠️ Нужен код подключения. Например: <code>/connect4821</code>")
        return

    codes = load_json(CONNECT_CODES_FILE)

    if code not in codes:
        bot.reply_to(message, "❌ Неверный код подключения.")
        return

    owner_id = codes[code]["owner_id"]

    if owner_id != message.from_user.id:
        bot.reply_to(message, "❌ Этот код принадлежит другому человеку.")
        return

    if not can_connect_group(message.chat.id, message.from_user.id):
        bot.reply_to(message, "❌ Подключить группу может только админ группы или владелец бота.")
        return

    groups = load_json(GROUPS_FILE)
    group_id = str(message.chat.id)

    if group_id in groups:
        bot.reply_to(
            message,
            "❌ <b>Эта группа уже подключена.</b>\n\n"
            f"👑 Владелец: {groups[group_id].get('owner_name', 'Неизвестно')}"
        )
        return

    role_name = "bot_owner" if is_bot_owner(message.from_user.id) else "owner"

    groups[group_id] = {
        "group_id": message.chat.id,
        "group_title": message.chat.title,
        "owner_id": message.from_user.id,
        "owner_name": name_of(message.from_user),
        "owner_username": message.from_user.username,
        "connected_by_role": role_name,
        "admins": {
            str(message.from_user.id): name_of(message.from_user)
        },
        "created_at": now_time(),
        "active": True
    }

    save_json(GROUPS_FILE, groups)
    save_user(message.from_user, "bot_owner" if is_bot_owner(message.from_user.id) else "owner")

    bot.reply_to(
        message,
        "✅ <b>Группа подключена!</b>\n\n"
        f"📌 Группа: {message.chat.title}\n"
        f"👑 Владелец заявок: {name_of(message.from_user)}\n\n"
        "Теперь все заявки из этой группы будут приходить владельцу в личку."
    )


@bot.message_handler(commands=["setup"])
def old_setup(message):
    if message.chat.type in ["group", "supergroup"]:
        bot.reply_to(
            message,
            "⚠️ Подключение делается через уникальный код.\n\n"
            "Открой бота в личке, нажми «👑 Подключить группу» и получи команду."
        )
    else:
        start(message)


@bot.message_handler(commands=["support"])
def support_group(message):
    save_user(message.from_user)

    if message.chat.type not in ["group", "supergroup"]:
        start(message)
        return

    groups = load_json(GROUPS_FILE)
    group_id = str(message.chat.id)

    if group_id not in groups or not groups[group_id].get("active", True):
        bot.reply_to(message, "⚠️ Группа ещё не подключена. Владелец должен подключить группу через личку бота.")
        return

    bot_username = bot.get_me().username

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("📝 Создать заявку", url=f"https://t.me/{bot_username}?start=ticket"))

    bot.reply_to(
        message,
        "🛠 <b>Есть проблема или жалоба?</b>\n\n"
        "Нажми кнопку ниже и создай заявку.",
        reply_markup=kb
    )


@bot.callback_query_handler(func=lambda call: call.data == "create_ticket")
def create_ticket(call):
    save_user(call.from_user)

    groups = load_json(GROUPS_FILE)
    active_groups = {gid: info for gid, info in groups.items() if info.get("active", True)}

    if not active_groups:
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "⚠️ Пока нет подключенных групп.")
        return

    kb = types.InlineKeyboardMarkup()

    for group_id, info in active_groups.items():
        kb.add(types.InlineKeyboardButton(info["group_title"], callback_data=f"choose_group:{group_id}"))

    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, "📌 Выберите группу, куда отправить заявку:", reply_markup=kb)


@bot.callback_query_handler(func=lambda call: call.data.startswith("choose_group:"))
def choose_group(call):
    save_user(call.from_user)

    group_id = call.data.split(":", 1)[1]
    groups = load_json(GROUPS_FILE)

    if group_id not in groups or not groups[group_id].get("active", True):
        bot.answer_callback_query(call.id, "Группа не найдена")
        return

    user_states[call.from_user.id] = {
        "step": "choose_category",
        "group_id": group_id
    }

    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, "📂 Выберите тип заявки:", reply_markup=categories_menu())


@bot.callback_query_handler(func=lambda call: call.data.startswith("cat_"))
def choose_category(call):
    save_user(call.from_user)

    if call.from_user.id not in user_states:
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "Сначала нажмите «Создать заявку».")
        return

    category = call.data.replace("cat_", "")
    user_states[call.from_user.id]["step"] = "write_text"
    user_states[call.from_user.id]["category"] = category

    bot.answer_callback_query(call.id)
    bot.send_message(
        call.message.chat.id,
        f"✍️ <b>Тип заявки:</b> {category}\n\n"
        "Опишите проблему одним сообщением."
    )


@bot.message_handler(func=lambda message: message.from_user.id in user_states)
def save_ticket(message):
    save_user(message.from_user)

    state = user_states.get(message.from_user.id)

    if state.get("step") != "write_text":
        return

    groups = load_json(GROUPS_FILE)
    group_id = state["group_id"]

    if group_id not in groups or not groups[group_id].get("active", True):
        bot.send_message(message.chat.id, "❌ Группа не найдена или отключена.")
        user_states.pop(message.from_user.id, None)
        return

    group = groups[group_id]

    tickets_data = load_json(TICKETS_FILE)
    tickets_data["last_id"] += 1
    ticket_id = tickets_data["last_id"]

    ticket = {
        "id": ticket_id,
        "group_id": group_id,
        "group_title": group["group_title"],
        "owner_id": group["owner_id"],
        "owner_name": group["owner_name"],
        "user_id": message.from_user.id,
        "user_name": name_of(message.from_user),
        "category": state["category"],
        "text": message.text,
        "status": "На рассмотрении",
        "created_at": now_time()
    }

    tickets_data["tickets"][str(ticket_id)] = ticket
    save_json(TICKETS_FILE, tickets_data)

    user_states.pop(message.from_user.id, None)

    bot.send_message(
        message.chat.id,
        f"✅ <b>Заявка #{ticket_id} создана!</b>\n\n"
        f"📌 <b>Группа:</b> {ticket['group_title']}\n"
        f"📂 <b>Тип:</b> {ticket['category']}\n"
        f"📝 <b>Текст:</b> {ticket['text']}\n"
        f"⏳ <b>Статус:</b> На рассмотрении\n\n"
        "Ответ придёт сюда в бота."
    )

    owner_text = (
        f"🚨 <b>Новая заявка #{ticket_id}</b>\n\n"
        f"📌 <b>Группа:</b> {ticket['group_title']}\n"
        f"👤 <b>От:</b> {ticket['user_name']}\n"
        f"📂 <b>Тип:</b> {ticket['category']}\n"
        f"🕐 <b>Дата:</b> {ticket['created_at']}\n\n"
        f"📝 <b>Текст:</b>\n{ticket['text']}"
    )

    try:
        bot.send_message(group["owner_id"], owner_text, reply_markup=owner_ticket_buttons(ticket_id))
    except Exception:
        bot.send_message(
            message.chat.id,
            "⚠️ Заявка создана, но владелец группы должен сначала написать боту /start в личке."
        )


@bot.callback_query_handler(func=lambda call: call.data == "my_groups_btn")
def my_groups_btn(call):
    save_user(call.from_user)

    found = get_my_groups(call.from_user.id)

    if not found:
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "👑 У вас пока нет подключенных групп.")
        return

    bot.answer_callback_query(call.id)

    for group_id, group in found:
        status = "✅ Активна" if group.get("active", True) else "🚫 Отключена"
        bot.send_message(
            call.message.chat.id,
            f"⚙️ <b>Управление группой</b>\n\n"
            f"📌 Группа: {group['group_title']}\n"
            f"👑 Владелец: {group['owner_name']}\n"
            f"📍 Статус: {status}\n"
            f"🕐 Подключена: {group['created_at']}",
            reply_markup=group_manage_buttons(group_id)
        )


@bot.callback_query_handler(func=lambda call: call.data.startswith("disconnect_group:"))
def disconnect_group(call):
    save_user(call.from_user)

    group_id = call.data.split(":", 1)[1]
    groups = load_json(GROUPS_FILE)

    if group_id not in groups:
        bot.answer_callback_query(call.id, "Группа не найдена")
        return

    group = groups[group_id]

    if group.get("owner_id") != call.from_user.id and not is_bot_owner(call.from_user.id):
        bot.answer_callback_query(call.id, "Нет доступа")
        return

    group_title = group.get("group_title", "Группа")

    del groups[group_id]
    save_json(GROUPS_FILE, groups)

    bot.answer_callback_query(call.id, "Группа отключена")
    bot.send_message(
        call.message.chat.id,
        f"🚪 <b>Группа отключена</b>\n\n"
        f"📌 {group_title}\n\n"
        "Теперь заявки из этой группы больше не принимаются."
    )

    try:
        bot.send_message(int(group_id), "🚪 Бот отключён от заявок этой группы и сейчас выйдет из чата.")
        bot.leave_chat(int(group_id))
    except Exception:
        pass


@bot.callback_query_handler(func=lambda call: call.data.startswith("owner_reply:"))
def owner_reply(call):
    save_user(call.from_user)

    ticket_id = call.data.split(":", 1)[1]
    tickets_data = load_json(TICKETS_FILE)
    ticket = tickets_data["tickets"].get(ticket_id)

    if not ticket:
        bot.answer_callback_query(call.id, "Заявка не найдена")
        return

    if ticket["owner_id"] != call.from_user.id and not is_bot_owner(call.from_user.id):
        bot.answer_callback_query(call.id, "Нет доступа")
        return

    owner_reply_states[call.from_user.id] = ticket_id

    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, f"💬 Напишите ответ пользователю по заявке #{ticket_id}.")


@bot.message_handler(func=lambda message: message.from_user.id in owner_reply_states)
def send_owner_reply(message):
    save_user(message.from_user)

    ticket_id = owner_reply_states.get(message.from_user.id)

    tickets_data = load_json(TICKETS_FILE)
    ticket = tickets_data["tickets"].get(str(ticket_id))

    if not ticket:
        bot.send_message(message.chat.id, "❌ Заявка не найдена.")
        owner_reply_states.pop(message.from_user.id, None)
        return

    try:
        bot.send_message(
            ticket["user_id"],
            f"💬 <b>Ответ по заявке #{ticket_id}</b>\n\n"
            f"{message.text}"
        )
    except Exception:
        bot.send_message(message.chat.id, "❌ Не смог отправить ответ пользователю.")
        return

    ticket["status"] = "Ответ отправлен"
    save_json(TICKETS_FILE, tickets_data)

    owner_reply_states.pop(message.from_user.id, None)
    bot.send_message(message.chat.id, f"✅ Ответ по заявке #{ticket_id} отправлен.")


@bot.callback_query_handler(func=lambda call: call.data.startswith("owner_close:"))
def owner_close(call):
    save_user(call.from_user)

    ticket_id = call.data.split(":", 1)[1]
    tickets_data = load_json(TICKETS_FILE)
    ticket = tickets_data["tickets"].get(ticket_id)

    if not ticket:
        bot.answer_callback_query(call.id, "Заявка не найдена")
        return

    if ticket["owner_id"] != call.from_user.id and not is_bot_owner(call.from_user.id):
        bot.answer_callback_query(call.id, "Нет доступа")
        return

    ticket["status"] = "Закрыта"
    save_json(TICKETS_FILE, tickets_data)

    try:
        bot.send_message(ticket["user_id"], f"✅ <b>Заявка #{ticket_id} закрыта.</b>")
    except Exception:
        pass

    bot.answer_callback_query(call.id, "Заявка закрыта")


@bot.callback_query_handler(func=lambda call: call.data.startswith("owner_reject:"))
def owner_reject(call):
    save_user(call.from_user)

    ticket_id = call.data.split(":", 1)[1]
    tickets_data = load_json(TICKETS_FILE)
    ticket = tickets_data["tickets"].get(ticket_id)

    if not ticket:
        bot.answer_callback_query(call.id, "Заявка не найдена")
        return

    if ticket["owner_id"] != call.from_user.id and not is_bot_owner(call.from_user.id):
        bot.answer_callback_query(call.id, "Нет доступа")
        return

    ticket["status"] = "Отклонена"
    save_json(TICKETS_FILE, tickets_data)

    try:
        bot.send_message(ticket["user_id"], f"❌ <b>Заявка #{ticket_id} отклонена.</b>")
    except Exception:
        pass

    bot.answer_callback_query(call.id, "Заявка отклонена")


@bot.callback_query_handler(func=lambda call: call.data == "my_tickets")
def my_tickets(call):
    save_user(call.from_user)

    tickets_data = load_json(TICKETS_FILE)
    my = []

    for ticket in tickets_data["tickets"].values():
        if ticket["user_id"] == call.from_user.id:
            my.append(ticket)

    if not my:
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "📋 У вас пока нет заявок.")
        return

    text = "📋 <b>Ваши последние заявки:</b>\n\n"

    for ticket in my[-10:]:
        text += (
            f"🟡 <b>Заявка #{ticket['id']}</b>\n"
            f"📌 Группа: {ticket['group_title']}\n"
            f"📂 Тип: {ticket['category']}\n"
            f"⏳ Статус: {ticket['status']}\n\n"
        )

    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, text)


@bot.message_handler(commands=["my_groups"])
def my_groups_command(message):
    save_user(message.from_user)

    found = get_my_groups(message.from_user.id)

    if not found:
        bot.send_message(message.chat.id, "👑 У вас пока нет подключенных групп.")
        return

    for group_id, group in found:
        status = "✅ Активна" if group.get("active", True) else "🚫 Отключена"
        bot.send_message(
            message.chat.id,
            f"⚙️ <b>Управление группой</b>\n\n"
            f"📌 Группа: {group['group_title']}\n"
            f"👑 Владелец: {group['owner_name']}\n"
            f"📍 Статус: {status}\n"
            f"🕐 Подключена: {group['created_at']}",
            reply_markup=group_manage_buttons(group_id)
        )


if __name__ == "__main__":
    ensure_files()
    print("TicketHelpBot запущен...")
    bot.infinity_polling(skip_pending=True)
