import os
import json
import logging
import base64
import requests
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, MessageEntity
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("BOT_TOKEN", "8877176302:AAETTH8e3LWY0BL3pHsOpUo4huAQjzOq2bg")
CHAT_LINK = "-1003617964607"
BOT_PASSWORD = os.environ.get("BOT_PASSWORD", "HARRY2005TDZ")
RAILWAY_API_TOKEN = os.environ.get("RAILWAY_API_TOKEN", "")
RAILWAY_SERVICE_ID = os.environ.get("RAILWAY_SERVICE_ID", "13ebf69b-680a-44d2-a905-ce4ef7803993")
RAILWAY_ENVIRONMENT_ID = os.environ.get("RAILWAY_ENVIRONMENT_ID", "33dea9d1-8da0-40b1-9569-dc64580a4f0d")

# ==================== STORAGE ====================

def load():
    raw = os.environ.get("BOT_DATA", "")
    if raw:
        try:
            return json.loads(base64.b64decode(raw).decode("utf-8"))
        except Exception as e:
            logger.error(f"Load error: {e}")
    return {}

def save(data):
    try:
        encoded = base64.b64encode(json.dumps(data, ensure_ascii=False).encode()).decode()
        os.environ["BOT_DATA"] = encoded
        if RAILWAY_API_TOKEN:
            try:
                mut = """mutation variableUpsert($input: VariableUpsertInput!) {
                    variableUpsert(input: $input)
                }"""
                requests.post(
                    "https://backboard.railway.com/graphql/v2",
                    json={"query": mut, "variables": {"input": {
                        "serviceId": RAILWAY_SERVICE_ID,
                        "environmentId": RAILWAY_ENVIRONMENT_ID,
                        "name": "BOT_DATA",
                        "value": encoded
                    }}},
                    headers={
                        "Authorization": f"Bearer {RAILWAY_API_TOKEN}",
                        "Content-Type": "application/json"
                    },
                    timeout=10
                )
            except Exception as e:
                logger.error(f"Railway API error: {e}")
    except Exception as e:
        logger.error(f"Save error: {e}")

# ==================== STATES ====================

WAITING = 1
WAITING_PASS = 99
pending = {}

# ==================== AUTH ====================

def load_auth():
    return set(load().get("_auth", []))

authenticated_users = load_auth()

def save_auth():
    data = load()
    data["_auth"] = list(authenticated_users)
    save(data)

def check_auth(uid):
    return uid in authenticated_users

# ==================== MENU ====================

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

# ==================== HELPERS ====================

def entities_to_list(entities):
    """Chuyen MessageEntity list sang list dict de luu JSON"""
    if not entities:
        return []
    result = []
    for e in entities:
        d = {"type": e.type, "offset": e.offset, "length": e.length}
        if e.url:
            d["url"] = e.url
        if e.language:
            d["language"] = e.language
        result.append(d)
    return result

def list_to_entities(lst):
    """Chuyen list dict ve MessageEntity list"""
    if not lst:
        return None
    entities = []
    for d in lst:
        e = MessageEntity(
            type=d["type"],
            offset=d["offset"],
            length=d["length"],
            url=d.get("url"),
            language=d.get("language"),
        )
        entities.append(e)
    return entities if entities else None

def save_message(data, n, msg):
    """Luu mot tin nhan (bat ky loai) vao data[key{n}]"""
    if msg.photo:
        file_id = msg.photo[-1].file_id
        caption = msg.caption or ""
        cap_entities = entities_to_list(msg.caption_entities)
        data[f"key{n}"] = {
            "type": "photo", "file_id": file_id,
            "caption": caption, "cap_entities": cap_entities
        }
    elif msg.animation:
        file_id = msg.animation.file_id
        caption = msg.caption or ""
        cap_entities = entities_to_list(msg.caption_entities)
        data[f"key{n}"] = {
            "type": "animation", "file_id": file_id,
            "caption": caption, "cap_entities": cap_entities
        }
    elif msg.video:
        file_id = msg.video.file_id
        caption = msg.caption or ""
        cap_entities = entities_to_list(msg.caption_entities)
        data[f"key{n}"] = {
            "type": "video", "file_id": file_id,
            "caption": caption, "cap_entities": cap_entities
        }
    elif msg.sticker:
        data[f"key{n}"] = {"type": "sticker", "file_id": msg.sticker.file_id}
    elif msg.document:
        file_id = msg.document.file_id
        caption = msg.caption or ""
        cap_entities = entities_to_list(msg.caption_entities)
        data[f"key{n}"] = {
            "type": "document", "file_id": file_id,
            "caption": caption, "cap_entities": cap_entities
        }
    elif msg.voice:
        file_id = msg.voice.file_id
        caption = msg.caption or ""
        cap_entities = entities_to_list(msg.caption_entities)
        data[f"key{n}"] = {
            "type": "voice", "file_id": file_id,
            "caption": caption, "cap_entities": cap_entities
        }
    elif msg.video_note:
        data[f"key{n}"] = {"type": "video_note", "file_id": msg.video_note.file_id}
    elif msg.text:
        text = msg.text
        text_entities = entities_to_list(msg.entities)
        data[f"key{n}"] = {
            "type": "text", "text": text, "entities": text_entities
        }
    else:
        return False
    return True

