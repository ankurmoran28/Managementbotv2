import asyncio
import aiosqlite
from telegram import Update, Chat
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
)
from random import choice

# === CONFIGURATION ===
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"  # <-- PUT YOUR TELEGRAM BOT TOKEN HERE
OWNER_ID = 123456789  # <-- PUT YOUR USER ID HERE

DB_PATH = "keys.db"

WELCOME_MESSAGES = [
    "👋 Welcome, {name}! Glad to have you here.",
    "Hey {name}, welcome aboard! 🚀",
    "Hello {name}! Enjoy your stay.",
    "Hi {name}, we’re happy you joined us! 😊",
    "Welcome to the bot, {name}! Need help? Type /help.",
    "Greetings, {name}! Let’s get started. 🎉",
    "🎉 Hooray, {name} just joined us!",
    "{name}, you’re now part of something awesome.",
    "Hey {name}, glad you stopped by! Let’s explore together.",
    "Hi {name}! Looking forward to chatting with you.",
    "Welcome, {name}! We hope you enjoy our features. 🌟",
    "It’s great to see you, {name}!",
    "Hello {name}, let’s achieve great things together! 💪",
    "A big welcome to you, {name}! 🎈",
    "Hi {name}, let’s make your experience amazing.",
    "{name}, thanks for joining! You’re in the right place.",
    "Welcome, {name}! Don’t hesitate to ask if you need anything.",
    "Hey {name}, your journey starts now! 🚀",
    "Hello {name}! Ready to get started?",
    "Glad to have you with us, {name}!",
    "Welcome, {name}! This is the beginning of something great. 🌠"
]

