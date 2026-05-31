import os
import json
import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

logging.basicConfig(level=logging.INFO)

TOKEN = os.environ.get("BOT_TOKEN", "8877176302:AAETTH8e3LWY0BL3pHsOpUo4huAQjzOq2bg")
DATA_FILE = "storage.json"

# DANH SÁCH 2 ID NHÓM CỐ ĐỊNH CỦA BẠN
LIST_GROUPS = [-1003617964607, -1002237072619] 

# MẬT KHẨU KHÓA HỆ THỐNG
BOT_PASSWORD = os.environ.get("BOT_PASSWORD", "HARRY2005TDZ")

WAITING = 1
WAITING_PASS = 99  
pending = {}
authenticated_users = set() 

def load():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE) as f:
            return json.load(f)
    return {}

def save(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

# Hàm gửi tin nhắn/phương tiện đến TẤT CẢ các nhóm trong danh sách
async def broadcast_to_all_groups(bot, action_type, **kwargs):
    for chat_id in LIST_GROUPS:
        try:
            if action_type == "message":
                await bot.send_message(chat_id=chat_id, **kwargs)
            elif action_type == "photo":
                await bot.send_photo(chat_id=chat_id, **kwargs)
            elif action_type == "video":
                await bot.send_video(chat_id=chat_id, **kwargs)
            elif action_type == "animation":
                await bot.send_animation(chat_id=chat_id, **kwargs)
            elif action_type == "document":
                await bot.send_document(chat_id=chat_id, **kwargs)
        except Exception as e:
            logging.error(f"Không thể gửi tin nhắn đến nhóm {chat_id}: {e}")

# Thanh menu điều khiển
def bieu_dien_menu():
    reply_keyboard = [
        ['CHUẨN BỊ', 'LÊN CA', 'BÁO BÀN', 'CHỜ LỆNH', 'BẮT ĐẦU'],
        ['CON 10%', 'CÁI 10%', 'XUỐNG CA', 'SỰ KIỆN', 'KHUYẾN MÃI'],
        ['GỬI TIN NHẮN NHANH'],
        ['ĐỔI CHUẨN BỊ', 'ĐỔI LÊN CA', 'ĐỔI CHỜ LỆNH', 'ĐỔI BẮT ĐẦU', 'ĐỔI CON 10%'],
        ['ĐỔI CÁI 10%', 'ĐỔI XUỐNG CA', 'ĐỔI SỰ KIỆN', 'ĐỔI KHUYẾN MÃI'],
    ]
    return ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True, one_time_keyboard=False)

BUTTON_MAP = {
    'CHUẨN BỊ': '/gui1',
    'LÊN CA': '/gui2',
    'BÁO BÀN': '/doi3',
    'CHỜ LỆNH': '/gui4',
    'BẮT ĐẦU': '/gui5',
    'CON 10%': '/gui6',
    'CÁI 10%': '/gui7',
    'XUỐNG CA': '/gui8',
    'SỰ KIỆN': '/gui9',
    'KHUYẾN MÃI': '/gui10',
    'GỬI TIN NHẮN NHANH': '/all',
    'ĐỔI CHUẨN BỊ': '/doi1',
    'ĐỔI LÊN CA': '/doi2',
    'ĐỔI CHỜ LỆNH': '/doi4',
    'ĐỔI BẮT ĐẦU': '/doi5',
    'ĐỔI CON 10%': '/doi6',
    'ĐỔI CÁI 10%': '/doi7',
    'ĐỔI XUỐNG CA': '/doi8',
    'ĐỔI SỰ KIỆN': '/doi9',
    'ĐỔI KHUYẾN MÃI': '/doi10',
}

def check_auth(user_id):
    return user_id in authenticated_users

async def start(u: Update, c: ContextTypes.DEFAULT_TYPE):
    uid = u.effective_user.id
    if not check_auth(uid):
        pending[uid] = ("login", None, None)
        await u.message.reply_text(
            "🔒 Bot này đã được bảo mật!\n"
            "Vui lòng nhập mật khẩu để mở khóa hệ thống:",
            reply_markup=ReplyKeyboardRemove()
        )
        return WAITING_PASS
        
    await u.message.reply_text(
        "👋 Hệ thống điều khiển BOT LENH VIP đã sẵn sàng!\n\n"
        "Bây giờ bạn có thể ra lệnh trực tiếp tại đây.",
        reply_markup=bieu_dien_menu()
    )