# ==================== CORE SEND ====================

async def _send_key(n: int, u: Update, c: ContextTypes.DEFAULT_TYPE):
    """Gui noi dung lenh n ra group CHAT_LINK, giu nguyen dinh dang"""
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
        caption = item.get("caption", "") or ""
        file_id = item.get("file_id", "")
        cap_entities = list_to_entities(item.get("cap_entities", []))

        if itype == "text":
            text = item.get("text", "")
            if not text or not text.strip():
                await u.message.reply_text(
                    f"Lenh {n} text rong! Nap lai bang /nap{n}.",
                    reply_markup=bieu_dien_menu())
                return
            text_entities = list_to_entities(item.get("entities", []))
            await c.bot.send_message(
                chat_id=CHAT_LINK,
                text=text,
                entities=text_entities
            )
            await u.message.reply_text(f"Da gui lenh {n} (chu) len group!", reply_markup=bieu_dien_menu())

        elif itype == "photo":
            await c.bot.send_photo(
                chat_id=CHAT_LINK, photo=file_id,
                caption=caption, caption_entities=cap_entities)
            await u.message.reply_text(f"Da gui lenh {n} (anh) len group!", reply_markup=bieu_dien_menu())

        elif itype == "animation":
            await c.bot.send_animation(
                chat_id=CHAT_LINK, animation=file_id,
                caption=caption, caption_entities=cap_entities)
            await u.message.reply_text(f"Da gui lenh {n} (GIF) len group!", reply_markup=bieu_dien_menu())

        elif itype == "video":
            await c.bot.send_video(
                chat_id=CHAT_LINK, video=file_id,
                caption=caption, caption_entities=cap_entities)
            await u.message.reply_text(f"Da gui lenh {n} (video) len group!", reply_markup=bieu_dien_menu())

        elif itype == "sticker":
            await c.bot.send_sticker(chat_id=CHAT_LINK, sticker=file_id)
            await u.message.reply_text(f"Da gui lenh {n} (sticker) len group!", reply_markup=bieu_dien_menu())

        elif itype == "document":
            await c.bot.send_document(
                chat_id=CHAT_LINK, document=file_id,
                caption=caption, caption_entities=cap_entities)
            await u.message.reply_text(f"Da gui lenh {n} (file) len group!", reply_markup=bieu_dien_menu())

        elif itype == "voice":
            await c.bot.send_voice(
                chat_id=CHAT_LINK, voice=file_id,
                caption=caption, caption_entities=cap_entities)
            await u.message.reply_text(f"Da gui lenh {n} (voice) len group!", reply_markup=bieu_dien_menu())

        elif itype == "video_note":
            await c.bot.send_video_note(chat_id=CHAT_LINK, video_note=file_id)
            await u.message.reply_text(f"Da gui lenh {n} (video note) len group!", reply_markup=bieu_dien_menu())

        else:
            await u.message.reply_text(
                f"Lenh {n} dinh dang la: {itype}. Nap lai bang /nap{n}.",
                reply_markup=bieu_dien_menu())
    except Exception as e:
        logger.error(f"_send_key {n} error: {e}")
        await u.message.reply_text(f"Loi gui lenh {n}: {e}", reply_markup=bieu_dien_menu())

# ==================== HANDLERS ====================

async def start(u: Update, c: ContextTypes.DEFAULT_TYPE):
    uid = u.effective_user.id
    if not check_auth(uid):
        pending[uid] = ("login", None, None)
        await u.message.reply_text(
            "Bot nay da bao mat! Nhap mat khau:",
            reply_markup=ReplyKeyboardRemove())
        return WAITING_PASS
    await u.message.reply_text(
        "He thong BOT LENH VIP san sang!\n\n"
        "NAP LENH: Go /nap1 den /nap10 roi gui anh/gif/video/text (co dinh dang).\n"
        "GUI LENH: Bam nut tren menu.",
        reply_markup=bieu_dien_menu())
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
        f"Ho tro: Anh, GIF, Video, Sticker, Voice, File, Text (giu nguyen dinh dang).\n"
        f"/cancel de huy.",
        reply_markup=ReplyKeyboardRemove())
    return WAITING

