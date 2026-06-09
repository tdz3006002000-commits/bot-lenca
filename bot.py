import os
import json
import logging
import base64
import requests
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

logging.basicConfig(level=logging.INFO)

TOKEN = os.environ.get("BOT_TOKEN", "8877176302:AAETTH8e3LWY0BL3pHsOpUo4huAQjzOq2bg")
CHAT_LINK = "-1003617964607"

BOT_PASSWORD = os.environ.get("BOT_PASSWORD", "HARRY2005TDZ")

# ===== PERSISTENT STORAGE QUA RAILWAY API =====
RAILWAY_API_TOKEN = os.environ.get("RAILWAY_API_TOKEN", "")
RAILWAY_SERVICE_ID = os.environ.get("RAILWAY_SERVICE_ID", "13ebf69b-680a-44d2-a905-ce4ef7803993")
RAILWAY_ENVIRONMENT_ID = os.environ.get("RAILWAY_ENVIRONMENT_ID", "33dea9d1-8da0-40b1-9569-dc64580a4f0d")

def load():
    raw = os.environ.get("BOT_DATA", "")
    if raw:
        try:
            decoded = base64.b64decode(raw).decode("utf-8")
            return json.loads(decoded)
        except Exception as e:
            logging.warning(f"Khong doc duoc BOT_DATA: {e}")
    return {}

def save(data):
    try:
        encoded = base64.b64encode(json.dumps(data, ensure_ascii=False).encode("utf-8")).decode("utf-8")
        os.environ["BOT_DATA"] = encoded
        if RAILWAY_API_TOKEN:
            _save_to_railway(encoded)
        else:
            logging.warning("RAILWAY_API_TOKEN chua duoc cau hinh!")
    except Exception as e:
        logging.error(f"Loi khi luu data: {e}")

def _save_to_railway(encoded_value):
    try:
        mutation = "mutation variableUpsert($input: VariableUpsertInput!) { variableUpsert(input: $input) }"
        variables = {
            "input": {
                "serviceId": RAILWAY_SERVICE_ID,
                "environmentId": RAILWAY_ENVIRONMENT_ID,
                "name": "BOT_DATA",
                "value": encoded_value
            }
        }
        resp = requests.post(
            "https://backboard.railway.com/graphql/v2",
            json={"query": mutation, "variables": variables},
            headers={"Authorization": f"Bearer {RAILWAY_API_TOKEN}", "Content-Type": "application/json"},
            timeout=10
        )
        if resp.status_code == 200:
            logging.info("Da luu data len Railway!")
        else:
            logging.error(f"Railway API loi: {resp.status_code}")
    except Exception as e:
        logging.error(f"Loi Railway API: {e}")

WAITING = 1
WAITING_PASS = 99
pending = {}

def load_auth():
    data = load()
    return set(data.get("_auth", []))

authenticated_users = load_auth()

def save_auth():
    data = load()
    data["_auth"] = list(authenticated_users)
    save(data)

def bieu_dien_menu():
    reply_keyboard = [
        ['CHUAN BI', 'LEN CA', 'BAO BAN', 'CHO LENH', 'BAT DAU'],
        ['CON 10%', 'CAI 10%', 'HUP + 10%', 'GAY - 10%', 'HUP + 5%'],
        ['GAY - 5%', 'HUP - 5%', 'GAY - 15%', 'GAY + 5%', 'HOA + 00'],
        ['XUONG CA', 'SU KIEN', 'KHUYEN MAI'],
        ['GUI TIN NHAN NHANH'],
        ['DOI CHUAN BI', 'DOI LEN CA', 'DOI CHO LENH', 'DOI BAT DAU', 'DOI CON 10%'],
        ['DOI CAI 10%', 'DOI XUONG CA', 'DOI SU KIEN', 'DOI KHUYEN MAI'],
    ]
    return ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True, one_time_keyboard=False)

BUTTON_MAP = {
    'CHUAN BI': '/gui1', 'LEN CA': '/gui2', 'BAO BAN': '/doi3',
    'CHO LENH': '/gui4', 'BAT DAU': '/gui5', 'CON 10%': '/gui6',
    'CAI 10%': '/gui7', 'XUONG CA': '/gui8', 'SU KIEN': '/gui9',
    'KHUYEN MAI': '/gui10', 'HUP + 10%': '/doi11', 'GAY - 10%': '/doi12',
    'HUP + 5%': '/doi13', 'GAY - 5%': '/doi14', 'HUP - 5%': '/doi15',
    'GAY - 15%': '/doi16', 'GAY + 5%': '/doi17', 'HOA + 00': '/doi18',
    'GUI TIN NHAN NHANH': '/all', 'DOI CHUAN BI': '/doi1', 'DOI LEN CA': '/doi2',
    'DOI CHO LENH': '/doi4', 'DOI BAT DAU': '/doi5', 'DOI CON 10%': '/doi6',
    'DOI CAI 10%': '/doi7', 'DOI XUONG CA': '/doi8', 'DOI SU KIEN': '/doi9',
    'DOI KHUYEN MAI': '/doi10',
}