async def handle_password(u: Update, c: ContextTypes.DEFAULT_TYPE):
    uid = u.effective_user.id
    user_pass = u.message.text
    
    if user_pass == BOT_PASSWORD:
        authenticated_users.add(uid)
        pending.pop(uid, None)
        await u.message.reply_text(
            "🎉 Mật khẩu chính xác! Hệ thống đã được mở khóa.",
            reply_markup=bieu_dien_menu()
        )
        return ConversationHandler.END
    else:
        await u.message.reply_text("❌ Mật khẩu sai rồi! Vui lòng nhập lại mật khẩu:")
        return WAITING_PASS

async def nap_cmd(u: Update, c: ContextTypes.DEFAULT_TYPE):
    uid = u.effective_user.id
    if not check_auth(uid):
        await u.message.reply_text("🔒 Bạn cần gõ /start và nhập mật khẩu trước!")
        return ConversationHandler.END
        
    cmd = u.message.text.split()[0][1:]
    slot = cmd.replace("nap", "")
    pending[uid] = ("nap", slot, None)
    await u.message.reply_text(f"📥 Gửi nội dung cho ô {slot}:")
    return WAITING

async def doi_cmd(u: Update, c: ContextTypes.DEFAULT_TYPE):
    uid = u.effective_user.id
    if not check_auth(uid):
        await u.message.reply_text("🔒 Bạn cần gõ /start và nhập mật khẩu trước!")
        return ConversationHandler.END
        
    cmd = u.message.text.split()[0][1:]
    if "gui" in cmd:
        parts = cmd.split("gui")
        slot_doi = parts[0].replace("doi", "")
        slot_gui = parts[1]
        pending[uid] = ("doigui", slot_doi, slot_gui)
        await u.message.reply_text(f"🔄 Gửi nội dung mới cho ô {slot_doi} (sẽ gửi ô {slot_gui} lên tất cả các nhóm):")
    else:
        slot = cmd.replace("doi", "")
        pending[uid] = ("doi", slot, None)
        await u.message.reply_text(f"🔄 Gửi HÌNH ẢNH MỚI cho ô {slot}:")
    return WAITING

async def all_cmd(u: Update, c: ContextTypes.DEFAULT_TYPE):
    uid = u.effective_user.id
    if not check_auth(uid):
        await u.message.reply_text("🔒 Bạn cần gõ /start và nhập mật khẩu trước!")
        return ConversationHandler.END
        
    pending[uid] = ("all", None, None)
    await u.message.reply_text(f"⚡ Gửi tin nhắn bất kỳ, Bot sẽ bắn thẳng lên các nhóm ngay lập tức:")
    return WAITING

