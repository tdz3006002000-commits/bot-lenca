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
    'CHUAN BI':   'gui1',
    'LEN CA':     'gui2',
    'BAO BAN':    'gui3',
    'CHO LENH':   'gui4',
    'BAT DAU':    'gui5',
    'CON 10%':    'gui6',
    'CAI 10%':    'gui7',
    'HUP + 10%':  'gui8',
    'GAY - 10%':  'gui9',
    'HUP + 5%':   'gui10',
    'GAY - 5%':   'gui11',
    'HUP - 5%':   'gui12',
    'GAY - 15%':  'gui13',
    'GAY + 5%':   'gui14',
    'HOA + 00':   'gui15',
    'XUONG CA':   'gui16',
    'SU KIEN':    'gui17',
    'KHUYEN MAI': 'gui18',
    'GUI TIN NHAN NHANH': 'all',
    'DOI CHUAN BI':  'doi1',
    'DOI LEN CA':    'doi2',
    'DOI CHO LENH':  'doi4',
    'DOI BAT DAU':   'doi5',
    'DOI CON 10%':   'doi6',
    'DOI CAI 10%':   'doi7',
    'DOI XUONG CA':  'doi16',
    'DOI SU KIEN':   'doi17',
    'DOI KHUYEN MAI':'doi18',
}

# ==================== HELPERS ====================

def entities_to_list(entities):
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

def is_gif_document(msg):
    """Kiem tra xem document co phai GIF khong"""
    if msg.document:
        mime = msg.document.mime_type or ""
        fname = msg.document.file_name or ""
        return mime == "image/gif" or fname.lower().endswith(".gif")
    return False

def save_message(data, n, msg):
    """Luu mot tin nhan vao data[key{n}], giu nguyen dinh dang.
    Thu tu uu tien: animation > photo > video > sticker > document > voice > video_note > text
    Luu y: GIF co the la animation HOAC document tuy theo cach gui
    """
    caption = msg.caption or ""
    cap_entities = entities_to_list(msg.caption_entities)

    # GIF gui tu desktop/web co the la animation
    if msg.animation:
        file_id = msg.animation.file_id
        data[f"key{n}"] = {
            "type": "animation", "file_id": file_id,
            "caption": caption, "cap_entities": cap_entities
        }
        logger.info(f"Saved key{n} as animation, file_id={file_id[:20]}")
        return True

    if msg.photo:
        file_id = msg.photo[-1].file_id
        data[f"key{n}"] = {
            "type": "photo", "file_id": file_id,
            "caption": caption, "cap_entities": cap_entities
        }
        logger.info(f"Saved key{n} as photo")
        return True

    if msg.video:
        file_id = msg.video.file_id
        data[f"key{n}"] = {
            "type": "video", "file_id": file_id,
            "caption": caption, "cap_entities": cap_entities
        }
        logger.info(f"Saved key{n} as video")
        return True

    if msg.sticker:
        data[f"key{n}"] = {"type": "sticker", "file_id": msg.sticker.file_id}
        logger.info(f"Saved key{n} as sticker")
        return True

    if msg.document:
        file_id = msg.document.file_id
        mime = msg.document.mime_type or ""
        # Neu la GIF document -> luu nhu animation de gui dung dinh dang
        if mime == "image/gif":
            data[f"key{n}"] = {
                "type": "animation", "file_id": file_id,
                "caption": caption, "cap_entities": cap_entities
            }
            logger.info(f"Saved key{n} as animation (from gif document)")
        else:
            data[f"key{n}"] = {
                "type": "document", "file_id": file_id,
                "caption": caption, "cap_entities": cap_entities
            }
            logger.info(f"Saved key{n} as document, mime={mime}")
        return True

    if msg.voice:
        file_id = msg.voice.file_id
        data[f"key{n}"] = {
            "type": "voice", "file_id": file_id,
            "caption": caption, "cap_entities": cap_entities
        }
        logger.info(f"Saved key{n} as voice")
        return True

    if msg.video_note:
        data[f"key{n}"] = {"type": "video_note", "file_id": msg.video_note.file_id}
        logger.info(f"Saved key{n} as video_note")
        return True

    if msg.text:
        text = msg.text
        text_entities = entities_to_list(msg.entities)
        data[f"key{n}"] = {"type": "text", "text": text, "entities": text_entities}
        logger.info(f"Saved key{n} as text, len={len(text)}")
        return True

    logger.warning(f"save_message key{n}: unknown message type")
    return False

