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

SAFE_ENTITY_TYPES = {
    "bold", "italic", "underline", "strikethrough", "spoiler",
    "code", "pre", "text_link", "mention", "hashtag", "cashtag",
    "bot_command", "url", "email", "phone_number",
}

# Lenh 3 va 8-15: khi bam nut, cho user gui anh,
# roi gop anh do + caption lenh thanh 1 tin duy nhat gui len nhom
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
            except Exception as e:
                logger.error(f"Railway API error: {e}")
    except Exception as e:
        logger.error(f"Save error: {e}")

WAITING = 1
WAITING_PASS = 99
WAITING_PHOTO = 2
pending = {}

def load_auth():
    return set(load().get("_auth", []))

authenticated_users = load_auth()

def save_auth():
    data = load()
    data["_auth"] = list(authenticated_users)
    save(data)

def check_auth(uid):
    return uid in authenticated_users

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
    'CHUAN BI':   'gui1',  'LEN CA':     'gui2',  'BAO BAN':    'gui3',
    'CHO LENH':   'gui4',  'BAT DAU':    'gui5',  'CON 10%':    'gui6',
    'CAI 10%':    'gui7',  'HUP + 10%':  'gui8',  'GAY - 10%':  'gui9',
    'HUP + 5%':   'gui10', 'GAY - 5%':   'gui11', 'HUP - 5%':   'gui12',
    'GAY - 15%':  'gui13', 'GAY + 5%':   'gui14', 'HOA + 00':   'gui15',
    'XUONG CA':   'gui16', 'SU KIEN':    'gui17', 'KHUYEN MAI': 'gui18',
    'GUI TIN NHAN NHANH': 'all',
    'DOI CHUAN BI': 'doi1', 'DOI LEN CA': 'doi2', 'DOI CHO LENH': 'doi4',
    'DOI BAT DAU': 'doi5',  'DOI CON 10%': 'doi6', 'DOI CAI 10%': 'doi7',
    'DOI XUONG CA': 'doi16','DOI SU KIEN': 'doi17','DOI KHUYEN MAI': 'doi18',
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
    result = []
    for d in lst:
        if d.get("type") not in SAFE_ENTITY_TYPES:
            continue
        result.append(MessageEntity(
            type=d["type"], offset=d["offset"], length=d["length"],
            url=d.get("url"), language=d.get("language"),
        ))
    return result if result else None

def save_message(data, n, msg):
    caption = msg.caption or ""
    cap_ent = entities_to_list(msg.caption_entities)
    if msg.animation:
        data[f"key{n}"] = {"type": "animation", "file_id": msg.animation.file_id,
                           "caption": caption, "cap_entities": cap_ent}
        return True
    if msg.photo:
        data[f"key{n}"] = {"type": "photo", "file_id": msg.photo[-1].file_id,
                           "caption": caption, "cap_entities": cap_ent}
        return True
    if msg.video:
        data[f"key{n}"] = {"type": "video", "file_id": msg.video.file_id,
                           "caption": caption, "cap_entities": cap_ent}
        return True
    if msg.sticker:
        data[f"key{n}"] = {"type": "sticker", "file_id": msg.sticker.file_id}
        return True
    if msg.document:
        mime = msg.document.mime_type or ""
        itype = "animation" if mime == "image/gif" else "document"
        data[f"key{n}"] = {"type": itype, "file_id": msg.document.file_id,
                           "caption": caption, "cap_entities": cap_ent}
        return True
    if msg.voice:
        data[f"key{n}"] = {"type": "voice", "file_id": msg.voice.file_id,
                           "caption": caption, "cap_entities": cap_ent}
        return True
    if msg.video_note:
        data[f"key{n}"] = {"type": "video_note", "file_id": msg.video_note.file_id}
        return True
    if msg.text:
        data[f"key{n}"] = {"type": "text", "text": msg.text,
                           "entities": entities_to_list(msg.entities)}
        return True
    return False

def get_caption_text(item):
    """Lay text caption/noi dung tu lenh da nap de dung lam caption cho anh"""
    itype = item.get("type", "")
    if itype == "text":
        return item.get("text", ""), list_to_entities(item.get("entities", []))
    else:
        cap = item.get("caption", "") or ""
        cap_ent = list_to_entities(item.get("cap_entities", []))
        return cap, cap_ent

