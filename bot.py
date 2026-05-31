import os
import json
import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

logging.basicConfig(level=logging.INFO)

# Thay TOKEN của bạn vào đây
TOKEN = os.environ.get("BOT_TOKEN", "8877176302:AAETTH8e3LWY0BL3pHsOpUo4huAQjzOq2bg")
DATA_FILE = "storage.json"

# DANH SÁCH 2 ID NHÓM CỦA BẠN (Ép bot luôn gửi vào đây)
LIST_GROUPS = [-1003617964607, -1002237072619] 

# MẬT KHẨU BẢO MẬT
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

# HÀM BẮN TIN NHẮN ĐỒNG THỜI - ÉP CHẾT ĐẦU RA VÀO 2 NHÓM
async def broadcast_to_all_groups(bot, action_type, **kwargs):
    for chat_id in LIST_GROUPS:
        try:
            # Xóa bỏ hoàn toàn việc lấy chat_id tự động của Telegram, ép dùng LIST_GROUPS
            if "chat_id" in kwargs:
                kwargs["chat_id"] = chat_id
            else:
                kwargs.update({"chat_id": chat_id})

            if action_type == "message":
                await bot.send_message(**kwargs)
            elif action_type == "photo":
                await bot.send_photo(**kwargs)
            elif action_type == "video":
                await bot.send_video(**kwargs)
            elif action_type == "animation":
                await bot.send_animation(**kwargs)
            elif action_type == "document":
                await bot.send_document(**kwargs)
        except Exception as e:
            logging.error(f"Lỗi bắn nhóm {chat_id}: {e}")

# Menu nút bấm điều khiển
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
    'CHUẨN BỊ': '/gui1', 'LÊN CA': '/gui2', 'BÁO BÀN': '/doi3', 'CHỜ LỆNH': '/gui4', 'BẮT ĐẦU': '/gui5',
    'CON 10%': '/gui6', 'CÁI 10%': '/gui7', 'XUỐNG CA': '/gui8', 'SỰ KIỆN': '/gui9', 'KHUYẾN MÃI': '/gui10',
    'GỬI TIN NHẮN NHANH': '/all',
    'ĐỔI CHUẨN BỊ': '/doi1', 'ĐỔI LÊN CA': '/doi2', 'ĐỔI CHỜ LỆNH': '/doi4', 'ĐỔI BẮT ĐẦU': '/doi5', 'ĐỔI CON 10%': '/doi6',
    'ĐỔI CÁI 10%': '/doi7', 'ĐỔI XUỐNG CA': '/doi8', 'ĐỔI SỰ KIỆN': '/doi9', 'ĐỔI KHUYẾN MÃI': '/doi10',
}

def check_auth(user_id):
    return user_id in authenticated_users

async def start(u: Update, c: ContextTypes.DEFAULT_TYPE):
    uid = u.effective_user.id
    
    # Mẹo nhỏ: Nếu bạn gõ /start ở trong nhóm, Bot sẽ log ra ID nhóm để bạn check lại
    if u.effective_chat.type in ["group", "supergroup"]:
        print(f"📌 ID Nhóm bạn vừa gõ /start là: {u.effective_chat.id}")
        
    if not check_auth(uid):
        pending[uid] = ("login", None, None)
        await u.message.reply_text("🔒 Nhập mật khẩu điều khiển:", reply_markup=ReplyKeyboardRemove())
        return WAITING_PASS
        
    await u.message.reply_text("👋 Hệ thống điều khiển đã sẵn sàng!", reply_markup=bieu_dien_menu())

async def handle_password(u: Update, c: ContextTypes.DEFAULT_TYPE):
    uid = u.effective_user.id
    if u.message.text == BOT_PASSWORD:
        authenticated_users.add(uid)
        pending.pop(uid, None)
        await u.message.reply_text("🎉 Đăng nhập thành công!", reply_markup=bieu_dien_menu())
        return ConversationHandler.END
    else:
        await u.message.reply_text("❌ Sai mật khẩu! Nhập lại:")
        return WAITING_PASS

async def nap_cmd(u: Update, c: ContextTypes.DEFAULT_TYPE):
    uid = u.effective_user.id
    if not check_auth(uid): return ConversationHandler.END
    slot = u.message.text.split()[0][1:].replace("nap", "")
    pending[uid] = ("nap", slot, None)
    await u.message.reply_text(f"📥 Gửi nội dung lưu cho ô {slot}:")
    return WAITING

async def doi_cmd(u: Update, c: ContextTypes.DEFAULT_TYPE):
    uid = u.effective_user.id
    if not check_auth(uid): return ConversationHandler.END
    cmd = u.message.text.split()[0][1:]
    if "gui" in cmd:
        parts = cmd.split("gui")
        pending[uid] = ("doigui", parts[0].replace("doi", ""), parts[1])
        await u.message.reply_text(f"🔄 Đổi nội dung ô {parts[0].replace('doi', '')} và tự gửi ô {parts[1]}:")
    else:
        pending[uid] = ("doi", cmd.replace("doi", ""), None)
        await u.message.reply_text(f"🔄 Gửi HÌNH ẢNH MỚI cho ô {cmd.replace('doi', '')}:")
    return WAITING

async def all_cmd(u: Update, c: ContextTypes.DEFAULT_TYPE):
    uid = u.effective_user.id
    if not check_auth(uid): return ConversationHandler.END
    pending[uid] = ("all", None, None)
    await u.message.reply_text("⚡ Gửi tin nhắn bất kỳ để bắn thẳng lên 2 nhóm:")
    return WAITING

# SỬA LẠI TOÀN BỘ LOGIC KHI ẤN NÚT TRÊN MENU CHAT RIÊNG
async def handle_button_text(u: Update, c: ContextTypes.DEFAULT_TYPE):
    uid = u.effective_user.id
    text = u.message.text
    if text not in BUTTON_MAP: return
    if not check_auth(uid): return

    cmd = BUTTON_MAP[text]
    if cmd == '/all':
        pending