# ==================== CORE SEND ====================

async def _send_key(n: int, u: Update, c: ContextTypes.DEFAULT_TYPE):
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
            await c.bot.send_message(chat_id=CHAT_LINK, text=text, entities=text_entities)
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

# ==================== COMMAND HANDLERS ====================

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
        "NAP LENH: Go /nap1 den /nap18.\n"
        "XEM LENH: /xem\n"
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
    txt = u.message.text.strip()
    n = int(txt.replace("/nap", ""))
    pending[uid] = ("nap", n, None)
    await u.message.reply_text(
        f"NAP LENH {n}:\n"
        f"Gui: Anh, GIF, Video, Sticker, File, Text.\n"
        f"(Gui kem caption neu muon)\n"
        f"/cancel de huy.",
        reply_markup=ReplyKeyboardRemove())
    return WAITING

async def nap_receive(u: Update, c: ContextTypes.DEFAULT_TYPE):
    uid = u.effective_user.id
    if uid not in pending or pending[uid][0] != "nap":
        logger.warning(f"nap_receive called but uid {uid} not in pending nap state")
        return ConversationHandler.END
    n = pending[uid][1]

    msg = u.message
    # Log tat ca attributes de debug
    logger.info(
        f"nap_receive n={n}: "
        f"photo={bool(msg.photo)}, animation={bool(msg.animation)}, "
        f"video={bool(msg.video)}, sticker={bool(msg.sticker)}, "
        f"document={bool(msg.document)}, voice={bool(msg.voice)}, "
        f"video_note={bool(msg.video_note)}, text={bool(msg.text)}, "
        f"caption={repr(msg.caption)}"
    )

    # Kiem tra text rong
    if msg.text and not msg.text.strip():
        await msg.reply_text("Text trong! Gui noi dung co chu hoac media.", reply_markup=ReplyKeyboardRemove())
        return WAITING

    # Kiem tra text la lenh /command
    if msg.text and msg.text.strip().startswith("/"):
        await msg.reply_text("Khong luu lenh /command. Gui text hoac media.", reply_markup=bieu_dien_menu())
        del pending[uid]
        return ConversationHandler.END

    data = load()
    ok = save_message(data, n, msg)
    if not ok:
        await msg.reply_text(
            f"Khong nhan duoc! Bot da nhan:\n"
            f"photo={bool(msg.photo)}, gif={bool(msg.animation)}, "
            f"video={bool(msg.video)}, doc={bool(msg.document)}, text={bool(msg.text)}\n"
            f"Thu gui lai theo cach khac.",
            reply_markup=ReplyKeyboardRemove())
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
            f"Caption: {cap[:40] if cap else '(khong co)'}",
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
        "GUI TIN NHAN NHANH:\nGui noi dung de gui ngay len group.\n/cancel de huy.",
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
        cap_ent = list_to_entities(entities_to_list(msg.caption_entities))
        if msg.animation:
            await bot.send_animation(chat_id=CHAT_LINK, animation=msg.animation.file_id,
                                     caption=msg.caption or "", caption_entities=cap_ent)
        elif msg.photo:
            await bot.send_photo(chat_id=CHAT_LINK, photo=msg.photo[-1].file_id,
                                 caption=msg.caption or "", caption_entities=cap_ent)
        elif msg.video:
            await bot.send_video(chat_id=CHAT_LINK, video=msg.video.file_id,
                                 caption=msg.caption or "", caption_entities=cap_ent)
        elif msg.sticker:
            await bot.send_sticker(chat_id=CHAT_LINK, sticker=msg.sticker.file_id)
        elif msg.document:
            mime = msg.document.mime_type or ""
            if mime == "image/gif":
                await bot.send_animation(chat_id=CHAT_LINK, animation=msg.document.file_id,
                                         caption=msg.caption or "", caption_entities=cap_ent)
            else:
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
    lines = ["DANH SACH LENH (1-18):"]
    for i in range(1, 19):
        key = f"key{i}"
        if key in data:
            item = data[key]
            itype = item.get("type", "?")
            if itype == "text":
                preview = item.get("text", "")[:25]
                lines.append(f"Lenh {i:2d}: [TEXT] {preview}")
            else:
                cap = item.get("caption", "")
                lines.append(f"Lenh {i:2d}: [{itype.upper()}] {cap[:25] if cap else '(khong caption)'}")
        else:
            lines.append(f"Lenh {i:2d}: (CHUA NAP)")
    await u.message.reply_text("\n".join(lines), reply_markup=bieu_dien_menu())