async def _send_item_to_group(item, bot):
    """Gui item (khong kem anh ngoai) len nhom"""
    itype = item.get("type", "")
    caption = item.get("caption", "") or ""
    file_id = item.get("file_id", "")
    cap_ent = list_to_entities(item.get("cap_entities", []))
    try:
        if itype == "text":
            txt_ent = list_to_entities(item.get("entities", []))
            await bot.send_message(chat_id=CHAT_LINK, text=item.get("text",""), entities=txt_ent)
        elif itype == "photo":
            await bot.send_photo(chat_id=CHAT_LINK, photo=file_id,
                                 caption=caption, caption_entities=cap_ent)
        elif itype == "animation":
            await bot.send_animation(chat_id=CHAT_LINK, animation=file_id,
                                     caption=caption, caption_entities=cap_ent)
        elif itype == "video":
            await bot.send_video(chat_id=CHAT_LINK, video=file_id,
                                 caption=caption, caption_entities=cap_ent)
        elif itype == "sticker":
            await bot.send_sticker(chat_id=CHAT_LINK, sticker=file_id)
        elif itype == "document":
            await bot.send_document(chat_id=CHAT_LINK, document=file_id,
                                    caption=caption, caption_entities=cap_ent)
        elif itype == "voice":
            await bot.send_voice(chat_id=CHAT_LINK, voice=file_id,
                                 caption=caption, caption_entities=cap_ent)
        elif itype == "video_note":
            await bot.send_video_note(chat_id=CHAT_LINK, video_note=file_id)
        else:
            return False, f"Dinh dang {itype} khong ro"
        return True, None
    except Exception as e:
        err = str(e)
        if "entity" in err.lower() or "parse" in err.lower():
            try:
                if itype == "text":
                    await bot.send_message(chat_id=CHAT_LINK, text=item.get("text",""))
                elif itype in ("photo","animation","video","document"):
                    method = getattr(bot, f"send_{itype}")
                    await method(chat_id=CHAT_LINK, **{itype: file_id}, caption=caption)
                return True, None
            except Exception as e2:
                return False, str(e2)
        return False, err

async def _send_photo_with_caption(user_msg, caption, caption_entities, bot):
    """
    Gui ANH cua user len nhom, dung caption tu lenh da nap.
    Day la 1 tin nhan duy nhat: anh + caption.
    """
    cap_ent = caption_entities  # entities tu lenh da nap

    try:
        if user_msg.animation:
            await bot.send_animation(
                chat_id=CHAT_LINK,
                animation=user_msg.animation.file_id,
                caption=caption,
                caption_entities=cap_ent)
        elif user_msg.photo:
            await bot.send_photo(
                chat_id=CHAT_LINK,
                photo=user_msg.photo[-1].file_id,
                caption=caption,
                caption_entities=cap_ent)
        elif user_msg.video:
            await bot.send_video(
                chat_id=CHAT_LINK,
                video=user_msg.video.file_id,
                caption=caption,
                caption_entities=cap_ent)
        elif user_msg.document:
            mime = user_msg.document.mime_type or ""
            if mime == "image/gif":
                await bot.send_animation(
                    chat_id=CHAT_LINK,
                    animation=user_msg.document.file_id,
                    caption=caption,
                    caption_entities=cap_ent)
            else:
                await bot.send_photo(
                    chat_id=CHAT_LINK,
                    photo=user_msg.document.file_id,
                    caption=caption,
                    caption_entities=cap_ent)
        else:
            return False, "Tin nhan khong co anh/gif/video"
        return True, None
    except Exception as e:
        err = str(e)
        # Thu lai khong entity neu loi
        if "entity" in err.lower() or "parse" in err.lower():
            try:
                if user_msg.animation:
                    await bot.send_animation(chat_id=CHAT_LINK,
                                             animation=user_msg.animation.file_id, caption=caption)
                elif user_msg.photo:
                    await bot.send_photo(chat_id=CHAT_LINK,
                                         photo=user_msg.photo[-1].file_id, caption=caption)
                elif user_msg.video:
                    await bot.send_video(chat_id=CHAT_LINK,
                                         video=user_msg.video.file_id, caption=caption)
                return True, None
            except Exception as e2:
                return False, str(e2)
        return False, err

# ==================== COMMAND HANDLERS ====================