async def handle_button_text(u: Update, c: ContextTypes.DEFAULT_TYPE):
    uid = u.effective_user.id
    text = u.message.text

    if text not in BUTTON_MAP:
        return

    if not check_auth(uid):
        await u.message.reply_text("🔒 Tài khoản chưa mở khóa! Vui lòng gõ /start và nhập mật khẩu.")
        return

    cmd = BUTTON_MAP[text]

    if cmd == '/all':
        pending[uid] = ("all", None, None)
        await u.message.reply_text("⚡ Gửi tin nhắn bất kỳ, Bot sẽ bắn thẳng lên các nhóm ngay lập tức:")
        return WAITING

    if cmd.startswith('/gui'):
        slot = cmd.replace('/gui', '')
        data = load()
        item = data.get(slot)
        if not item:
            await u.message.reply_text(f"❌ Ô {slot} chưa có nội dung! Vui lòng dùng lệnh /nap{slot} trước.", reply_markup=bieu_dien_menu())
            return
        try:
            t = item["type"]
            if t == "text":
                await broadcast_to_all_groups(c.bot, "message", text=item["content"], parse_mode="HTML")
            elif t == "photo":
                await broadcast_to_all_groups(c.bot, "photo", photo=item["file_id"], caption=item["caption"], parse_mode="HTML")
            elif t == "video":
                await broadcast_to_all_groups(c.bot, "video", video=item["file_id"], caption=item["caption"], parse_mode="HTML")
            elif t == "animation":
                await broadcast_to_all_groups(c.bot, "animation", animation=item["file_id"], caption=item["caption"], parse_mode="HTML")
            elif t == "document":
                await broadcast_to_all_groups(c.bot, "document", document=item["file_id"], caption=item["caption"], parse_mode="HTML")
            await u.message.reply_text(f"✅ Đã gửi ô {slot} vào tất cả các nhóm!", reply_markup=bieu_dien_menu())
        except Exception as e:
            await u.message.reply_text(f"❌ Lỗi: {e}", reply_markup=bieu_dien_menu())
        return

    if cmd.startswith('/doi'):
        slot = cmd.replace('/doi', '')
        pending[uid] = ("doi", slot, None)
        await u.message.reply_text(f"🔄 Gửi HÌNH ẢNH MỚI cho ô {slot}:")
        return WAITING

async def handle_content(u: Update, c: ContextTypes.DEFAULT_TYPE):
    uid = u.effective_user.id
    info = pending.get(uid)
    if not info:
        return ConversationHandler.END
        
    action, slot1, slot2 = info
    msg = u.message
    
    if action == "all":
        try:
            if msg.text:
                await broadcast_to_all_groups(c.bot, "message", text=msg.text_html, parse_mode="HTML")
            elif msg.photo:
                await broadcast_to_all_groups(c.bot, "photo", photo=msg.photo[-1].file_id, caption=msg.caption_html or "", parse_mode="HTML")
            elif msg.video:
                await broadcast_to_all_groups(c.bot, "video", video=msg.video.file_id, caption=msg.caption_html or "", parse_mode="HTML")
            elif msg.animation:
                await broadcast_to_all_groups(c.bot, "animation", animation=msg.animation.file_id, caption=msg.caption_html or "", parse_mode="HTML")
            elif msg.document:
                await broadcast_to_all_groups(c.bot, "document", document=msg.document.file_id, caption=msg.caption_html or "", parse_mode="HTML")
            await u.message.reply_text("✅ Đã bắn thẳng nội dung lên tất cả các nhóm!", reply_markup=bieu_dien_menu())
        except Exception as e:
            await u.message.reply_text(f"❌ Lỗi gửi: {e}", reply_markup=bieu_dien_menu())
        pending.pop(uid, None)
        return ConversationHandler.END

    data = load()
    
    if action == "doi":
        item_cu = data.get(slot1)
        van_ban_cu = ""
        if item_cu:
            van_ban_cu = item_cu.get("content", "") if item_cu["type"] == "text" else item_cu.get("caption", "")
                
        if msg.photo:
            data[slot1] = {"type": "photo", "file_id": msg.photo[-1].file_id, "caption": van_ban_cu}
        elif msg.video:
            data[slot1] = {"type": "video", "file_id": msg.video.file_id, "caption": van_ban_cu}
        elif msg.animation:
            data[slot1] = {"type": "animation", "file_id": msg.animation.file_id, "caption": van_ban_cu}
        elif msg.document:
            data[slot1] = {"type": "document", "file_id": msg.document.file_id, "caption": van_ban_cu}
        elif msg.text:
            data[slot1] = {"type": "text", "content": msg.text_html}
            
        save(data)
        await u.message.reply_text(f"✅ Đã đổi dữ liệu ô {slot1}!", reply_markup=bieu_dien_menu())
        
        try:
            item = data[slot1]
            t = item["type"]
            if t == "text":
                await broadcast_to_all_groups(c.bot, "message", text=item["content"], parse_mode="HTML")
            elif t == "photo":
                await broadcast_to_all_groups(c.bot, "photo", photo=item["file_id"], caption=item["caption"], parse_mode="HTML")
            elif t == "video":
                await broadcast_to_all_groups(c.bot, "video", video=item["file_id"], caption=item["caption"], parse_mode="HTML")
            elif t == "animation":
                await broadcast_to_all_groups(c.bot, "animation", animation=item["file_id"], caption=item["caption"], parse_mode="HTML")
            elif t == "document":
                await broadcast_to_all_groups(c.bot, "document", document=item["file_id"], caption=item["caption"], parse_mode="HTML")
            await u.message.reply_text(f"🚀 Tự động gửi ô {slot1} lên tất cả các nhóm thành công!", reply_markup=bieu_dien_menu())
        except Exception as e:
            await u.message.reply_text(f"❌ Lỗi gửi nhóm: {e}", reply_markup=bieu_dien_menu())
            
        pending.pop(uid, None)
        return ConversationHandler.END

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
        
    save(data)
    await u.message.reply_text(f"✅ Đã lưu dữ liệu ô {slot1}!", reply_markup=bieu_dien_menu())
    
    if action == "doigui":
        item = data.get(slot2)
        if item:
            try:
                t = item["type"]
                if t == "text":
                    await broadcast_to_all_groups(c.bot, "message", text=item["content"], parse_mode="HTML")
                elif t == "photo":
                    await broadcast_to_all_groups(c.bot, "photo", photo=item["file_id"], caption=item["caption"], parse_mode="HTML")
                elif t == "video":
                    await broadcast_to_all_groups(c.bot, "video", video=item["file_id"], caption=item["caption"], parse_mode="HTML")
                elif t == "animation":
                    await broadcast_to_all_groups(c.bot, "animation", animation=item["file_id"], caption=item["caption"], parse_mode="HTML")
                elif t == "document":
                    await broadcast_to_all_groups(c.bot, "document", document=item["file_id"], caption=item["caption"], parse_mode="HTML")
                await u.message.reply_text(f"✅ Đã gửi ô {slot2} vào tất cả các nhóm!", reply_markup=bieu_dien_menu())
            except Exception as e:
                await u.message.reply_text(f"❌ Lỗi gửi: {e}", reply_markup=bieu_dien_menu())
            
    pending.pop(uid, None)
    return ConversationHandler.END

