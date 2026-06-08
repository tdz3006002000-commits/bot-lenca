import os
import json
import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

logging.basicConfig(level=logging.INFO)

TOKEN = os.environ.get("BOT_TOKEN", "8877176302:AAETTH8e3LWY0BL3pHsOpUo4huAQjzOq2bg")
CHAT_LINK = "-1003617964607"
DATA_FILE = "storage.json"

# CẤU HÌNH MẬT KHẨU CHO BOT - ĐÃ ĐỔI THÀNH HARRY2005TDZ (VIẾT HOA TOÀN BỘ)
BOT_PASSWORD = os.environ.get("BOT_PASSWORD", "HARRY2005TDZ")

WAITING = 1
WAITING_PASS = 99  # Trạng thái chờ nhập mật khẩu
pending = {}
authenticated_users = set() # Lưu danh sách ID người dùng đã nhập đúng mật khẩu

def load():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE) as f:
            return json.load(f)
    return {}

def save(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

# Thanh menu thiết kế tinh gọn theo yêu cầu
def bieu_dien_menu():
    boc_cut_nut = [
        # Nhóm GỬI (trên) - /gui1, /gui2, /doi3(BÁO BÀN), /gui4, /gui5
        ['/gui1', '/gui2', '/doi3', '/gui4', '/gui5'],
        ['/gui6', '/gui7', '/gui8', '/gui9', '/gui10'],
        # Ngăn cách
        ['/all'],
        # Nhóm ĐỔI (dưới) - không có /doi3
        ['/doi1', '/doi2', '/doi4', '/doi5', '/doi6'],
        ['/doi7', '/doi8', '/doi9', '/doi10'],
    ]
    keyboard = [
        # Nhóm GỬI (trên)
        [
            {'text': 'CHUẨN BỊ', 'callback': '/gui1'},
            {'text': 'LÊN CA', 'callback': '/gui2'},
            {'text': 'BÁO BÀN', 'callback': '/doi3'},
            {'text': 'CHỜ LỆNH', 'callback': '/gui4'},
            {'text': 'BẮT ĐẦU', 'callback': '/gui5'},
        ],
        [
            {'text': 'CON 10%', 'callback': '/gui6'},
            {'text': 'CÁI 10%', 'callback': '/gui7'},
            {'text': 'XUỐNG CA', 'callback': '/gui8'},
            {'text': 'SỰ KIỆN', 'callback': '/gui9'},
            {'text': 'KHUYẾN MÃI', 'callback': '/gui10'},
        ],
        # Ngăn cách
        [
            {'text': 'GỬI TIN NHẮN NHANH', 'callback': '/all'},
        ],
        # Nhóm ĐỔI (dưới) - không có /doi3
        [
            {'text': 'ĐỔI CHUẨN BỊ', 'callback': '/doi1'},
            {'text': 'ĐỔI LÊN CA', 'callback': '/doi2'},
            {'text': 'ĐỔI CHỜ LỆNH', 'callback': '/doi4'},
            {'text': 'ĐỔI BẮT ĐẦU', 'callback': '/doi5'},
            {'text': 'ĐỔI CON 10%', 'callback': '/doi6'},
        ],
        [
            {'text': 'ĐỔI CÁI 10%', 'callback': '/doi7'},
            {'text': 'ĐỔI XUỐNG CA', 'callback': '/doi8'},
            {'text': 'ĐỔI SỰ KIỆN', 'callback': '/doi9'},
            {'text': 'ĐỔI KHUYẾN MÃI', 'callback': '/doi10'},
        ],
    ]
    # Chuyển sang dạng text button cho ReplyKeyboardMarkup
    reply_keyboard = [
        ['CHUẨN BỊ', 'LÊN CA', 'BÁO BÀN', 'CHỜ LỆNH', 'BẮT ĐẦU'],
        ['CON 10%', 'CÁI 10%', 'XUỐNG CA', 'SỰ KIỆN', 'KHUYẾN MÃI'],
        ['GỬI TIN NHẮN NHANH'],
        ['ĐỔI CHUẨN BỊ', 'ĐỔI LÊN CA', 'ĐỔI CHỜ LỆNH', 'ĐỔI BẮT ĐẦU', 'ĐỔI CON 10%'],
        ['ĐỔI CÁI 10%', 'ĐỔI XUỐNG CA', 'ĐỔI SỰ KIỆN', 'ĐỔI KHUYẾN MÃI'],
        # ===== 9 NÚT MỚI THÊM VÀO =====
        ['HÚP + 10%', 'GÃY - 10%', 'HÚP + 5%', 'GÃY - 5%', 'HÚP - 5%'],
        ['GÃY - 15%', 'GÃY + 5%', 'HÒA + 00'],
    ]
    return ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True, one_time_keyboard=False)

# Map tên nút bấm -> lệnh thực tế
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
    # ===== 9 NÚT MỚI THÊM VÀO =====
    'HÚP + 10%': '/doi11',
    'GÃY - 10%': '/doi12',
    'HÚP + 5%': '/doi13',
    'GÃY - 5%': '/doi14',
    'HÚP - 5%': '/doi15',
    'GÃY - 15%': '/doi16',
    'GÃY + 5%': '/doi17',
    'HÒA + 00': '/doi18',
}

