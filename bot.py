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

# Cac loai entity bot co the gui lai (khong bao gom custom_emoji)
SAFE_ENTITY_TYPES = {
    "bold", "italic", "underline", "strikethrough", "spoiler",
    "code", "pre", "text_link", "mention", "hashtag", "cashtag",
    "bot_command", "url", "email", "phone_number",
}

# Cac lenh can user gui kem anh truoc khi gui len nhom
# Key 3 = BAO BAN, Key 8-15 = HUP/GAY/HOA
WAIT_PHOTO_KEYS = {3, 8, 9, 10, 11, 12, 13, 14, 15}

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
                logger.info("Saved BOT_DATA to Railway")
            except Exception as e:
                logger.error(f"Railway API error: {e}")
    except Exception as e:
        logger.error(f"Save error: {e}")

# ==================== STATES ====================

WAITING = 1
WAITING_PASS = 99
WAITING_PHOTO = 2   # Cho anh truoc khi gui lenh len nhom
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
        if e.type not in SAFE_ENTITY_TYPES:
            continue
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
        if d.get("type") not in SAFE_ENTITY_TYPES:
            continue
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
    caption = msg.caption or ""
    cap_entities = entities_to_list(msg.caption_entities)

    if msg.animation:
        data[f"key{n}"] = {"type": "animation", "file_id": msg.animation.file_id,
                           "caption": caption, "cap_entities": cap_entities}
        return True
    if msg.photo:
        data[f"key{n}"] = {"type": "photo", "file_id": msg.photo[-1].file_id,
                           "caption": caption, "cap_entities": cap_entities}
        return True
    if msg.video:
        data[f"key{n}"] = {"type": "video", "file_id": msg.video.file_id,
                           "caption": caption, "cap_entities": cap_entities}
        return True
    if msg.sticker:
        data[f"key{n}"] = {"type": "sticker", "file_id": msg.sticker.file_id}
        return True
    if msg.document:
        mime = msg.document.mime_type or ""
        itype = "animation" if mime == "image/gif" else "document"
        data[f"key{n}"] = {"type": itype, "file_id": msg.document.file_id,
                           "caption": caption, "cap_entities": cap_entities}
        return True
    if msg.voice:
        data[f"key{n}"] = {"type": "voice", "file_id": msg.voice.file_id,
                           "caption": caption, "cap_entities": cap_entities}
        return True
    if msg.video_note:
        data[f"key{n}"] = {"type": "video_note", "file_id": msg.video_note.file_id}
        return True
    if msg.text:
        data[f"key{n}"] = {"type": "text", "text": msg.text,
                           "entities": entities_to_list(msg.entities)}
        return True
    return False

async def _send_item_to_group(item, bot):
    """Gui item len CHAT_LINK, tra ve True neu thanh cong"""
    itype = item.get("type", "")
    caption = item.get("caption", "") or ""
    file_id = item.get("file_id", "")
    cap_entities = list_to_entities(item.get("cap_entities", []))

    try:
        if itype == "text":
            text_ent = list_to_entities(item.get("entities", []))
            await bot.send_message(chat_id=CHAT_LINK, text=item.get("text",""), entities=text_ent)
        elif itype == "photo":
            await bot.send_photo(chat_id=CHAT_LINK, photo=file_id,
                                 caption=caption, caption_entities=cap_entities)
        elif itype == "animation":
            await bot.send_animation(chat_id=CHAT_LINK, animation=file_id,
                                     caption=caption, caption_entities=cap_entities)
        elif itype == "video":
            await bot.send_video(chat_id=CHAT_LINK, video=file_id,
                                 caption=caption, caption_entities=cap_entities)
        elif itype == "sticker":
            await bot.send_sticker(chat_id=CHAT_LINK, sticker=file_id)
        elif itype == "document":
            await bot.send_document(chat_id=CHAT_LINK, document=file_id,
                                    caption=caption, caption_entities=cap_entities)
        elif itype == "voice":
            await bot.send_voice(chat_id=CHAT_LINK, voice=file_id,
                                 caption=caption, caption_entities=cap_entities)
        elif itype == "video_note":
            await bot.send_video_note(chat_id=CHAT_LINK, video_note=file_id)
        else:
            return False, f"Dinh dang {itype} khong ro"
        return True, None
    except Exception as e:
        err = str(e)
        # Thu gui lai khong entity neu loi entity
        if "entity" in err.lower() or "parse" in err.lower():
            try:
                if itype == "text":
                    await bot.send_message(chat_id=CHAT_LINK, text=item.get("text",""))
                elif itype == "photo":
                    await bot.send_photo(chat_id=CHAT_LINK, photo=file_id, caption=caption)
                elif itype == "animation":
                    await bot.send_animation(chat_id=CHAT_LINK, animation=file_id, caption=caption)
                elif itype == "video":
                    await bot.send_video(chat_id=CHAT_LINK, video=file_id, caption=caption)
                elif itype == "document":
                    await bot.send_document(chat_id=CHAT_LINK, document=file_id, caption=caption)
                return True, None
            except Exception as e2:
                return False, str(e2)
        return False, err