async def cancel(u: Update, c: ContextTypes.DEFAULT_TYPE):
    pending.pop(u.effective_user.id, None)
    await u.message.reply_text("❌ Đã hủy lệnh hiện tại!", reply_markup=bieu_dien_menu())
    return ConversationHandler.END

def main():
    app = Application.builder().token(TOKEN).build()
    
    login_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={WAITING_PASS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_password)]},
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    app.add_handler(login_handler)

    conv_all = ConversationHandler(
        entry_points=[CommandHandler("all", all_cmd)],
        states={WAITING: [MessageHandler(filters.ALL & ~filters.COMMAND, handle_content)]},
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    app.add_handler(conv_all)

    for i in range(1, 11):
        conv_nap = ConversationHandler(
            entry_points=[CommandHandler(f"nap{i}", nap_cmd)],
            states={WAITING: [MessageHandler(filters.ALL & ~filters.COMMAND, handle_content)]},
            fallbacks=[CommandHandler("cancel", cancel)],
        )
        app.add_handler(conv_nap)

        conv_doi = ConversationHandler(
            entry_points=[CommandHandler(f"doi{i}", doi_cmd)],
            states={WAITING: [MessageHandler(filters.ALL & ~filters.COMMAND, handle_content)]},
            fallbacks=[CommandHandler("cancel", cancel)],
        )
        app.add_handler(conv_doi)

        for j in range(1, 11):
            conv_doigui = ConversationHandler(
                entry_points=[CommandHandler(f"doi{i}gui{j}", doi_cmd)],
                states={WAITING: [MessageHandler(filters.ALL & ~filters.COMMAND, handle_content)]},
                fallbacks=[CommandHandler("cancel", cancel)],
            )
            app.add_handler(conv_doigui)

    conv_button = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & ~filters.COMMAND, handle_button_text)],
        states={WAITING: [MessageHandler(filters.ALL & ~filters.COMMAND, handle_content)]},
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(conv_button)

    print("Bot đang chạy ổn định...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
