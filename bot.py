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
RAILWAY_API_TOKEN = os.environ.get("RAILWAY_API_TOKEN", "")
RAILWAY_SERVICE_ID = os.environ.get("RAILWAY_SERVICE_ID", "13ebf69b-680a-44d2-a905-ce4ef7803993")
RAILWAY_ENVIRONMENT_ID = os.environ.get("RAILWAY_ENVIRONMENT_ID", "33dea9d1-8da0-40b1-9569-dc64580a4f0d")

def load():
    raw = os.environ.get("BOT_DATA", "")
    if raw:
        try:
            return json.loads(base64.b64decode(raw).decode("utf-8"))
        except:
            pass
    return {}

def save(data):
    try:
        encoded = base64.b64encode(json.dumps(data, ensure_ascii=False).encode()).decode()
        os.environ["BOT_DATA"] = encoded
        if RAILWAY_API_TOKEN:
            try:
                mut = "mutation variableUpsert($input: VariableUpsertInput!) { variableUpsert(input: $input) }"
                requests.post(
                    "https://backboard.railway.com/graphql/v2",
                    json={"query": mut, "variables": {"input": {
                        "serviceId": RAILWAY_SERVICE_ID,
                        "environmentId": RAILWAY_ENVIRONMENT_ID,
                        "name": "BOT_DATA", "value": encoded}}},
                    headers={"Authorization": f"Bearer {RAILWAY_API_TOKEN}", "Content-Type": "application/json"},
                    timeout=10)
            except Exception as e:
                logging.error(f"Railway API loi: {e}")
    except Exception as e:
        logging.error(f"Loi save: {e}")

WAITING = 1
WAITING_PASS = 99
pending = {}

def load_auth():
    return set(load().get("_auth", []))

authenticated_users = load_auth()

def save_auth():
    data = load()
    data["_auth"] = list(authenticated_users)
    save(data)

def bieu_dien_menu():
    return ReplyKeyboardMarkup([
        ['CHUAN BI', 'LEN CA', 'BAO BAN', 'CHO LENH', 'BAT DAU'],
        ['CON 10%', 'CAI 10%', 'HUP + 10%', 'GAY - 10%', 'HUP + 5%'],
        ['GAY - 5%', 'HUP - 5%', 'GAY - 15%', 'GAY + 5%', 'HOA + 00'],
        ['XUONG CA', 'SU KIEN', 'KHUYEN MAI'],
        ['GUI TIN NHAN NHANH'],
        ['DOI CHUAN BI', 'DOI LEN CA', 'DOI CHO LENH', 'DOI BAT DAU', 'DOI CON 10%'],
        ['DOI CAI 10%', 'DOI XUONG CA', 'DOI SU KIEN', 'DOI KHUYEN MAI'],
    ], resize_keyboard=True, one_time_keyboard=False)

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

def check_auth(uid): return uid in authenticated_users

async def start(u: Update, c: ContextTypes.DEFAULT_TYPE):
    uid = u.effective_user.id
    if not check_auth(uid):
        pending[uid] = ("login", None, None)
        await u.message.reply_text("Bot nay da bao mat! Nhap mat khau:", reply_markup=ReplyKeyboardRemove())
        return WAITING_PASS
    await u.message.reply_text(
        "He thong BOT LENH VIP san sang!\n\n"
        "NAP LENH: Go /nap1 den /nap10 roi gui anh hoac text.\n"
        "GUI LENH: Bam nut tren menu.", reply_markup=bieu_dien_menu())
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
    uid = u.effective_user.id
    pending.pop(uid, None)
    await u.message.reply_text("Da huy.", reply_markup=bieu_dien_menu())
    return ConversationHandler.END