async def _send_photo_to_group(msg, bot):
    """Gui anh/gif/video tu msg len CHAT_LINK"""
    cap_ent = list_to_entities(entities_to_list(msg.caption_entities))
    cap = msg.caption or ""
    try:
        if msg.animation:
            await bot.send_animation(chat_id=CHAT_LINK, animation=msg.animation.file_id,
                                     caption=cap, caption_entities=cap_ent)
        elif msg.photo:
            await bot.send_photo(chat_id=CHAT_LINK, photo=msg.photo[-1].file_id,
                                 caption=cap, caption_entities=cap_ent)
        elif msg.video:
            await bot.send_video(chat_id=CHAT_LINK, video=msg.video.file_id,
                                 caption=cap, caption_entities=cap_ent)
        elif msg.document:
            mime = msg.document.mime_type or ""
            if mime == "image/gif":
                await bot.send_animation(chat_id=CHAT_LINK, animation=msg.document.file_id,
                                         caption=cap, caption_entities=cap_ent)
            else:
                await bot.send_document(chat_id=CHAT_LINK, document=msg.document.file_id,
                                        caption=cap, caption_entities=cap_ent)
        else:
            return False
        return True
    except Exception as e:
        logger.error(f"_send_photo_to_group error: {e}")
        return False

# ==================== CORE SEND ====================

async def _send_key(n: int, u: Update, c: ContextTypes.DEFAULT_TYPE):
    """Gui lenh n len group (lenh thuong, khong can anh kem)"""
    data = load()
    item = data.get(f"key{n}")
    if not item:
        await u.message.reply_text(
            f"LENH {n} CHUA DUOC NAP!\nDung /nap{n} de nap.",
            reply_markup=bieu_dien_menu())
        return
    ok, err = await _send_item_to_group(item, c.bot)
    if ok:
        await u.message.reply_text(f"Da gui lenh {n} len group!", reply_markup=bieu_dien_menu())
    else:
        await u.message.reply_text(f"Loi gui lenh {n}: {err}", reply_markup=bieu_dien_menu())

# ==================== COMMAND HANDLERS ====================

async def start(u: Update, c: ContextTypes.DEFAULT_TYPE):
    uid = u.effective_user.id
    if not check_auth(uid):
        pending[uid] = ("login", None, None)
        await u.message.reply_text("Bot nay da bao mat! Nhap mat khau:",
                                   reply_markup=ReplyKeyboardRemove())
        return WAITING_PASS
    await u.message.reply_text(
        "He thong BOT LENH VIP san sang!\n\nNAP LENH: /nap1 den /nap18\nXEM: /xem\nGUI: Bam nut menu.",
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
        f"NAP LENH {n}:\nGui: Anh, GIF, Video, Sticker, File, Text.\n/cancel de huy.",
        reply_markup=ReplyKeyboardRemove())
    return WAITING

