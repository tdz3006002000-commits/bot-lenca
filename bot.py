import os
import json
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

logging.basicConfig(level=logging.INFO)

TOKEN = os.environ.get("BOT_TOKEN", "8877176302:AAETTH8e3LWY0BL3pHsOpUo4huAQjzOq2bg")
CHAT_LINK = "-1003617964607"
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
    await u.message.reply_text(
        "👋 Chào!\n"
        "📥 /nap1-10 để lưu\n"
        "📤 /gui1-10 để gửi vào nhóm\n"
        "🔄 /doi1-10 để đổi nội dung\n"
        "⚡ /doiXguiY để đổi ô X và gửi ô Y lên nhóm luôn"
    )

async def nap_cmd(u: Update, c: ContextTypes.DEFAULT_TYPE):
    cmd = u.message.text.split()[0][1:]
    slot = cmd.replace("nap", "")
    pending[u.effective_user.id] = ("nap", slot, None)
    await u.message.reply_text(f"📥 Gửi nội dung cho ô {slot}:")
    return WAITING

async def doi_cmd(u: Update, c: ContextTypes.DEFAULT_TYPE):
    cmd = u.message.text.split()[0][1:]
    if "gui" in cmd:
        parts = cmd.split("gui")
        slot_doi = parts[0].replace("doi", "")
        slot_gui = parts[1]
        pending[u.effective_user.id] = ("doigui", slot_doi, slot_gui)
        await u.message.reply_text(f"🔄 Gửi nội dung mới cho ô {slot_doi} (sẽ gửi ô {slot_gui} lên nhóm):")
    else:
        slot = cmd.replace("doi", "")
        pending[u.effective_user.id] = ("doi", slot, None)
        await u.message.reply_text(f"🔄 Gửi nội dung mới cho ô {slot}:")
    return WAITING

async def handle_content(u: Update, c: ContextTypes.DEFAULT_TYPE):
    uid = u.effective_user.id
    info = pending.get(uid)
    if not info:
        return ConversationHandler.END
    action, slot1, slot2 = info
    data = load()
    msg = u.message
    if msg.text:
        data[slot1] = {"type": "text", "content": msg.text}
    elif msg.photo:
        data[slot1] = {"type": "photo", "file_id": msg.photo[-1].file_id, "caption": msg.caption or ""}
    elif msg.video:
        data[slot1] = {"type": "video", "file_id": msg.video.file_id, "caption": msg.caption or ""}
    elif msg.animation:
        data[slot1] = {"type": "animation", "file_id": msg.animation.file_id, "caption": msg.caption or ""}
    elif msg.document:
        data[slot1] = {"type": "document", "file_id": msg.document.file_id, "caption": msg.caption or ""}
    else:
        await u.message.reply_text("❌ Không hỗ trợ định dạng này!")
        return ConversationHandler.END
    save(data)
    await u.message.reply_text(f"✅ Đã lưu/cập nhật ô {slot1}!")
    if action == "doigui":
        item = data.get(slot2)
        if item:
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
                await u.message.reply_text(f"✅ Đã gửi ô {slot2} vào nhóm!")
            except Exception as e:
                await u.message.reply_text(f"❌ Lỗi gửi: {e}")
        else:
            await u.message.reply_text(f"❌ Ô {slot2} chưa có nội dung!")
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

def make_nap_handler(i):
    async def handler(u, c):
        return await nap_cmd(u, c)
    return handler

def make_doi_handler(i, with_gui=False, gui_slot=None):
    async def handler(u, c):
        return await doi_cmd(u, c)
    return handler

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))

    for i in range(1, 11):
        # /napX
        conv_nap = ConversationHandler(
            entry_points=[CommandHandler(f"nap{i}", nap_cmd)],
            states={WAITING: [MessageHandler(filters.ALL & ~filters.COMMAND, handle_content)]},
            fallbacks=[CommandHandler("cancel", cancel)],
        )
        app.add_handler(conv_nap)

        # /guiX
        app.add_handler(CommandHandler(f"gui{i}", gui_cmd))

        # /doiX
        conv_doi = ConversationHandler(
            entry_points=[CommandHandler(f"doi{i}", doi_cmd)],
            states={WAITING: [MessageHandler(filters.ALL & ~filters.COMMAND, handle_content)]},
            fallbacks=[CommandHandler("cancel", cancel)],
        )
        app.add_handler(conv_doi)

        # /doiXguiY
        for j in range(1, 11):
            conv_doigui = ConversationHandler(
                entry_points=[CommandHandler(f"doi{i}gui{j}", doi_cmd)],
                states={WAITING: [MessageHandler(filters.ALL & ~filters.COMMAND, handle_content)]},
                fallbacks=[CommandHandler("cancel", cancel)],
            )
            app.add_handler(conv_doigui)

    print("Bot chạy!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