async def start(u: Update, c: ContextTypes.DEFAULT_TYPE):
    uid = u.effective_user.id
    if not check_auth(uid):
        pending[uid] = ("login", None, None)
        await u.message.reply_text("Bot nay da bao mat! Nhap mat khau:",
                                   reply_markup=ReplyKeyboardRemove())
        return WAITING_PASS
    await u.message.reply_text(
        "BOT LENH VIP san sang!\nNAP: /nap1-/nap18 | XEM: /xem | GUI: Bam nut menu.",
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
    pending.pop(u.effective_user.id, None)
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
        await msg.reply_text(f"Da luu lenh {n} (TEXT)!\n{item.get('text','')[:40]}", reply_markup=bieu_dien_menu())
    else:
        cap = item.get("caption", "")
        await msg.reply_text(f"Da luu lenh {n} ({itype.upper()})!\nCaption: {cap[:40] if cap else '(khong)'}", reply_markup=bieu_dien_menu())
    return ConversationHandler.END

async def gui_cmd(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not check_auth(u.effective_user.id):
        await u.message.reply_text("Chua xac thuc!")
        return
    n = int(u.message.text.strip().replace("/gui", ""))
    data = load()
    item = data.get(f"key{n}")
    if not item:
        await u.message.reply_text(f"LENH {n} CHUA NAP! Dung /nap{n}.", reply_markup=bieu_dien_menu())
        return
    ok, err = await _send_item_to_group(item, c.bot)
    if ok:
        await u.message.reply_text(f"Da gui lenh {n} len group!", reply_markup=bieu_dien_menu())
    else:
        await u.message.reply_text(f"Loi: {err}", reply_markup=bieu_dien_menu())

async def doi_cmd(u: Update, c: ContextTypes.DEFAULT_TYPE):
    uid = u.effective_user.id
    if not check_auth(uid):
        await u.message.reply_text("Chua xac thuc!")
        return ConversationHandler.END
    n = int(u.message.text.strip().replace("/doi", ""))
    data = load()
    if f"key{n}" not in data:
        await u.message.reply_text(f"Lenh {n} chua nap!", reply_markup=bieu_dien_menu())
        return ConversationHandler.END
    pending[uid] = ("doi", n, None)
    item = data[f"key{n}"]
    await u.message.reply_text(
        f"DOI LENH {n} ({item.get('type','?').upper()}):\nGui noi dung moi.\n/cancel de huy.",
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
    ok2, err = await _send_item_to_group(tmp["key0"], c.bot)
    if ok2:
        await msg.reply_text("Da gui tin nhan len group!", reply_markup=bieu_dien_menu())
    else:
        await msg.reply_text(f"Loi gui: {err}", reply_markup=bieu_dien_menu())
    return ConversationHandler.END

# ---- LENH CAN ANH KEM (3, 8-15): nhan anh user + gop caption lenh thanh 1 tin ----

async def photo_with_lenh_receive(u: Update, c: ContextTypes.DEFAULT_TYPE):
    """
    Nhan anh tu user.
    Gui 1 tin nhan duy nhat len nhom = ANH USER + CAPTION tu lenh da nap.
    """
    uid = u.effective_user.id
    if uid not in pending or pending[uid][0] != "gui_with_photo":
        return ConversationHandler.END

    n = pending[uid][1]
    del pending[uid]
    msg = u.message

    # Kiem tra co anh/gif/video khong
    has_media = (msg.photo or msg.animation or msg.video or msg.document)
    if not has_media:
        await msg.reply_text(
            "Phai gui ANH hoac GIF! Thu lai hoac /cancel de huy.",
            reply_markup=ReplyKeyboardRemove())
        # Set lai pending de doi tiep
        pending[uid] = ("gui_with_photo", n, None)
        return WAITING_PHOTO

    # Lay caption/noi dung tu lenh da nap
    data = load()
    item = data.get(f"key{n}")
    if not item:
        await msg.reply_text(f"Lenh {n} khong con! Nap lai bang /nap{n}.", reply_markup=bieu_dien_menu())
        return ConversationHandler.END

    # Lay caption text va entities tu lenh da nap
    caption_text, caption_entities = get_caption_text(item)

    # Gui 1 tin nhan: anh user + caption = noi dung lenh
    ok, err = await _send_photo_with_caption(msg, caption_text, caption_entities, c.bot)
    if ok:
        await msg.reply_text(f"Da gui anh + lenh {n} len group!", reply_markup=bieu_dien_menu())
    else:
        await msg.reply_text(f"Loi gui: {err}", reply_markup=bieu_dien_menu())
    return ConversationHandler.END

async def xem_lenh(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not check_auth(u.effective_user.id):
        await u.message.reply_text("Chua xac thuc!")
        return
    data = load()
    lines = ["DANH SACH LENH (1-18):"]
    for i in range(1, 19):
        mark = "[*] " if i in WAIT_PHOTO_KEYS else "    "
        key = f"key{i}"
        if key in data:
            item = data[key]
            itype = item.get("type", "?")
            if itype == "text":
                lines.append(f"{i:2d}: {mark}[TEXT] {item.get('text','')[:25]}")
            else:
                cap = item.get("caption", "")
                lines.append(f"{i:2d}: {mark}[{itype.upper()}] {cap[:25] if cap else '(khong caption)'}")
        else:
            lines.append(f"{i:2d}: {mark}(CHUA NAP)")
    await u.message.reply_text("\n".join(lines) + "\n\n[*] = gui kem anh", reply_markup=bieu_dien_menu())

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
        if n in WAIT_PHOTO_KEYS:
            # Kiem tra lenh da nap chua
            data = load()
            if f"key{n}" not in data:
                await u.message.reply_text(
                    f"LENH {n} CHUA DUOC NAP!\nDung /nap{n} de nap truoc.",
                    reply_markup=bieu_dien_menu())
                return
            item = data[f"key{n}"]
            caption_text, _ = get_caption_text(item)
            preview = caption_text[:50] + "..." if len(caption_text) > 50 else caption_text
            # Set pending va hoi anh
            pending[uid] = ("gui_with_photo", n, None)
            await u.message.reply_text(
                f"Lenh {n} ({item.get('type','?').upper()}): {preview}\n\n"
                f"GUI ANH/GIF len de bot gui kem noi dung tren len nhom (1 tin nhan)!\n"
                f"/cancel de huy.",
                reply_markup=ReplyKeyboardRemove())
        else:
            # Gui ngay khong can anh
            data = load()
            item = data.get(f"key{n}")
            if not item:
                await u.message.reply_text(
                    f"LENH {n} CHUA DUOC NAP!\nDung /nap{n}.",
                    reply_markup=bieu_dien_menu())
                return
            ok, err = await _send_item_to_group(item, c.bot)
            if ok:
                await u.message.reply_text(f"Da gui lenh {n} len group!", reply_markup=bieu_dien_menu())
            else:
                await u.message.reply_text(f"Loi: {err}", reply_markup=bieu_dien_menu())
        return

    if cmd.startswith("doi"):
        n = int(cmd.replace("doi", ""))
        data = load()
        if f"key{n}" not in data:
            await u.message.reply_text(f"Lenh {n} chua nap! Dung /nap{n}.", reply_markup=bieu_dien_menu())
            return
        pending[uid] = ("doi", n, None)
        item = data[f"key{n}"]
        await u.message.reply_text(
            f"DOI LENH {n} ({item.get('type','?').upper()}):\nGui noi dung moi.\n/cancel de huy.",
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
    # Conversation cho lenh 3,8-15: doi anh roi gop vao 1 tin gui nhom
    photo_lenh_conv = ConversationHandler(
        entry_points=[],
        states={WAITING_PHOTO: [
            MessageHandler(photo_media & ~filters.COMMAND, photo_with_lenh_receive),
            MessageHandler(filters.TEXT & ~filters.COMMAND, photo_with_lenh_receive),
        ]},
        fallbacks=[CommandHandler("cancel", cancel)],
        per_user=True, allow_reentry=True,
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

    # Handler nhan anh cho lenh 3,8-15
    app.add_handler(MessageHandler(
        (photo_media | (filters.TEXT & ~filters.COMMAND)) & ~filters.Regex(btn_pattern),
        _router_photo_lenh
    ))

    for i in range(1, 19):
        app.add_handler(CommandHandler(f"gui{i}", gui_cmd))
    app.add_handler(CommandHandler("xem", xem_lenh))

    logger.info("Bot dang chay...")
    app.run_polling(drop_pending_updates=True)

async def _router_photo_lenh(u: Update, c: ContextTypes.DEFAULT_TYPE):
    """Router: neu dang cho anh cho lenh thi xu ly, con lai bo qua"""
    uid = u.effective_user.id
    if uid in pending and pending[uid][0] == "gui_with_photo":
        await photo_with_lenh_receive(u, c)

if __name__ == "__main__":
    main()