async def nap_receive(u: Update, c: ContextTypes.DEFAULT_TYPE):
    uid = u.effective_user.id
    if uid not in pending or pending[uid][0] != "nap":
        return ConversationHandler.END
    n = pending[uid][1]
    msg = u.message
    if msg.text and not msg.text.strip():
        await msg.reply_text("Text trong!", reply_markup=ReplyKeyboardRemove())
        return WAITING
    if msg.text and msg.text.strip().startswith("/") and msg.text.strip() != "/cancel":
        await msg.reply_text("Khong luu lenh /command.", reply_markup=bieu_dien_menu())
        del pending[uid]
        return ConversationHandler.END
    data = load()
    ok = save_message(data, n, msg)
    if not ok:
        await msg.reply_text("Dinh dang khong ho tro.", reply_markup=ReplyKeyboardRemove())
        return WAITING
    del pending[uid]
    save(data)
    item = data[f"key{n}"]
    itype = item.get("type", "?")
    if itype == "text":
        await msg.reply_text(
            f"Da luu lenh {n} (TEXT)!\n{item.get('text','')[:40]}",
            reply_markup=bieu_dien_menu())
    else:
        cap = item.get("caption", "")
        await msg.reply_text(
            f"Da luu lenh {n} ({itype.upper()})!\nCaption: {cap[:40] if cap else '(khong)'}",
            reply_markup=bieu_dien_menu())
    return ConversationHandler.END