async def nap_cmd(u: Update, c: ContextTypes.DEFAULT_TYPE):
    uid = u.effective_user.id
    if not check_auth(uid):
        await u.message.reply_text("Chua xac thuc! Go /start.")
        return ConversationHandler.END
    n = int(u.message.text.strip().replace("/nap", ""))
    pending[uid] = ("nap", n, None)
    await u.message.reply_text(
        f"NAP LENH {n}:\n"
        f"- Gui ANH (co the kem chu thich caption)\n"
        f"- Hoac gui TEXT\n"
        f"/cancel de huy.",
        reply_markup=ReplyKeyboardRemove())
    return WAITING

async def nap_receive(u: Update, c: ContextTypes.DEFAULT_TYPE):
    uid = u.effective_user.id
    if uid not in pending or pending[uid][0] != "nap":
        return ConversationHandler.END
    n = pending[uid][1]
    data = load()
    if u.message.photo:
        # Luu anh: lay file_id anh lon nhat
        file_id = u.message.photo[-1].file_id
        caption = u.message.caption or ""
        data[f"key{n}"] = {"type": "photo", "file_id": file_id, "caption": caption}
        del pending[uid]
        save(data)
        await u.message.reply_text(
            f"Da luu lenh {n} (ANH)!\n"
            f"Caption: {caption if caption else '(khong co)'}",
            reply_markup=bieu_dien_menu())
    elif u.message.text:
        text = u.message.text.strip()
        if not text:
            await u.message.reply_text("Text khong duoc de trong! Gui lai hoac /cancel:")
            return WAITING
        data[f"key{n}"] = {"type": "text", "text": text}
        del pending[uid]
        save(data)
        await u.message.reply_text(
            f"Da luu lenh {n} (TEXT)!\n"
            f"Noi dung: {text[:50]}...",
            reply_markup=bieu_dien_menu())
    else:
        await u.message.reply_text("Chi ho tro anh hoac text! Gui lai hoac /cancel:")
        return WAITING
    return ConversationHandler.END

async def _send_key(n: int, u: Update, c: ContextTypes.DEFAULT_TYPE):
    """Gui lenh n ra group CHAT_LINK"""
    data = load()
    item = data.get(f"key{n}")
    if not item:
        await u.message.reply_text(
            f"LENH {n} CHUA DUOC NAP!\n"
            f"Dung /nap{n} de nap noi dung truoc.",
            reply_markup=bieu_dien_menu())
        return
    try:
        itype = item.get("type", "")
        if itype == "photo":
            await c.bot.send_photo(
                chat_id=CHAT_LINK,
                photo=item["file_id"],
                caption=item.get("caption", "") or "")
            await u.message.reply_text(f"Da gui lenh {n} (anh) len group!", reply_markup=bieu_dien_menu())
        elif itype == "text":
            text = item.get("text", "").strip()
            if not text:
                await u.message.reply_text(
                    f"Lenh {n} bi luu text rong! Vui long nap lai bang /nap{n}.",
                    reply_markup=bieu_dien_menu())
                return
            await c.bot.send_message(chat_id=CHAT_LINK, text=text)
            await u.message.reply_text(f"Da gui lenh {n} (text) len group!", reply_markup=bieu_dien_menu())
        else:
            await u.message.reply_text(
                f"Lenh {n} bi loi dinh dang (type={itype}). Nap lai bang /nap{n}.",
                reply_markup=bieu_dien_menu())
    except Exception as e:
        logging.error(f"Loi gui lenh {n}: {e}")
        await u.message.reply_text(f"Loi gui lenh {n}: {e}", reply_markup=bieu_dien_menu())