# Hàm kiểm tra bảo mật (Nếu chưa xác thực sẽ bắt nhập mật khẩu)
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
        "📥 Lưu dữ liệu: Gõ tay lệnh /nap1 đến /nap10 (Chỉ làm 1 lần)\n"
        "📤 Gửi nhanh, đổi nội dung ảnh và gửi trực tiếp: Dùng thanh menu bên dưới.",
        reply_markup=bieu_dien_menu()
    )

# Hàm xử lý kiểm tra mật khẩu người dùng nhập vào
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
        await u.message.reply_text("🔒 Bạn cần gõ /start và nhập mật khẩu trước khi dùng lệnh!")
        return ConversationHandler.END
        
    cmd = u.message.text.split()[0][1:]
    slot = cmd.replace("nap", "")
    pending[uid] = ("nap", slot, None)
    await u.message.reply_text(f"📥 Gửi nội dung cho ô {slot}:")
    return WAITING

async def doi_cmd(u: Update, c: ContextTypes.DEFAULT_TYPE):
    uid = u.effective_user.id
    if not check_auth(uid):
        await u.message.reply_text("🔒 Bạn cần gõ /start và nhập mật khẩu trước khi dùng lệnh!")
        return ConversationHandler.END
        
    cmd = u.message.text.split()[0][1:]
    if "gui" in cmd:
        parts = cmd.split("gui")
        slot_doi = parts[0].replace("doi", "")
        slot_gui = parts[1]
        pending[uid] = ("doigui", slot_doi, slot_gui)
        await u.message.reply_text(f"🔄 Gửi nội dung mới cho ô {slot_doi} (sẽ gửi ô {slot_gui} lên nhóm):")
    else:
        slot = cmd.replace("doi", "")
        pending[uid] = ("doi", slot, None)
        await u.message.reply_text(f"🔄 Gửi HÌNH ẢNH MỚI cho ô {slot} (Bot sẽ giữ văn bản cũ và tự gửi lên nhóm):")
    return WAITING

# Xử lý chức năng gửi liền lập tức /all
async def all_cmd(u: Update, c: ContextTypes.DEFAULT_TYPE):
    uid = u.effective_user.id
    if not check_auth(uid):
        await u.message.reply_text("🔒 Bạn cần gõ /start và nhập mật khẩu trước khi dùng lệnh!")
        return ConversationHandler.END
        
    pending[uid] = ("all", None, None)
    await u.message.reply_text("⚡ Gửi tin nhắn bất kỳ (Chữ/Ảnh/Video), Bot sẽ bắn thẳng lên nhóm ngay lập tức:")
    return WAITING

# Xử lý nút bấm text (chuyển tên nút -> lệnh thực tế)
async def handle_button_text(u: Update, c: ContextTypes.DEFAULT_TYPE):
    uid = u.effective_user.id
    text = u.message.text

    if text not in BUTTON_MAP:
        return

    if not check_auth(uid):
        await u.message.reply_text("🔒 Bạn cần gõ /start và nhập mật khẩu trước khi dùng lệnh!")
        return

    cmd = BUTTON_MAP[text]

    if cmd == '/all':
        pending[uid] = ("all", None, None)
        await u.message.reply_text("⚡ Gửi tin nhắn bất kỳ (Chữ/Ảnh/Video), Bot sẽ bắn thẳng lên nhóm ngay lập tức:")
        return WAITING

    if cmd.startswith('/gui'):
        slot = cmd.replace('/gui', '')
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
        return

    if cmd.startswith('/doi'):
        slot = cmd.replace('/doi', '')
        pending[uid] = ("doi", slot, None)
        await u.message.reply_text(f"🔄 Gửi HÌNH ẢNH MỚI cho ô {slot} (Bot sẽ giữ văn bản cũ và tự gửi lên nhóm):")
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
            data[slot1] = {"type": "text", "content": msg.text_html}
        else:
            await u.message.reply_text("❌ Định dạng không hợp lệ cho lệnh đổi!", reply_markup=bieu_dien_menu())
            return ConversationHandler.END
            
        save(data)
        await u.message.reply_text(f"✅ Đã đổi ảnh và giữ nguyên văn bản cũ cho ô {slot1}!", reply_markup=bieu_dien_menu())
        
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
    uid = u.effective_user.id
    if not check_auth(uid):
        await u.message.reply_text("🔒 Bạn cần gõ /start và nhập mật khẩu trước khi dùng lệnh!")
        return
        
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
    
    # Quản lý luồng đăng nhập bằng mật khẩu khi gõ /start
    login_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={WAITING_PASS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_password)]},
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    app.add_handler(login_handler)

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

        # /guiX (bỏ gui3)
        if i != 3:
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

    # ===== ĐĂNG KÝ 8 NÚT MỚI /doi11 -> /doi18 =====
    for i in range(11, 19):
        conv_doi_new = ConversationHandler(
            entry_points=[CommandHandler(f"doi{i}", doi_cmd)],
            states={WAITING: [MessageHandler(filters.ALL & ~filters.COMMAND, handle_content)]},
            fallbacks=[CommandHandler("cancel", cancel)],
        )
        app.add_handler(conv_doi_new)

    # Xử lý nút bấm text từ keyboard
    conv_button = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & ~filters.COMMAND, handle_button_text)],
        states={WAITING: [MessageHandler(filters.ALL & ~filters.COMMAND, handle_content)]},
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(conv_button)

    print("Bot đang chạy ổn định với hệ thống khóa bảo mật!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