def check_auth(user_id):
    return user_id in authenticated_users

async def start(u: Update, c: ContextTypes.DEFAULT_TYPE):
    uid = u.effective_user.id
    if not check_auth(uid):
        pending[uid] = ("login", None, None)
        await u.message.reply_text("Bot nay da bao mat! Nhap mat khau:", reply_markup=ReplyKeyboardRemove())
        return WAITING_PASS
    await u.message.reply_text("He thong BOT LENH VIP san sang!\n/nap1 den /nap10 de nap lenh.", reply_markup=bieu_dien_menu())
    return ConversationHandler.END

async def handle_password(u: Update, c: ContextTypes.DEFAULT_TYPE):
    uid = u.effective_user.id
    if u.message.text == BOT_PASSWORD:
        authenticated_users.add(uid)
        save_auth()
        await u.message.reply_text("Mat khau dung! Chao mung!", reply_markup=bieu_dien_menu())
        return ConversationHandler.END
    await u.message.reply_text("Mat khau sai! Thu lai:")
    return WAITING_PASS

async def cancel(u: Update, c: ContextTypes.DEFAULT_TYPE):
    await u.message.reply_text("Da huy.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

async def nap_cmd(u: Update, c: ContextTypes.DEFAULT_TYPE):
    uid = u.effective_user.id
    if not check_auth(uid):
        await u.message.reply_text("Chua xac thuc! Go /start.")
        return ConversationHandler.END
    n = int(u.message.text.replace("/nap", ""))
    pending[uid] = ("nap", n, None)
    await u.message.reply_text(f"Nhap noi dung lenh {n}:\n/cancel de huy.", reply_markup=ReplyKeyboardRemove())
    return WAITING

async def nap_receive(u: Update, c: ContextTypes.DEFAULT_TYPE):
    uid = u.effective_user.id
    if uid not in pending or pending[uid][0] != "nap":
        return ConversationHandler.END
    n = pending[uid][1]
    data = load()
    if u.message.photo:
        data[f"key{n}"] = {"type": "photo", "file_id": u.message.photo[-1].file_id, "caption": u.message.caption or ""}
    else:
        data[f"key{n}"] = {"type": "text", "text": u.message.text or ""}
    save(data)
    await u.message.reply_text(f"Da luu lenh {n}!", reply_markup=bieu_dien_menu())
    del pending[uid]
    return ConversationHandler.END

async def gui_cmd(u: Update, c: ContextTypes.DEFAULT_TYPE):
    uid = u.effective_user.id
    if not check_auth(uid):
        await u.message.reply_text("Chua xac thuc!")
        return
    n = int(u.message.text.replace("/gui", ""))
    data = load()
    key = f"key{n}"
    if key not in data:
        await u.message.reply_text(f"Lenh {n} chua nap! Dung /nap{n}.")
        return
    item = data[key]
    try:
        if item["type"] == "photo":
            await c.bot.send_photo(chat_id=CHAT_LINK, photo=item["file_id"], caption=item.get("caption", ""))
        else:
            await c.bot.send_message(chat_id=CHAT_LINK, text=item["text"])
        await u.message.reply_text(f"Da gui lenh {n}!", reply_markup=bieu_dien_menu())
    except Exception as e:
        await u.message.reply_text(f"Loi gui lenh {n}: {e}")

async def doi_cmd(u: Update, c: ContextTypes.DEFAULT_TYPE):
    uid = u.effective_user.id
    if not check_auth(uid):
        await u.message.reply_text("Chua xac thuc!")
        return ConversationHandler.END
    n = int(u.message.text.replace("/doi", ""))
    data = load()
    key = f"key{n}"
    if key not in data:
        await u.message.reply_text(f"Lenh {n} chua nap!")
        return ConversationHandler.END
    pending[uid] = ("doi", n, None)
    await u.message.reply_text(f"Doi noi dung lenh {n}. Nhap moi:\n/cancel de huy.", reply_markup=ReplyKeyboardRemove())
    return WAITING

async def doi_receive(u: Update, c: ContextTypes.DEFAULT_TYPE):
    uid = u.effective_user.id
    if uid not in pending or pending[uid][0] != "doi":
        return ConversationHandler.END
    n = pending[uid][1]
    data = load()
    key = f"key{n}"
    if u.message.photo:
        data[key] = {"type": "photo", "file_id": u.message.photo[-1].file_id, "caption": u.message.caption or ""}
    else:
        old = data.get(key, {})
        if old.get("type") == "photo":
            data[key]["caption"] = u.message.text or ""
        else:
            data[key] = {"type": "text", "text": u.message.text or ""}
    save(data)
    await u.message.reply_text(f"Da doi lenh {n}!", reply_markup=bieu_dien_menu())
    del pending[uid]
    return ConversationHandler.END

async def all_cmd(u: Update, c: ContextTypes.DEFAULT_TYPE):
    uid = u.effective_user.id
    if not check_auth(uid):
        await u.message.reply_text("Chua xac thuc!")
        return ConversationHandler.END
    pending[uid] = ("all", None, None)
    await u.message.reply_text("Nhap tin nhan hoac anh:\n/cancel de huy.", reply_markup=ReplyKeyboardRemove())
    return WAITING

async def all_receive(u: Update, c: ContextTypes.DEFAULT_TYPE):
    uid = u.effective_user.id
    if uid not in pending or pending[uid][0] != "all":
        return ConversationHandler.END
    try:
        if u.message.photo:
            await c.bot.send_photo(chat_id=CHAT_LINK, photo=u.message.photo[-1].file_id, caption=u.message.caption or "")
        else:
            await c.bot.send_message(chat_id=CHAT_LINK, text=u.message.text or "")
        await u.message.reply_text("Da gui tin nhan!", reply_markup=bieu_dien_menu())
    except Exception as e:
        await u.message.reply_text(f"Loi: {e}")
    del pending[uid]
    return ConversationHandler.END

async def button_handler(u: Update, c: ContextTypes.DEFAULT_TYPE):
    uid = u.effective_user.id
    if not check_auth(uid):
        await u.message.reply_text("Chua xac thuc!")
        return ConversationHandler.END
    text = u.message.text
    if text not in BUTTON_MAP:
        return ConversationHandler.END
    cmd = BUTTON_MAP[text]
    u.message.text = cmd
    if cmd.startswith("/gui"):
        await gui_cmd(u, c)
    elif cmd.startswith("/doi"):
        n = int(cmd.replace("/doi", ""))
        data = load()
        key = f"key{n}"
        if key not in data:
            await u.message.reply_text(f"Lenh {n} chua nap!", reply_markup=bieu_dien_menu())
            return ConversationHandler.END
        pending[uid] = ("doi", n, None)
        await u.message.reply_text(f"Doi lenh {n}. Nhap moi:\n/cancel de huy.", reply_markup=ReplyKeyboardRemove())
        return WAITING
    elif cmd == "/all":
        pending[uid] = ("all", None, None)
        await u.message.reply_text("Nhap tin nhan:\n/cancel de huy.", reply_markup=ReplyKeyboardRemove())
        return WAITING
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
        states={WAITING: [MessageHandler(filters.ALL & ~filters.COMMAND, all_receive)]},
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    app.add_handler(conv_all)
    for i in range(1, 11):
        conv_nap = ConversationHandler(
            entry_points=[CommandHandler(f"nap{i}", nap_cmd)],
            states={WAITING: [MessageHandler(filters.ALL & ~filters.COMMAND, nap_receive)]},
            fallbacks=[CommandHandler("cancel", cancel)],
        )
        app.add_handler(conv_nap)
        if i != 3:
            app.add_handler(CommandHandler(f"gui{i}", gui_cmd))
        conv_doi = ConversationHandler(
            entry_points=[CommandHandler(f"doi{i}", doi_cmd)],
            states={WAITING: [MessageHandler(filters.ALL & ~filters.COMMAND, doi_receive)]},
            fallbacks=[CommandHandler("cancel", cancel)],
        )
        app.add_handler(conv_doi)
    for i in range(11, 19):
        conv_doi_new = ConversationHandler(
            entry_points=[CommandHandler(f"doi{i}", doi_cmd)],
            states={WAITING: [MessageHandler(filters.ALL & ~filters.COMMAND, doi_receive)]},
            fallbacks=[CommandHandler("cancel", cancel)],
        )
        app.add_handler(conv_doi_new)
    conv_button = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & ~filters.COMMAND, button_handler)],
        states={WAITING: [MessageHandler(filters.ALL & ~filters.COMMAND, doi_receive)]},
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(conv_button)
    print("Bot dang chay voi he thong luu tru persistent!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
