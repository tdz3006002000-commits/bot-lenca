import os
import json
import logging
from telegram import Update, ReplyKeyboardMarkup
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

# Thanh menu thiết kế tinh gọn theo yêu cầu (Không chứa /nap, có thêm /all)
def bieu_dien_menu():
    boc_cut_nut = [
        ['/gui1', '/gui2', '/gui3', '/gui4', '/gui5'],
        ['/gui6', '/gui7', '/gui8', '/gui9', '/gui10'],
        ['/doi1', '/doi2', '/doi3', '/doi4', '/doi5'],
        ['/doi6', '/doi7', '/doi8', '/doi9', '/doi10'],
        ['/all']
    ]
    return ReplyKeyboardMarkup(boc_cut_nut, resize_keyboard=True, one_time_keyboard=False)

async def start(u: Update, c: ContextTypes.DEFAULT_TYPE):
    await u.message.reply_text(
        "👋 Hệ thống điều khiển BOT LENH VIP đã sẵn sàng!\n\n"
        "📥 Lưu dữ liệu: Gõ tay lệnh /nap1 đến /nap10 (Chỉ làm 1 lần)\n"
        "📤 Gửi nhanh, đổi nội dung ảnh và gửi trực tiếp: Dùng thanh menu bên dưới.",
        reply_markup=bieu_dien_menu()
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
        await u.message.reply_text(f"🔄 Gửi HÌNH ẢNH MỚI cho ô {slot} (Bot sẽ giữ văn bản cũ và tự gửi lên nhóm):")
    return WAITING

# Xử lý chức năng gửi liền lập tức /all
async def all_cmd(u: Update, c: ContextTypes.DEFAULT_TYPE):
    pending[u.effective_user.id] = ("all", None, None)
    await u.message.reply_text("⚡ Gửi tin nhắn bất kỳ (Chữ/Ảnh/Video), Bot sẽ bắn thẳng lên nhóm ngay lập tức:")
    return WAITING

async def handle_content(u: Update, c: ContextTypes.DEFAULT_TYPE):
    uid = u.effective_user.id
    info = pending.get(uid)
    if not info:
        return ConversationHandler.END
        
    action, slot1, slot2 = info
    msg = u.message
    
    # Trường hợp 1: Thao tác gửi thẳng luôn của lệnh /all
    if action == "all":
        try:
            if msg.text:
                await c.bot.send_message(CHAT_LINK, msg.text_html, parse_mode="HTML")
            elif msg.photo:
                await c.bot.send_photo(CHAT_LINK, msg.photo[-1].file_id, caption=msg.caption_html or "", parse_mode="HTML")
            elif msg.video:
                await c.bot.send_video(CHAT_LINK, msg.video.file_id, caption=msg.caption_html or "", parse_mode="HTML")
            elif msg.animation:
                await c.bot.send_animation(CHAT_LINK, msg.animation.file_id, caption=msg.caption_html or "", parse_mode="HTML")
            elif msg.document:
                await c.bot.send_document(CHAT_LINK, msg.document.file_id, caption=msg.caption_html or "", parse_mode="HTML")
            else:
                await u.message.reply_text("❌ Không hỗ trợ định dạng này!", reply_markup=bieu_dien_menu())
                return ConversationHandler.END
            await u.message.reply_text("✅ Đã bắn thẳng nội dung lên nhóm thành công!", reply_markup=bieu_dien_menu())
        except Exception as e:
            await u.message.reply_text(f"❌ Lỗi gửi thẳng: {e}", reply_markup=bieu_dien_menu())
        pending.pop(uid, None)
        return ConversationHandler.END

    data = load()
    
    # Trường hợp 2: Logic chỉnh sửa lệnh /doiX (Thay đổi ảnh mới nhưng giữ nguyên văn bản cũ)
    if action == "doi":
        item_cu = data.get(slot1)
        van_ban_cu = ""
        
        # Trích xuất văn bản cũ đang có trong bộ nhớ của ô này
        if item_cu:
            if item_cu["type"] == "text":
                van_ban_cu = item_cu["content"]
            else:
                van_ban_cu = item_cu.get("caption", "")
                
        if msg.photo:
            data[slot1] = {"type": "photo", "file_id": msg.photo[-1].file_id, "caption": van_ban_cu}
        elif msg.video:
            data[slot1] = {"type": "video", "file_id": msg.video.file_id, "caption": van_ban_cu}
        elif msg.animation:
            data[slot1] = {"type": "animation", "file_id": msg.animation.file_id, "caption": van_ban_cu}
        elif msg.document:
            data[slot1] = {"type": "document", "file_id": msg.document.file_id, "caption": van_ban_cu}
        elif msg.text:
            # Nếu user cố tình gửi chữ, hệ thống hiểu là đè văn bản mới hoàn toàn vào text cũ
            data[slot1] = {"type": "text", "content": msg.text_html}
        else:
            await u.message.reply_text("❌ Định dạng không hợp lệ cho lệnh đổi!", reply_markup=bieu_dien_menu())
            return ConversationHandler.END
            
        save(data)
        await u.message.reply_text(f"✅ Đã đổi ảnh và giữ nguyên văn bản cũ cho ô {slot1}!", reply_markup=bieu_dien_menu())
        
        # Bắt buộc tự động gửi ngay lập tức lên nhóm sau khi đổi thành công
        try:
            item = data[slot1]
            t = item["type"]
            if t == "text":
                await c.bot.send_message(CHAT_LINK, item["content"], parse_mode="HTML")
            elif t == "photo":
                await c.bot.send_photo(CHAT_LINK, item["file_id"], caption=item["caption"], parse_mode="HTML")
            elif t == "video":
                await c.bot.send_video(CHAT_LINK, item["file_id"], caption=item["caption"], parse_mode="HTML")
            elif t == "animation":
                await c.bot.send_animation(CHAT_LINK, item["file_id"], caption=item["caption"], parse_mode="HTML")
            elif t == "document":
                await c.bot.send_document(CHAT_LINK, item["file_id"], caption=item["caption"], parse_mode="HTML")
            await u.message.reply_text(f"🚀 Tự động gửi ô {slot1} kèm ảnh mới lên nhóm thành công!", reply_markup=bieu_dien_menu())
        except Exception as e:
            await u.message.reply_text(f"❌ Lỗi tự động gửi lên nhóm: {e}", reply_markup=bieu_dien_menu())
            
        pending.pop(uid, None)
        return ConversationHandler.END

    # Trường hợp 3: Chạy lệnh nạp thủ công /napX ban đầu
    if msg.text:
        data[slot1] = {"type": "text", "content": msg.text_html}
    elif msg.photo:
        data[slot1] = {"type": "photo", "file_id": msg.photo[-1].file_id, "caption": msg.caption_html or ""}
    elif msg.video:
        data[slot1] = {"type": "video", "file_id": msg.video.file_id, "caption": msg.caption_html or ""}
    elif msg.animation:
        data[slot1] = {"type": "animation", "file_id": msg.animation.file_id, "caption": msg.caption_html or ""}
    elif msg.document:
        data[slot1] = {"type": "document", "file_id": msg.document.file_id, "caption": msg.caption_html or ""}
    else:
        await u.message.reply_text("❌ Không hỗ trợ định dạng này!", reply_markup=bieu_dien_menu())
        return ConversationHandler.END
        
    save(data)
    await u.message.reply_text(f"✅ Đã lưu/cập nhật dữ liệu ô {slot1}!", reply_markup=bieu_dien_menu())
    
    if action == "doigui":
        item = data.get(slot2)
        if item:
            try:
                t = item["type"]
                if t == "text":
                    await c.bot.send_message(CHAT_LINK, item["content"], parse_mode="HTML")
                elif t == "photo":
                    await c.bot.send_photo(CHAT_LINK, item["file_id"], caption=item["caption"], parse_mode="HTML")
                elif t == "video":
                    await c.bot.send_video(CHAT_LINK, item["file_id"], caption=item["caption"], parse_mode="HTML")
                elif t == "animation":
                    await c.bot.send_animation(CHAT_LINK, item["file_id"], caption=item["caption"], parse_mode="HTML")
                elif t == "document":
                    await c.bot.send_document(CHAT_LINK, item["file_id"], caption=item["caption"], parse_mode="HTML")
                await u.message.reply_text(f"✅ Đã gửi ô {slot2} vào nhóm!", reply_markup=bieu_dien_menu())
            except Exception as e:
                await u.message.reply_text(f"❌ Lỗi gửi: {e}", reply_markup=bieu_dien_menu())
        else:
            await u.message.reply_text(f"❌ Ô {slot2} chưa có nội dung!", reply_markup=bieu_dien_menu())
            
    pending.pop(uid, None)
    return ConversationHandler.END

async def gui_cmd(u: Update, c: ContextTypes.DEFAULT_TYPE):
    cmd = u.message.text.split()[0][1:]
    slot = cmd.replace("gui", "")
    data = load()
    item = data.get(slot)
    if not item:
        await u.message.reply_text(f"❌ Ô {slot} chưa có nội dung!", reply_markup=bieu_dien_menu())
        return
    try:
        t = item["type"]
        if t == "text":
            await c.bot.send_message(CHAT_LINK, item["content"], parse_mode="HTML")
        elif t == "photo":
            await c.bot.send_photo(CHAT_LINK, item["file_id"], caption=item["caption"], parse_mode="HTML")
        elif t == "video":
            await c.bot.send_video(CHAT_LINK, item["file_id"], caption=item["caption"], parse_mode="HTML")
        elif t == "animation":
            await c.bot.send_animation(CHAT_LINK, item["file_id"], caption=item["caption"], parse_mode="HTML")
        elif t == "document":
            await c.bot.send_document(CHAT_LINK, item["file_id"], caption=item["caption"], parse_mode="HTML")
        await u.message.reply_text(f"✅ Đã gửi ô {slot} vào nhóm!", reply_markup=bieu_dien_menu())
    except Exception as e:
        await u.message.reply_text(f"❌ Lỗi: {e}", reply_markup=bieu_dien_menu())

async def cancel(u: Update, c: ContextTypes.DEFAULT_TYPE):
    pending.pop(u.effective_user.id, None)
    await u.message.reply_text("❌ Đã hủy lệnh hiện tại!", reply_markup=bieu_dien_menu())
    return ConversationHandler.END

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))

    # Đăng ký xử lý lệnh gửi trực tiếp /all độc lập trong menu
    conv_all = ConversationHandler(
        entry_points=[CommandHandler("all", all_cmd)],
        states={WAITING: [MessageHandler(filters.ALL & ~filters.COMMAND, handle_content)]},
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    app.add_handler(conv_all)

    for i in range(1, 11):
        # /napX (Lệnh gõ tay)
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

    print("Bot đang chạy ổn định với các nâng cấp mới!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