async def nap_receive(u: Update, c: ContextTypes.DEFAULT_TYPE):
    uid = u.effective_user.id
    if uid not in pending or pending[uid][0] != "nap":
        return ConversationHandler.END
    n = pending[uid][1]
    data = load()
    msg = u.message

    # Kiem tra text trong
    if msg.text and not msg.text.strip():
        await msg.reply_text("Text trong! Gui noi dung co chu hoac media.", reply_markup=ReplyKeyboardRemove())
        return WAITING

    # Kiem tra text la lenh /command
    if msg.text and msg.text.strip().startswith("/"):
        await msg.reply_text("Khong luu lenh /command. Gui text binh thuong hoac media.", reply_markup=bieu_dien_menu())
        del pending[uid]
        return ConversationHandler.END

    ok = save_message(data, n, msg)
    if not ok:
        await msg.reply_text("Dinh dang khong ho tro. Gui: anh/gif/video/sticker/voice/file/text.", reply_markup=ReplyKeyboardRemove())
        return WAITING

    del pending[uid]
    save(data)
    item = data[f"key{n}"]
    itype = item.get("type", "?")
    if itype == "text":
        preview = item.get("text", "")[:40]
        await msg.reply_text(f"Da luu lenh {n} (TEXT)!\nNoi dung: {preview}", reply_markup=bieu_dien_menu())
    else:
        cap = item.get("caption", "")
        await msg.reply_text(
            f"Da luu lenh {n} ({itype.upper()})!\n"
            f"Caption: {cap[:30] if cap else '(khong co)'}",
            reply_markup=bieu_dien_menu())
    return ConversationHandler.END

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
        f"Gui noi dung moi.\n/cancel de huy.",
        reply_markup=ReplyKeyboardRemove())
    return WAITING

async def doi_receive(u: Update, c: ContextTypes.DEFAULT_TYPE):
    uid = u.effective_user.id
    if uid not in pending or pending[uid][0] != "doi":
        return ConversationHandler.END
    pending[uid] = ("nap", pending[uid][1], None)
    return await nap_receive(u, c)

async def all_cmd(u: Update, c: ContextTypes.DEFAULT_TYPE):
    uid = u.effective_user.id
    if not check_auth(uid):
        await u.message.reply_text("Chua xac thuc! Go /start.")
        return ConversationHandler.END
    pending[uid] = ("all", None, None)
    await u.message.reply_text(
        "GUI TIN NHAN NHANH:\nGui noi dung (anh/gif/video/text) de gui ngay len group.\n/cancel de huy.",
        reply_markup=ReplyKeyboardRemove())
    return WAITING

async def all_receive(u: Update, c: ContextTypes.DEFAULT_TYPE):
    uid = u.effective_user.id
    if uid not in pending or pending[uid][0] != "all":
        return ConversationHandler.END
    del pending[uid]
    msg = u.message
    bot = c.bot
    try:
        if msg.photo:
            cap_ent = list_to_entities(entities_to_list(msg.caption_entities))
            await bot.send_photo(chat_id=CHAT_LINK, photo=msg.photo[-1].file_id,
                                 caption=msg.caption or "", caption_entities=cap_ent)
        elif msg.animation:
            cap_ent = list_to_entities(entities_to_list(msg.caption_entities))
            await bot.send_animation(chat_id=CHAT_LINK, animation=msg.animation.file_id,
                                     caption=msg.caption or "", caption_entities=cap_ent)
        elif msg.video:
            cap_ent = list_to_entities(entities_to_list(msg.caption_entities))
            await bot.send_video(chat_id=CHAT_LINK, video=msg.video.file_id,
                                 caption=msg.caption or "", caption_entities=cap_ent)
        elif msg.sticker:
            await bot.send_sticker(chat_id=CHAT_LINK, sticker=msg.sticker.file_id)
        elif msg.document:
            cap_ent = list_to_entities(entities_to_list(msg.caption_entities))
            await bot.send_document(chat_id=CHAT_LINK, document=msg.document.file_id,
                                    caption=msg.caption or "", caption_entities=cap_ent)
        elif msg.text:
            text = msg.text.strip()
            if not text:
                await msg.reply_text("Text trong! Thu lai.", reply_markup=bieu_dien_menu())
                return ConversationHandler.END
            txt_ent = list_to_entities(entities_to_list(msg.entities))
            await bot.send_message(chat_id=CHAT_LINK, text=text, entities=txt_ent)
        else:
            await msg.reply_text("Dinh dang khong ho tro.", reply_markup=bieu_dien_menu())
            return ConversationHandler.END
        await msg.reply_text("Da gui tin nhan len group!", reply_markup=bieu_dien_menu())
    except Exception as e:
        logger.error(f"all_receive error: {e}")
        await msg.reply_text(f"Loi gui: {e}", reply_markup=bieu_dien_menu())
    return ConversationHandler.END