async def gui_cmd(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not check_auth(u.effective_user.id):
        await u.message.reply_text("Chua xac thuc! Go /start.")
        return
    n = int(u.message.text.strip().replace("/gui", ""))
    await _send_key(n, u, c)

async def doi_cmd(u: Update, c: ContextTypes.DEFAULT_TYPE):
    uid = u.effective_user.id
    if not check_auth(uid):
        await u.message.reply_text("Chua xac thuc! Go /start.")
        return ConversationHandler.END
    n = int(u.message.text.strip().replace("/doi", ""))
    data = load()
    if f"key{n}" not in data:
        await u.message.reply_text(
            f"Lenh {n} chua nap! Dung /nap{n} de nap.",
            reply_markup=bieu_dien_menu())
        return ConversationHandler.END
    pending[uid] = ("doi", n, None)
    item = data[f"key{n}"]
    itype = item.get("type", "?")
    await u.message.reply_text(
        f"DOI LENH {n} (hien tai: {itype}):\n"
        f"Gui ANH moi hoac TEXT moi.\n"
        f"/cancel de huy.",
        reply_markup=ReplyKeyboardRemove())
    return WAITING

async def doi_receive(u: Update, c: ContextTypes.DEFAULT_TYPE):
    uid = u.effective_user.id
    if uid not in pending or pending[uid][0] != "doi":
        return ConversationHandler.END
    n = pending[uid][1]
    data = load()
    key = f"key{n}"
    if u.message.photo:
        file_id = u.message.photo[-1].file_id
        caption = u.message.caption or ""
        data[key] = {"type": "photo", "file_id": file_id, "caption": caption}
        del pending[uid]
        save(data)
        await u.message.reply_text(
            f"Da doi lenh {n} thanh ANH!\nCaption: {caption if caption else '(khong co)'}",
            reply_markup=bieu_dien_menu())
    elif u.message.text:
        text = u.message.text.strip()
        if not text:
            await u.message.reply_text("Text khong duoc de trong! Gui lai hoac /cancel:")
            return WAITING
        # Neu lenh cu la anh, chi doi caption; neu la text thi doi text
        old = data.get(key, {})
        if old.get("type") == "photo":
            data[key]["caption"] = text
            del pending[uid]
            save(data)
            await u.message.reply_text(
                f"Da doi caption lenh {n}!\nCaption moi: {text[:50]}",
                reply_markup=bieu_dien_menu())
        else:
            data[key] = {"type": "text", "text": text}
            del pending[uid]
            save(data)
            await u.message.reply_text(
                f"Da doi lenh {n} thanh TEXT!\nNoi dung: {text[:50]}",
                reply_markup=bieu_dien_menu())
    else:
        await u.message.reply_text("Chi ho tro anh hoac text! Gui lai hoac /cancel:")
        return WAITING
    return ConversationHandler.END

async def all_cmd(u: Update, c: ContextTypes.DEFAULT_TYPE):
    uid = u.effective_user.id
    if not check_auth(uid):
        await u.message.reply_text("Chua xac thuc! Go /start.")
        return ConversationHandler.END
    pending[uid] = ("all", None, None)
    await u.message.reply_text(
        "GUI TIN NHAN NHANH vao group:\n"
        "Gui ANH hoac TEXT.\n"
        "/cancel de huy.",
        reply_markup=ReplyKeyboardRemove())
    return WAITING

async def all_receive(u: Update, c: ContextTypes.DEFAULT_TYPE):
    uid = u.effective_user.id
    if uid not in pending or pending[uid][0] != "all":
        return ConversationHandler.END
    try:
        if u.message.photo:
            await c.bot.send_photo(
                chat_id=CHAT_LINK,
                photo=u.message.photo[-1].file_id,
                caption=u.message.caption or "")
        elif u.message.text:
            text = u.message.text.strip()
            if not text:
                await u.message.reply_text("Text khong duoc de trong!")
                return WAITING
            await c.bot.send_message(chat_id=CHAT_LINK, text=text)
        else:
            await u.message.reply_text("Chi ho tro anh hoac text!")
            return WAITING
        await u.message.reply_text("Da gui vao group!", reply_markup=bieu_dien_menu())
    except Exception as e:
        await u.message.reply_text(f"Loi: {e}")
    del pending[uid]
    return ConversationHandler.END

async def button_handler(u: Update, c: ContextTypes.DEFAULT_TYPE):
    uid = u.effective_user.id
    if not check_auth(uid):
        await u.message.reply_text("Chua xac thuc! Go /start.")
        return ConversationHandler.END
    text = u.message.text
    if text not in BUTTON_MAP:
        return ConversationHandler.END
    cmd = BUTTON_MAP[text]
    if cmd.startswith("/gui"):
        n = int(cmd.replace("/gui", ""))
        await _send_key(n, u, c)
        return ConversationHandler.END
    elif cmd.startswith("/doi"):
        n = int(cmd.replace("/doi", ""))
        data = load()
        if f"key{n}" not in data:
            await u.message.reply_text(
                f"Lenh {n} chua nap! Dung /nap{n} de nap truoc.",
                reply_markup=bieu_dien_menu())
            return ConversationHandler.END
        pending[uid] = ("doi", n, None)
        item = data[f"key{n}"]
        itype = item.get("type", "?")
        await u.message.reply_text(
            f"DOI LENH {n} (hien tai: {itype}):\nGui ANH moi hoac TEXT moi.\n/cancel de huy.",
            reply_markup=ReplyKeyboardRemove())
        return WAITING
    elif cmd == "/all":
        pending[uid] = ("all", None, None)
        await u.message.reply_text(
            "GUI NHANH vao group:\nGui ANH hoac TEXT.\n/cancel de huy.",
            reply_markup=ReplyKeyboardRemove())
        return WAITING
    return ConversationHandler.END

async def xem_lenh(u: Update, c: ContextTypes.DEFAULT_TYPE):
    """Xem danh sach cac lenh da nap"""
    if not check_auth(u.effective_user.id):
        await u.message.reply_text("Chua xac thuc! Go /start.")
        return
    data = load()
    keys = [k for k in data.keys() if k.startswith("key")]
    if not keys:
        await u.message.reply_text("Chua nap lenh nao! Dung /nap1 den /nap10.", reply_markup=bieu_dien_menu())
        return
    msg = "DANH SACH LENH DA NAP:\n"
    for k in sorted(keys):
        n = k.replace("key", "")
        item = data[k]
        itype = item.get("type", "?")
        if itype == "photo":
            cap = item.get("caption", "")
            msg += f"  Lenh {n}: [ANH] caption={cap[:30] if cap else '(khong co)'}\n"
        else:
            txt = item.get("text", "")
            msg += f"  Lenh {n}: [TEXT] {txt[:40]}\n"
    await u.message.reply_text(msg, reply_markup=bieu_dien_menu())

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={WAITING_PASS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_password)]},
        fallbacks=[CommandHandler("cancel", cancel)]
    ))
    app.add_handler(CommandHandler("xem", xem_lenh))
    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("all", all_cmd)],
        states={WAITING: [MessageHandler(filters.ALL & ~filters.COMMAND, all_receive)]},
        fallbacks=[CommandHandler("cancel", cancel)]
    ))
    for i in range(1, 11):
        app.add_handler(ConversationHandler(
            entry_points=[CommandHandler(f"nap{i}", nap_cmd)],
            states={WAITING: [MessageHandler(filters.ALL & ~filters.COMMAND, nap_receive)]},
            fallbacks=[CommandHandler("cancel", cancel)]
        ))
        if i != 3:
            app.add_handler(CommandHandler(f"gui{i}", gui_cmd))
        app.add_handler(ConversationHandler(
            entry_points=[CommandHandler(f"doi{i}", doi_cmd)],
            states={WAITING: [MessageHandler(filters.ALL & ~filters.COMMAND, doi_receive)]},
            fallbacks=[CommandHandler("cancel", cancel)]
        ))
    for i in range(11, 19):
        app.add_handler(ConversationHandler(
            entry_points=[CommandHandler(f"doi{i}", doi_cmd)],
            states={WAITING: [MessageHandler(filters.ALL & ~filters.COMMAND, doi_receive)]},
            fallbacks=[CommandHandler("cancel", cancel)]
        ))
    app.add_handler(ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & ~filters.COMMAND, button_handler)],
        states={WAITING: [MessageHandler(filters.ALL & ~filters.COMMAND, doi_receive)]},
        fallbacks=[CommandHandler("cancel", cancel)]
    ))
    print("Bot dang chay!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