async def gui_cmd(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not check_auth(u.effective_user.id):
        await u.message.reply_text("Chua xac thuc!")
        return
    n = int(u.message.text.strip().replace("/gui", ""))
    await _send_key(n, u, c)

async def doi_cmd(u: Update, c: ContextTypes.DEFAULT_TYPE):
    uid = u.effective_user.id
    if not check_auth(uid):
        await u.message.reply_text("Chua xac thuc!")
        return ConversationHandler.END
    n = int(u.message.text.strip().replace("/doi", ""))
    data = load()
    if f"key{n}" not in data:
        await u.message.reply_text(f"Lenh {n} chua nap! Dung /nap{n}.", reply_markup=bieu_dien_menu())
        return ConversationHandler.END
    pending[uid] = ("doi", n, None)
    item = data[f"key{n}"]
    itype = item.get("type", "?")
    await u.message.reply_text(
        f"DOI LENH {n} (hien tai: {itype}):\nGui noi dung moi.\n/cancel de huy.",
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
        await u.message.reply_text("Chua xac thuc!")
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
    tmp = {}
    ok = save_message(tmp, 0, msg)
    if not ok or "key0" not in tmp:
        await msg.reply_text("Dinh dang khong ho tro.", reply_markup=bieu_dien_menu())
        return ConversationHandler.END
    item = tmp["key0"]
    ok2, err = await _send_item_to_group(item, c.bot)
    if ok2:
        await msg.reply_text("Da gui tin nhan len group!", reply_markup=bieu_dien_menu())
    else:
        await msg.reply_text(f"Loi gui: {err}", reply_markup=bieu_dien_menu())
    return ConversationHandler.END

# ---------- LOGIC CHO LENH CAN ANH KEM (3, 8-15) ----------

async def gui_with_photo_cmd(u: Update, c: ContextTypes.DEFAULT_TYPE):
    """Xu ly khi bam nut lenh can anh kem: hoi user gui anh"""
    uid = u.effective_user.id
    n = pending[uid][1]  # lay n tu pending da duoc set boi button_handler
    data = load()
    if f"key{n}" not in data:
        await u.message.reply_text(
            f"LENH {n} CHUA DUOC NAP!\nDung /nap{n} de nap noi dung truoc.",
            reply_markup=bieu_dien_menu())
        del pending[uid]
        return ConversationHandler.END
    # Hoi user gui anh
    item = data[f"key{n}"]
    itype = item.get("type", "?")
    cap = item.get("caption", item.get("text", ""))
    await u.message.reply_text(
        f"LENH {n} SAN SANG ({itype.upper()}).\n"
        f"Gui ANH/GIF len de bot gui kem lenh nay len nhom.\n"
        f"/cancel de huy.",
        reply_markup=ReplyKeyboardRemove())
    return WAITING_PHOTO

async def photo_receive(u: Update, c: ContextTypes.DEFAULT_TYPE):
    """Nhan anh tu user, gui anh + lenh len nhom"""
    uid = u.effective_user.id
    if uid not in pending or pending[uid][0] != "gui_with_photo":
        return ConversationHandler.END
    n = pending[uid][1]
    del pending[uid]
    msg = u.message

    # Kiem tra phai la anh/gif/video
    has_media = (msg.photo or msg.animation or msg.video or
                 (msg.document and msg.document.mime_type and
                  "image" in msg.document.mime_type))
    if not has_media:
        await msg.reply_text(
            "Phai gui ANH hoac GIF! Thu lai hoac /cancel de huy.",
            reply_markup=ReplyKeyboardRemove())
        pending[uid] = ("gui_with_photo", n, None)
        return WAITING_PHOTO

    bot = c.bot
    errors = []

    # Buoc 1: Gui anh cua user len nhom
    ok1 = await _send_photo_to_group(msg, bot)
    if not ok1:
        errors.append("Loi gui anh")

    # Buoc 2: Gui lenh da nap len nhom
    data = load()
    item = data.get(f"key{n}")
    if item:
        ok2, err2 = await _send_item_to_group(item, bot)
        if not ok2:
            errors.append(f"Loi gui lenh {n}: {err2}")
    else:
        errors.append(f"Lenh {n} khong con trong data")

    if errors:
        await msg.reply_text(
            "Co loi: " + " | ".join(errors),
            reply_markup=bieu_dien_menu())
    else:
        await msg.reply_text(
            f"Da gui anh + lenh {n} len group!",
            reply_markup=bieu_dien_menu())
    return ConversationHandler.END

async def xem_lenh(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not check_auth(u.effective_user.id):
        await u.message.reply_text("Chua xac thuc!")
        return
    data = load()
    lines = ["DANH SACH LENH (1-18):"]
    for i in range(1, 19):
        key = f"key{i}"
        mark = " [*]" if i in WAIT_PHOTO_KEYS else ""
        if key in data:
            item = data[key]
            itype = item.get("type", "?")
            if itype == "text":
                preview = item.get("text", "")[:25]
                lines.append(f"{i:2d}{mark}: [TEXT] {preview}")
            else:
                cap = item.get("caption", "")
                lines.append(f"{i:2d}{mark}: [{itype.upper()}] {cap[:25] if cap else '(khong)'}")
        else:
            lines.append(f"{i:2d}{mark}: (CHUA NAP)")
    await u.message.reply_text(
        "\n".join(lines) + "\n\n[*] = can gui kem anh",
        reply_markup=bieu_dien_menu())

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
        # Kiem tra lenh co can anh kem khong
        if n in WAIT_PHOTO_KEYS:
            data = load()
            if f"key{n}" not in data:
                await u.message.reply_text(
                    f"LENH {n} CHUA DUOC NAP!\nDung /nap{n} de nap.",
                    reply_markup=bieu_dien_menu())
                return
            # Set pending va hoi user gui anh
            pending[uid] = ("gui_with_photo", n, None)
            item = data[f"key{n}"]
            itype = item.get("type", "?")
            await u.message.reply_text(
                f"LENH {n} ({itype.upper()}) SAN SANG.\n"
                f"GUI ANH/GIF len de bot gui kem len nhom ngay!\n"
                f"/cancel de huy.",
                reply_markup=ReplyKeyboardRemove())
        else:
            # Lenh thuong: gui ngay khong can anh
            await _send_key(n, u, c)
        return

    if cmd.startswith("doi"):
        n = int(cmd.replace("doi", ""))
        data = load()
        if f"key{n}" not in data:
            await u.message.reply_text(
                f"Lenh {n} chua nap! Dung /nap{n}.",
                reply_markup=bieu_dien_menu())
            return
        pending[uid] = ("doi", n, None)
        item = data[f"key{n}"]
        itype = item.get("type", "?")
        await u.message.reply_text(
            f"DOI LENH {n} (hien tai: {itype}):\nGui noi dung moi.\n/cancel de huy.",
            reply_markup=ReplyKeyboardRemove())
        return

# ==================== MAIN ====================

def main():
    app = Application.builder().token(TOKEN).build()

    all_media = filters.ALL & ~filters.COMMAND
    photo_media = (filters.PHOTO | filters.ANIMATION | filters.VIDEO |
                   filters.Document.IMAGE | filters.Document.MimeType("image/gif"))

    auth_conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={WAITING_PASS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_password)]},
        fallbacks=[CommandHandler("cancel", cancel)],
        per_user=True, allow_reentry=True,
    )

    nap_conv = ConversationHandler(
        entry_points=[CommandHandler(f"nap{i}", nap_cmd) for i in range(1, 19)],
        states={WAITING: [MessageHandler(all_media, nap_receive)]},
        fallbacks=[CommandHandler("cancel", cancel)],
        per_user=True, allow_reentry=True,
    )

    doi_conv = ConversationHandler(
        entry_points=[CommandHandler(f"doi{i}", doi_cmd) for i in range(1, 19)],
        states={WAITING: [MessageHandler(all_media, doi_receive)]},
        fallbacks=[CommandHandler("cancel", cancel)],
        per_user=True, allow_reentry=True,
    )

    all_conv = ConversationHandler(
        entry_points=[CommandHandler("all", all_cmd)],
        states={WAITING: [MessageHandler(all_media, all_receive)]},
        fallbacks=[CommandHandler("cancel", cancel)],
        per_user=True, allow_reentry=True,
    )

    # Conversation cho lenh can anh kem (3, 8-15)
    # Entry point la button_handler (set pending roi return), state WAITING_PHOTO nhan anh
    # Dung MessageHandler bat tat ca - check pending state trong handler
    photo_conv = ConversationHandler(
        entry_points=[],  # Entry duoc xu ly qua button_handler
        states={
            WAITING_PHOTO: [
                MessageHandler(photo_media & ~filters.COMMAND, photo_receive),
                MessageHandler(filters.TEXT & ~filters.COMMAND, photo_receive),
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_user=True, allow_reentry=True,
    )

    import re
    btn_labels = list(BUTTON_MAP.keys())
    escaped = [re.escape(b) for b in btn_labels]
    btn_pattern = "^(" + "|".join(escaped) + ")$"

    # Button handler xu ly tat ca nut, bao gom viec set state cho photo_conv
    app.add_handler(MessageHandler(filters.Regex(btn_pattern), button_handler))

    app.add_handler(auth_conv)
    app.add_handler(nap_conv)
    app.add_handler(doi_conv)
    app.add_handler(all_conv)

    # Handler cho viec nhan anh sau khi button_handler set pending gui_with_photo
    app.add_handler(MessageHandler(
        (photo_media | (filters.TEXT & ~filters.COMMAND)) & ~filters.Regex(btn_pattern),
        _photo_or_text_router
    ))

    for i in range(1, 19):
        app.add_handler(CommandHandler(f"gui{i}", gui_cmd))
    app.add_handler(CommandHandler("xem", xem_lenh))

    logger.info("Bot dang chay...")
    app.run_polling(drop_pending_updates=True)

async def _photo_or_text_router(u: Update, c: ContextTypes.DEFAULT_TYPE):
    """Router: neu pending la gui_with_photo thi xu ly nhan anh, con lai bo qua"""
    uid = u.effective_user.id
    if uid in pending and pending[uid][0] == "gui_with_photo":
        await photo_receive(u, c)

if __name__ == "__main__":
    main()