async def xem_lenh(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not check_auth(u.effective_user.id):
        await u.message.reply_text("Chua xac thuc! Go /start.")
        return
    data = load()
    lines = ["DANH SACH LENH DA NAP:"]
    for i in range(1, 19):
        key = f"key{i}"
        if key in data:
            item = data[key]
            itype = item.get("type", "?")
            if itype == "text":
                preview = item.get("text", "")[:30]
                has_fmt = "co dinh dang" if item.get("entities") else "text thuong"
                lines.append(f"Lenh {i}: [TEXT/{has_fmt}] {preview}")
            else:
                cap = item.get("caption", "")
                lines.append(f"Lenh {i}: [{itype.upper()}] cap={cap[:20] if cap else '(khong)'}")
        else:
            lines.append(f"Lenh {i}: (chua nap)")
    await u.message.reply_text("\n".join(lines), reply_markup=bieu_dien_menu())

async def button_handler(u: Update, c: ContextTypes.DEFAULT_TYPE):
    uid = u.effective_user.id
    if not check_auth(uid):
        await u.message.reply_text("Chua xac thuc! Go /start.")
        return
    text = u.message.text
    cmd = BUTTON_MAP.get(text)
    if not cmd:
        return

    if cmd == "/all":
        pending[uid] = ("all", None, None)
        await u.message.reply_text(
            "GUI TIN NHAN NHANH:\nGui noi dung (anh/gif/video/text) de gui ngay len group.\n/cancel de huy.",
            reply_markup=ReplyKeyboardRemove())
        return

    if cmd.startswith("/gui"):
        n = int(cmd.replace("/gui", ""))
        await _send_key(n, u, c)
        return

    if cmd.startswith("/doi"):
        n = int(cmd.replace("/doi", ""))
        data = load()
        if f"key{n}" not in data:
            await u.message.reply_text(
                f"Lenh {n} chua nap! Dung /nap{n} de nap truoc.",
                reply_markup=bieu_dien_menu())
            return
        pending[uid] = ("doi", n, None)
        item = data[f"key{n}"]
        itype = item.get("type", "?")
        await u.message.reply_text(
            f"DOI LENH {n} (hien tai: {itype}):\n"
            f"Gui noi dung moi.\n/cancel de huy.",
            reply_markup=ReplyKeyboardRemove())
        return

# ==================== MAIN ====================

def main():
    app = Application.builder().token(TOKEN).build()

    media_filter = (
        filters.PHOTO | filters.Document.ALL | filters.VIDEO |
        filters.ANIMATION | filters.Sticker.ALL | filters.VOICE |
        filters.VIDEO_NOTE | filters.TEXT
    )

    auth_conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={WAITING_PASS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_password)]},
        fallbacks=[CommandHandler("cancel", cancel)],
        per_user=True,
        allow_reentry=True,
    )

    nap_conv = ConversationHandler(
        entry_points=[CommandHandler(f"nap{i}", nap_cmd) for i in range(1, 19)],
        states={WAITING: [MessageHandler(media_filter & ~filters.COMMAND, nap_receive)]},
        fallbacks=[CommandHandler("cancel", cancel)],
        per_user=True,
        allow_reentry=True,
    )

    doi_conv = ConversationHandler(
        entry_points=[CommandHandler(f"doi{i}", doi_cmd) for i in range(1, 19)],
        states={WAITING: [MessageHandler(media_filter & ~filters.COMMAND, doi_receive)]},
        fallbacks=[CommandHandler("cancel", cancel)],
        per_user=True,
        allow_reentry=True,
    )

    all_conv = ConversationHandler(
        entry_points=[CommandHandler("all", all_cmd)],
        states={WAITING: [MessageHandler(media_filter & ~filters.COMMAND, all_receive)]},
        fallbacks=[CommandHandler("cancel", cancel)],
        per_user=True,
        allow_reentry=True,
    )

    button_keys = list(BUTTON_MAP.keys())
    button_filter = filters.Regex(f"^({'|'.join(map(lambda x: x.replace('+', r'\\+').replace('%', r'\\%'), button_keys))})$")
    app.add_handler(MessageHandler(button_filter, button_handler))

    app.add_handler(auth_conv)
    app.add_handler(nap_conv)
    app.add_handler(doi_conv)
    app.add_handler(all_conv)

    for i in range(1, 11):
        app.add_handler(CommandHandler(f"gui{i}", gui_cmd))
    app.add_handler(CommandHandler("xem", xem_lenh))

    logger.info("Bot dang chay...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