async def button_handler(u: Update, c: ContextTypes.DEFAULT_TYPE):
    uid = u.effective_user.id
    if not check_auth(uid):
        await u.message.reply_text("Chua xac thuc! Go /start.")
        return
    btn = u.message.text
    cmd = BUTTON_MAP.get(btn)
    if not cmd:
        return

    if cmd == "all":
        pending[uid] = ("all", None, None)
        await u.message.reply_text(
            "GUI TIN NHAN NHANH:\nGui noi dung de gui ngay len group.\n/cancel de huy.",
            reply_markup=ReplyKeyboardRemove())
        return

    if cmd.startswith("gui"):
        n = int(cmd.replace("gui", ""))
        await _send_key(n, u, c)
        return

    if cmd.startswith("doi"):
        n = int(cmd.replace("doi", ""))
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

    # Filter bat tat ca loai media - dung filters.ALL thay vi liet ke tung loai
    # de tranh bo sot GIF/animation gui duoi dang document
    all_media = filters.ALL & ~filters.COMMAND

    auth_conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={WAITING_PASS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_password)]},
        fallbacks=[CommandHandler("cancel", cancel)],
        per_user=True,
        allow_reentry=True,
    )

    nap_conv = ConversationHandler(
        entry_points=[CommandHandler(f"nap{i}", nap_cmd) for i in range(1, 19)],
        states={WAITING: [MessageHandler(all_media, nap_receive)]},
        fallbacks=[CommandHandler("cancel", cancel)],
        per_user=True,
        allow_reentry=True,
    )

    doi_conv = ConversationHandler(
        entry_points=[CommandHandler(f"doi{i}", doi_cmd) for i in range(1, 19)],
        states={WAITING: [MessageHandler(all_media, doi_receive)]},
        fallbacks=[CommandHandler("cancel", cancel)],
        per_user=True,
        allow_reentry=True,
    )

    all_conv = ConversationHandler(
        entry_points=[CommandHandler("all", all_cmd)],
        states={WAITING: [MessageHandler(all_media, all_receive)]},
        fallbacks=[CommandHandler("cancel", cancel)],
        per_user=True,
        allow_reentry=True,
    )

    import re
    btn_labels = list(BUTTON_MAP.keys())
    escaped = [re.escape(b) for b in btn_labels]
    btn_pattern = "^(" + "|".join(escaped) + ")$"
    app.add_handler(MessageHandler(filters.Regex(btn_pattern), button_handler))

    app.add_handler(auth_conv)
    app.add_handler(nap_conv)
    app.add_handler(doi_conv)
    app.add_handler(all_conv)

    for i in range(1, 19):
        app.add_handler(CommandHandler(f"gui{i}", gui_cmd))
    app.add_handler(CommandHandler("xem", xem_lenh))

    logger.info("Bot dang chay...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
