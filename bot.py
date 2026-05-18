import os
import json
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

logging.basicConfig(level=logging.INFO)

TOKEN = os.environ.get("BOT_TOKEN", "8877176302:AAETTH8e3LWY0BL3pHsOpUo4huAQjzOq2bg")
CHAT_LINK = "https://t.me/+eO24OhrqxGAzZDZl"
DATA_FILE = "storage.json"
WAITING = 1
pending = {}

def load():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE) as f:
            return json.load(f)
    return {}

def save(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

async def start(u: Update, c: ContextTypes.DEFAULT_TYPE):
    await u.message.reply_text("👋 Chào!\n📥 /nap1-10 để lưu\n📤 /gui1-10 để gửi vào nhóm")

async def nap_cmd(u: Update, c: ContextTypes.DEFAULT_TYPE):
    cmd = u.message.text.split()[0][1:]
    slot = cmd.replace("nap", "")
    pending[u.effective_user.id] = slot
    await u.message.reply_text(f"📥 Gửi nội dung cho ô {slot}:")
    return WAITING

async def save_content(u: Update, c: ContextTypes.DEFAULT_TYPE):
    uid = u.effective_user.id
    slot = pending.get(uid)
    if not slot:
        return ConversationHandler.END
    data = load()
    msg = u.message
    if msg.text:
        data[slot] = {"type": "text", "content": msg.text}
    elif msg.photo:
        data[slot] = {"type": "photo", "file_id": msg.photo[-1].file_id, "caption": msg.caption or ""}
    elif msg.video:
        data[slot] = {"type": "video", "file_id": msg.video.file_id, "caption": msg.caption or ""}
    elif msg.animation:
        data[slot] = {"type": "animation", "file_id": msg.animation.file_id, "caption": msg.caption or ""}
    elif msg.document:
        data[slot] = {"type": "document", "file_id": msg.document.file_id, "caption": msg.caption or ""}
    else:
        await u.message.reply_text("❌ Không hỗ trợ định dạng này!")
        return ConversationHandler.END
    save(data)
    await u.message.reply_text(f"✅ Đã lưu ô {slot}!")
    pending.pop(uid, None)
    return ConversationHandler.END

async def gui_cmd(u: Update, c: ContextTypes.DEFAULT_TYPE):
    cmd = u.message.text.split()[0][1:]
    slot = cmd.replace("gui", "")
    data = load()
    item = data.get(slot)
    if not item:
        await u.message.reply_text(f"❌ Ô {slot} chưa có nội dung!")
        return
    try:
        t = item["type"]
        if t == "text":
            await c.bot.send_message(CHAT_LINK, item["content"])
        elif t == "photo":
            await c.bot.send_photo(CHAT_LINK, item["file_id"], caption=item["caption"])
        elif t == "video":
            await c.bot.send_video(CHAT_LINK, item["file_id"], caption=item["caption"])
        elif t == "animation":
            await c.bot.send_animation(CHAT_LINK, item["file_id"], caption=item["caption"])
        elif t == "document":
            await c.bot.send_document(CHAT_LINK, item["file_id"], caption=item["caption"])
        await u.message.reply_text(f"✅ Đã gửi ô {slot} vào nhóm!")
    except Exception as e:
        await u.message.reply_text(f"❌ Lỗi: {e}")

async def cancel(u: Update, c: ContextTypes.DEFAULT_TYPE):
    pending.pop(u.effective_user.id, None)
    await u.message.reply_text("❌ Đã hủy!")
    return ConversationHandler.END

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    for i in range(1, 11):
        conv = ConversationHandler(
            entry_points=[CommandHandler(f"nap{i}", nap_cmd)],
            states={WAITING: [MessageHandler(filters.ALL & ~filters.COMMAND, save_content)]},
            fallbacks=[CommandHandler("cancel", cancel)],
        )
        app.add_handler(conv)
        app.add_handler(CommandHandler(f"gui{i}", gui_cmd))
    print("Bot chạy!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