# === DATABASE INIT ===
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""CREATE TABLE IF NOT EXISTS keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT NOT NULL UNIQUE,
            expiry DATE,
            device_limit INTEGER DEFAULT 1,
            used_count INTEGER DEFAULT 0,
            type TEXT DEFAULT 'single', -- 'single' or 'universal'
            group_id INTEGER,           -- NULL means any group
            note TEXT
        )""")
        await db.execute("""CREATE TABLE IF NOT EXISTS admins (
            user_id INTEGER PRIMARY KEY
        )""")
        await db.execute("""CREATE TABLE IF NOT EXISTS keylogs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            key_id INTEGER,
            key TEXT,
            group_id INTEGER,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )""")
        await db.execute("""CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            message TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )""")
        await db.commit()

# === PERMISSION DECORATORS ===
async def is_admin(user_id: int):
    if user_id == OWNER_ID:
        return True
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT 1 FROM admins WHERE user_id=?", (user_id,)) as cur:
            return await cur.fetchone() is not None

def admin_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await is_admin(update.effective_user.id):
            await update.message.reply_text("🚫 <b>Only admins can use this command.</b>", parse_mode="HTML")
            return
        return await func(update, context)
    return wrapper

def owner_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != OWNER_ID:
            await update.message.reply_text("👑 <b>Only the bot owner can use this command.</b>", parse_mode="HTML")
            return
        return await func(update, context)
    return wrapper

def private_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.message.chat.type != "private":
            await update.message.reply_text("🔒 <b>Please use this command in a private chat with me!</b>", parse_mode="HTML")
            return
        return await func(update, context)
    return wrapper

# === BOT COMMANDS ===

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.effective_user.first_name
    await update.message.reply_text(choice(WELCOME_MESSAGES).format(name=name))

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "<b>🤖 KeyBot Help Menu</b>\n\n"
        "<b>Main Commands:</b>\n"
        "• /key - Get a key (private only)\n"
        "• /listkeys - List all keys\n"
        "• /feedback <message> - Send feedback\n"
        "• /id - Get your user and chat ID\n\n"
        "<b>Admin Commands:</b>\n"
        "• /addkey <key> <expiry YYYY-MM-DD> <device_limit> <single|universal> [group_id or 'any'] [note]\n"
        "• /delkey <key>\n"
        "• /listadmins\n\n"
        "<b>Owner Commands:</b>\n"
        "• /addadmin <user_id>\n"
        "• /removeadmin <user_id>\n",
        parse_mode="HTML"
    )

async def id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    msg = f"👤 <b>Your User ID:</b> <code>{user.id}</code>"
    if chat.type in ["group", "supergroup"]:
        msg += f"\n👥 <b>Group ID:</b> <code>{chat.id}</code>"
    await update.message.reply_text(msg, parse_mode="HTML")

async def listadmins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id FROM admins") as cur:
            admins = await cur.fetchall()
    admin_list = [f"👑 <b>Owner:</b> <code>{OWNER_ID}</code>"] + [f"🔑 <b>Admin:</b> <code>{row[0]}</code>" for row in admins if row[0] != OWNER_ID]
    await update.message.reply_text("\n".join(admin_list), parse_mode="HTML")

@owner_only
async def addadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /addadmin <user_id>")
        return
    try:
        user_id = int(context.args[0])
    except Exception:
        await update.message.reply_text("User ID must be a number.")
        return
    if user_id == OWNER_ID:
        await update.message.reply_text("Owner is always admin.")
        return
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (user_id,))
        await db.commit()
    await update.message.reply_text(f"✅ <b>User</b> <code>{user_id}</code> <b>added as admin.</b>", parse_mode="HTML")

@owner_only
async def removeadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /removeadmin <user_id>")
        return
    try:
        user_id = int(context.args[0])
    except Exception:
        await update.message.reply_text("User ID must be a number.")
        return
    if user_id == OWNER_ID:
        await update.message.reply_text("Owner cannot be removed.")
        return
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM admins WHERE user_id=?", (user_id,))
        await db.commit()
    await update.message.reply_text(f"🗑️ <b>Removed admin</b> <code>{user_id}</code>.", parse_mode="HTML")

@admin_only
async def addkey(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 4:
        await update.message.reply_text("Usage: /addkey <key> <expiry YYYY-MM-DD> <device_limit> <single|universal> [group_id or 'any'] [note]")
        return
    key, expiry, device_limit, key_type = context.args[:4]
    group_id = None
    note = None
    if len(context.args) > 4:
        group_arg = context.args[4]
        if group_arg.lower() != 'any':
            try:
                group_id = int(group_arg)
            except Exception:
                note = ' '.join(context.args[4:])
        if group_id:
            note = ' '.join(context.args[5:]) if len(context.args) > 5 else None
        else:
            note = ' '.join(context.args[5:]) if len(context.args) > 5 else ' '.join(context.args[4:])
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute(
                "INSERT INTO keys (key, expiry, device_limit, used_count, type, group_id, note) VALUES (?, ?, ?, 0, ?, ?, ?)",
                (key, expiry, int(device_limit), key_type, group_id, note)
            )
            await db.commit()
        except Exception as e:
            await update.message.reply_text(f"❌ <b>Error:</b> <code>{e}</code>", parse_mode="HTML")
            return
    await update.message.reply_text(f"✅ <b>Key</b> <code>{key}</code> <b>added.</b>", parse_mode="HTML")

@admin_only
async def delkey(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /delkey <key>")
        return
    key = context.args[0]
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM keys WHERE key = ?", (key,))
        await db.commit()
    await update.message.reply_text(f"🗑️ <b>Key</b> <code>{key}</code> <b>deleted.</b>", parse_mode="HTML")

async def listkeys(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT key, expiry, device_limit, used_count, type, group_id, note FROM keys ORDER BY expiry DESC") as cursor:
            keys = await cursor.fetchall()
    if not keys:
        await update.message.reply_text("No keys in the database.")
        return
    msg = "🔑 <b>All Keys:</b>\n"
    for k in keys:
        gid = f"<code>{k[5]}</code>" if k[5] else "Any"
        note = f"📝 {k[6]}" if k[6] else ""
        msg += (
            f"\n<b>{k[0]}</b> | <i>{k[4]}</i> | "
            f"{k[3]}/{k[2]} used | ⏳ <b>{k[1]}</b> | 👥 <b>{gid}</b> {note}"
        )
    await update.message.reply_text(msg, parse_mode="HTML")

@private_only
async def key_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username
    async with aiosqlite.connect(DB_PATH) as db:
        now = await db.execute_fetchone("SELECT date('now')")
        now = now[0]
        # 1. Universal, any group
        async with db.execute(
            "SELECT id, key, expiry, device_limit, used_count, note FROM keys WHERE type='universal' AND (group_id IS NULL) AND expiry >= ? AND used_count < device_limit",
            (now,)
        ) as cur:
            row = await cur.fetchone()
            if row:
                await db.execute("UPDATE keys SET used_count = used_count + 1 WHERE id = ?", (row[0],))
                await db.execute(
                    "INSERT INTO keylogs (user_id, username, key_id, key, group_id) VALUES (?, ?, ?, ?, ?)",
                    (user_id, username, row[0], row[1], None)
                )
                await db.commit()
                await update.message.reply_text(
                    f"🌐 <b>Your Key:</b> <code>{row[1]}</code>\n"
                    f"⏳ <b>Expiry:</b> {row[2]}\n"
                    f"📱 <b>Remaining Devices:</b> {row[3] - row[4] - 1}\n"
                    f"{f'📝 {row[5]}' if row[5] else ''}",
                    parse_mode="HTML"
                )
                return
        # 2. Single-use, any group
        async with db.execute(
            "SELECT id, key, expiry, note FROM keys WHERE type='single' AND (group_id IS NULL) AND used_count = 0 AND expiry >= ?",
            (now,)
        ) as cur:
            row = await cur.fetchone()
            if row:
                await db.execute("UPDATE keys SET used_count = 1 WHERE id = ?", (row[0],))
                await db.execute(
                    "INSERT INTO keylogs (user_id, username, key_id, key, group_id) VALUES (?, ?, ?, ?, ?)",
                    (user_id, username, row[0], row[1], None)
                )
                await db.commit()
                await update.message.reply_text(
                    f"🔑 <b>Your Key:</b> <code>{row[1]}</code>\n"
                    f"⏳ <b>Expiry:</b> {row[2]}\n"
                    f"📱 <b>For One Device Only</b>\n"
                    f"{f'📝 {row[3]}' if row[3] else ''}",
                    parse_mode="HTML"
                )
                return
        await update.message.reply_text("❌ <b>No keys available.</b>", parse_mode="HTML")

async def feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = " ".join(context.args)
    if not msg:
        await update.message.reply_text("Usage: /feedback <your message>")
        return
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO feedback (user_id, message) VALUES (?, ?)", (update.effective_user.id, msg))
        await db.commit()
    await update.message.reply_text("✅ <b>Feedback received, thank you!</b>", parse_mode="HTML")

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❓ <b>Unknown command.</b> Use /help.", parse_mode="HTML")

# === MAIN ===
def main():
    asyncio.get_event_loop().run_until_complete(init_db())
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("id", id_command))
    app.add_handler(CommandHandler("addadmin", addadmin))
    app.add_handler(CommandHandler("removeadmin", removeadmin))
    app.add_handler(CommandHandler("listadmins", listadmins))
    app.add_handler(CommandHandler("addkey", addkey))
    app.add_handler(CommandHandler("delkey", delkey))
    app.add_handler(CommandHandler("listkeys", listkeys))
    app.add_handler(CommandHandler("key", key_command))
    app.add_handler(CommandHandler("feedback", feedback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown))
    print("Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()