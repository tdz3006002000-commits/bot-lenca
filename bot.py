import os
import json
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

TOKEN = "8877176302:AAETTH8e3LWY0BL3pHsOpUo4huAQjzOq2bg"
CHAT_LINK = "https://t.me/+eO24OhrqxGAzZDZl"
DATA_FILE = "storage.json"

WAITING_CONTENT = 1
current_slot = {}

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

async def nap(update: Update, context: ContextTypes.DEFAULT_TYPE, slot: int):
    current_slot[update.effective_user.id] = slot
    await update.message.reply_text(f"📥 Gửi nội dung cho ô số {slot} (tin nhắn, ảnh, video, gif...):")
    return WAITING_CONTENT

async def save_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    slot = current_slot.get(user_id)
    if slot is None:
        return ConversationHandler.END

    data = load_data()
    msg = update.message

    if msg.text:
        data[str(slot)] = {"type": "text", "content": msg.text}
    elif msg.photo:
        data[str(slot)] = {"type": "photo", "file_id": msg.photo[-1].file_id, "caption": msg.caption or ""}
    elif msg.video:
        data[str(slot)] = {"type": "video", "file_id": msg.video.file_id, "caption": msg.caption or ""}
    elif msg.animation:
        data[str(slot)] = {"type": "animation", "file_id": msg.animation.file_id, "caption": msg.caption or ""}
    elif msg.document:
        data[str(slot)] = {"type": "document", "file_id": msg.document.file_id, "caption": msg.caption or ""}
    else:
        await update.message.reply_text("❌ Định dạng không hỗ trợ!")
        return ConversationHandler.END

    save_data(data)
    await update.message.reply_text(f"✅ Đã lưu vào ô số {slot}!")
    current_slot.pop(user_id, None)
    return ConversationHandler.END

async def gui(update: Update, context: ContextTypes.DEFAULT_TYPE, slot: int):
    data = load_data()
    item = data.get(str(slot))

    if not item:
        await update.message.reply_text(f"❌ Ô số {slot} chưa có nội dung!")
        return

    chat_id = CHAT_LINK
    try:
        if item["type"] == "text":
            await context.bot.send_message(chat_id=chat_id, text=item["content"])
        elif item["type"] == "photo":
            await context.bot.send_photo(chat_id=chat_id, photo=item["file_id"], caption=item["caption"])
        elif item["type"] == "video":
            await context.bot.send_video(chat_id=chat_id, video=item["file_id"], caption=item["caption"])
        elif item["type"] == "animation":
            await context.bot.send_animation(chat_id=chat_id, animation=item["file_id"], caption=item["caption"])
        elif item["type"] == "document":
            await context.bot.send_document(chat_id=chat_id, document=item["file_id"], caption=item["caption"])
        await update.message.reply_text(f"✅ Đã gửi ô số {slot} vào nhóm!")
    except Exception as e:
        await update.message.reply_text(f"❌ Lỗi: {str(e)}\nHãy chắc bot đã được thêm vào nhóm và là admin!")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    current_slot.pop(update.effective_user.id, None)
    await update.message.reply_text("❌ Đã hủy!")
    return ConversationHandler.END

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Chào mừng!\n\n"
        "📥 Lệnh lưu: /nap1 đến /nap10\n"
        "📤 Lệnh gửi: /gui1 đến /gui10\n\n"
        "Ví dụ: gõ /nap1 rồi gửi ảnh/video/text để lưu vào ô 1\n"
        "Gõ /gui1 để gửi ô 1 vào nhóm"
    )

def make_nap_handler(slot):
    async def handler(update, context):
        return await nap(update, context, slot)
    return handler

def make_gui_handler(slot):
    async def handler(update, context):
        return await gui(update, context, slot)
    return handler

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    for i in range(1, 11):
        conv = ConversationHandler(
            entry_points=[CommandHandler(f"nap{i}", make_nap_handler(i))],
            states={WAITING_CONTENT: [MessageHandler(filters.ALL & ~filters.COMMAND, save_content)]},
            fallbacks=[CommandHandler("cancel", cancel)],
        )
        app.add_handler(conv)
        app.add_handler(CommandHandler(f"gui{i}", make_gui_handler(i)))

    print("Bot đang chạy...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
