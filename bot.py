import os
import json
import logging
import base64
import requests
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, MessageEntity
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("BOT_TOKEN", "8877176302:AAETTH8e3LWY0BL3pHsOpUo4huAQjzOq2bg")
CHAT_LINK = "-1003617964607"
BOT_PASSWORD = os.environ.get("BOT_PASSWORD", "HARRY2005TDZ")
RAILWAY_API_TOKEN = os.environ.get("RAILWAY_API_TOKEN", "")
RAILWAY_SERVICE_ID = os.environ.get("RAILWAY_SERVICE_ID", "13ebf69b-680a-44d2-a905-ce4ef7803993")
RAILWAY_ENVIRONMENT_ID = os.environ.get("RAILWAY_ENVIRONMENT_ID", "33dea9d1-8da0-40b1-9569-dc64580a4f0d")
RAILWAY_PROJECT_ID = os.environ.get("RAILWAY_PROJECT_ID", "83626a22-0f63-4b60-8411-f0f1a0059f46")

SAFE_ENTITY_TYPES = {"bold", "italic", "underline", "strikethrough", "spoiler", "code", "pre", "text_link", "mention", "hashtag", "cashtag", "bot_command", "url", "email", "phone_number"}

WAIT_PHOTO_KEYS = {3, 8, 9, 10, 11, 12, 13, 14, 15}
# STORAGE

def _rget():
    if not RAILWAY_API_TOKEN:
        return None
    q = "query variables($p: String!, $s: String!, $e: String!) { variables(projectId: $p, serviceId: $s, environmentId: $e) }"
    r = requests.post("https://backboard.railway.com/graphql/v2", json={"query": q, "variables": {"p": RAILWAY_PROJECT_ID, "s": RAILWAY_SERVICE_ID, "e": RAILWAY_ENVIRONMENT_ID}}, headers={"Authorization": f"Bearer {RAILWAY_API_TOKEN}", "Content-Type": "application/json"}, timeout=15)
    d = r.json()
    logger.info(f"Railway GET: {str(d)[:100]}")
    return d.get("data", {}).get("variables", {}).get("BOT_DATA", None)

def _rset(encoded):
    if not RAILWAY_API_TOKEN:
        logger.warning("No RAILWAY_API_TOKEN!")
        return False
    m = "mutation variableUpsert($i: VariableUpsertInput!) { variableUpsert(input: $i) }"
    r = requests.post("https://backboard.railway.com/graphql/v2", json={"query": m, "variables": {"i": {"projectId": RAILWAY_PROJECT_ID, "serviceId": RAILWAY_SERVICE_ID, "environmentId": RAILWAY_ENVIRONMENT_ID, "name": "BOT_DATA", "value": encoded}}}, headers={"Authorization": f"Bearer {RAILWAY_API_TOKEN}", "Content-Type": "application/json"}, timeout=15)
    result = r.json()
    logger.info(f"Railway SET: {str(result)[:100]}")
    return not bool(result.get("errors"))

def load():
    raw = os.environ.get("BOT_DATA", "")
    if not raw:
        logger.info("Fetching BOT_DATA from Railway...")
        raw = _rget() or ""
        if raw:
            os.environ["BOT_DATA"] = raw
            logger.info("BOT_DATA loaded OK")
    if raw:
        return json.loads(base64.b64decode(raw).decode("utf-8"))
    return {}

def save(data):
    encoded = base64.b64encode(json.dumps(data, ensure_ascii=False).encode()).decode()
    os.environ["BOT_DATA"] = encoded
    ok = _rset(encoded)
    if not ok:
        logger.error("Railway save FAILED!")

# AUTH

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

# MENU

def menu():
    return ReplyKeyboardMarkup([
        ["CHUAN BI", "LEN CA", "BAO BAN", "CHO LENH", "BAT DAU"],
        ["CON 10%", "CAI 10%", "HUP + 10%", "GAY - 10%", "HUP + 5%"],
        ["GAY - 5%", "HUP - 5%", "GAY - 15%", "GAY + 5%", "HOA + 00"],
        ["XUONG CA", "SU KIEN", "KHUYEN MAI"],
        ["GUI TIN NHAN NHANH"],
    ], resize_keyboard=True, one_time_keyboard=False)

BUTTON_MAP = {
    "CHUAN BI": "gui1", "LEN CA": "gui2", "BAO BAN": "gui3",
    "CHO LENH": "gui4", "BAT DAU": "gui5", "CON 10%": "gui6",
    "CAI 10%": "gui7", "HUP + 10%": "gui8", "GAY - 10%": "gui9",
    "HUP + 5%": "gui10", "GAY - 5%": "gui11", "HUP - 5%": "gui12",
    "GAY - 15%": "gui13", "GAY + 5%": "gui14", "HOA + 00": "gui15",
    "XUONG CA": "gui16", "SU KIEN": "gui17", "KHUYEN MAI": "gui18",
    "GUI TIN NHAN NHANH": "all",
}

# ENTITY HELPERS

def ents2list(entities):
    if not entities:
        return []
    res = []
    for e in entities:
        if e.type not in SAFE_ENTITY_TYPES:
            continue
        d = {"type": e.type, "offset": e.offset, "length": e.length}
        if e.type == "text_link" and e.url:
            d["url"] = e.url
        res.append(d)
    return res

def list2ents(lst):
    res = []
    for d in (lst or []):
        res.append(MessageEntity(type=d["type"], offset=d["offset"], length=d["length"], url=d.get("url")))
    return res

def fix_cap_ents(text, ents_list):
    if not ents_list or not text:
        return []
    tlen = len(text)
    res = []
    for d in ents_list:
        if d["offset"] >= tlen:
            continue
        nd = dict(d)
        if d["offset"] + d["length"] > tlen:
            nd["length"] = tlen - d["offset"]
        if nd["length"] > 0:
            res.append(nd)
    return res

def get_lenh_caption(item):
    if not item:
        return None, []
    t = item.get("type", "text")
    if t == "text":
        return item.get("text", ""), item.get("entities", [])
    return item.get("caption", ""), item.get("caption_entities", [])

# SEND

async def send_item(item, bot, chat_id=CHAT_LINK):
    t = item.get("type", "text")
    if t == "text":
        txt = item.get("text", "")
        ents = list2ents(item.get("entities", []))
        await bot.send_message(chat_id=chat_id, text=txt, entities=ents or None)
    elif t == "photo":
        cap = item.get("caption") or None
        ents = list2ents(item.get("caption_entities", [])) or None
        await bot.send_photo(chat_id=chat_id, photo=item["file_id"], caption=cap, caption_entities=ents)
    elif t == "animation":
        cap = item.get("caption") or None
        ents = list2ents(item.get("caption_entities", [])) or None
        await bot.send_animation(chat_id=chat_id, animation=item["file_id"], caption=cap, caption_entities=ents)
    elif t == "video":
        cap = item.get("caption") or None
        ents = list2ents(item.get("caption_entities", [])) or None
        await bot.send_video(chat_id=chat_id, video=item["file_id"], caption=cap, caption_entities=ents)
    elif t == "sticker":
        await bot.send_sticker(chat_id=chat_id, sticker=item["file_id"])
    elif t == "document":
        cap = item.get("caption") or None
        ents = list2ents(item.get("caption_entities", [])) or None
        await bot.send_document(chat_id=chat_id, document=item["file_id"], caption=cap, caption_entities=ents)
    elif t == "voice":
        await bot.send_voice(chat_id=chat_id, voice=item["file_id"])
    elif t == "video_note":
        await bot.send_video_note(chat_id=chat_id, video_note=item["file_id"])

async def send_photo_with_cap(user_msg, cap_text, cap_ents_list, bot, chat_id=CHAT_LINK):
    cap = cap_text or None
    ents = list2ents(fix_cap_ents(cap_text or "", cap_ents_list)) if cap_ents_list else None
    if not ents:
        ents = None
    msg = user_msg
    if msg.photo:
        await bot.send_photo(chat_id=chat_id, photo=msg.photo[-1].file_id, caption=cap, caption_entities=ents)
    elif msg.animation:
        await bot.send_animation(chat_id=chat_id, animation=msg.animation.file_id, caption=cap, caption_entities=ents)
    elif msg.video:
        await bot.send_video(chat_id=chat_id, video=msg.video.file_id, caption=cap, caption_entities=ents)
    elif msg.document:
        await bot.send_document(chat_id=chat_id, document=msg.document.file_id, caption=cap, caption_entities=ents)
    elif msg.sticker:
        await bot.send_sticker(chat_id=chat_id, sticker=msg.sticker.file_id)
        if cap:
            await bot.send_message(chat_id=chat_id, text=cap, entities=ents)
    else:
        if cap:
            await bot.send_message(chat_id=chat_id, text=cap, entities=ents)

# HANDLERS

async def start(u: Update, c: ContextTypes.DEFAULT_TYPE):
    uid = u.effective_user.id
    if check_auth(uid):
        await u.message.reply_text("Bot san sang!", reply_markup=menu())
        return
    pending[uid] = {"action": "pass"}
    await u.message.reply_text("Nhap mat khau:")

async def xem(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not check_auth(u.effective_user.id):
        return
    data = load()
    lines = []
    for i in range(1, 19):
        key = f"key{i}"
        if key in data:
            item = data[key]
            t = item.get("type", "?")
            preview = (item.get("text") or item.get("caption") or f"[{t}]")[:40]
            lines.append(f"Lenh {i} ({t}): {preview}")
        else:
            lines.append(f"Lenh {i}: CHUA NAP")
    await u.message.reply_text("\n".join(lines))

async def nap_cmd(u: Update, c: ContextTypes.DEFAULT_TYPE):
    uid = u.effective_user.id
    if not check_auth(uid):
        await u.message.reply_text("Chua dang nhap. Dung /start")
        return
    txt = (u.message.text or "").strip()
    try:
        n = int(txt.replace("/nap", ""))
        assert 1 <= n <= 18
    except Exception:
        await u.message.reply_text("Dung /nap1 den /nap18")
        return
    pending[uid] = {"action": "nap", "n": n}
    await u.message.reply_text(f"NAP LENH {n}:\nGui: Anh, GIF, Video, Sticker, File, Text.\n/cancel de huy.", reply_markup=ReplyKeyboardRemove())

async def cancel(u: Update, c: ContextTypes.DEFAULT_TYPE):
    uid = u.effective_user.id
    pending.pop(uid, None)
    await u.message.reply_text("Da huy.", reply_markup=menu())

async def universal_handler(u: Update, c: ContextTypes.DEFAULT_TYPE):
    uid = u.effective_user.id
    msg = u.message
    txt = (msg.text or "").strip()
    info = pending.get(uid)

    if info:
        action = info.get("action")

        if action == "pass":
            if txt == BOT_PASSWORD:
                authenticated_users.add(uid)
                save_auth()
                pending.pop(uid, None)
                await msg.reply_text("Dang nhap thanh cong!", reply_markup=menu())
            else:
                await msg.reply_text("Sai mat khau. Thu lai:")
            return

        if action == "nap":
            n = info.get("n")
            data = load()
            key = f"key{n}"
            if msg.photo:
                fid = msg.photo[-1].file_id
                cap = msg.caption or ""
                ents = ents2list(msg.caption_entities)
                data[key] = {"type": "photo", "file_id": fid, "caption": cap, "caption_entities": ents}
                await msg.reply_text(f"Da luu lenh {n} (PHOTO)!\nCaption: {cap[:50]}", reply_markup=menu())
            elif msg.animation:
                fid = msg.animation.file_id
                cap = msg.caption or ""
                ents = ents2list(msg.caption_entities)
                data[key] = {"type": "animation", "file_id": fid, "caption": cap, "caption_entities": ents}
                await msg.reply_text(f"Da luu lenh {n} (GIF)!\nCaption: {cap[:50]}", reply_markup=menu())
            elif msg.video:
                fid = msg.video.file_id
                cap = msg.caption or ""
                ents = ents2list(msg.caption_entities)
                data[key] = {"type": "video", "file_id": fid, "caption": cap, "caption_entities": ents}
                await msg.reply_text(f"Da luu lenh {n} (VIDEO)!\nCaption: {cap[:50]}", reply_markup=menu())
            elif msg.sticker:
                data[key] = {"type": "sticker", "file_id": msg.sticker.file_id}
                await msg.reply_text(f"Da luu lenh {n} (STICKER)!", reply_markup=menu())
            elif msg.document:
                fid = msg.document.file_id
                cap = msg.caption or ""
                ents = ents2list(msg.caption_entities)
                data[key] = {"type": "document", "file_id": fid, "caption": cap, "caption_entities": ents}
                await msg.reply_text(f"Da luu lenh {n} (FILE)!\nCaption: {cap[:50]}", reply_markup=menu())
            elif msg.voice:
                data[key] = {"type": "voice", "file_id": msg.voice.file_id}
                await msg.reply_text(f"Da luu lenh {n} (VOICE)!", reply_markup=menu())
            elif msg.video_note:
                data[key] = {"type": "video_note", "file_id": msg.video_note.file_id}
                await msg.reply_text(f"Da luu lenh {n} (VIDEO NOTE)!", reply_markup=menu())
            elif msg.text and not msg.text.startswith("/"):
                ents = ents2list(msg.entities)
                data[key] = {"type": "text", "text": msg.text, "entities": ents}
                await msg.reply_text(f"Da luu lenh {n} (TEXT)!\n{msg.text[:50]}", reply_markup=menu())
            else:
                await msg.reply_text("Khong nhan duoc. Thu lai. /cancel de huy.")
                return
            pending.pop(uid, None)
            save(data)
            return

        if action == "gui_with_photo":
            n = info.get("n")
            data = load()
            key = f"key{n}"
            if key not in data:
                await msg.reply_text(f"LENH {n} CHUA NAP! Dung /nap{n} truoc.", reply_markup=menu())
                pending.pop(uid, None)
                return
            item = data[key]
            cap_text, cap_ents = get_lenh_caption(item)
            try:
                await send_photo_with_cap(msg, cap_text, cap_ents, c.bot)
                await msg.reply_text(f"Da gui lenh {n} (anh+lenh) len group!", reply_markup=menu())
            except Exception as e:
                logger.error(f"Send photo+lenh {n}: {e}")
                await msg.reply_text(f"Loi gui lenh {n}: {e}", reply_markup=menu())
            pending.pop(uid, None)
            return

    if not check_auth(uid):
        return
    if not txt:
        return
    action = BUTTON_MAP.get(txt)
    if not action:
        return

    if action == "all":
        data = load()
        ok = fail = 0
        for i in range(1, 19):
            key = f"key{i}"
            if key in data:
                try:
                    await send_item(data[key], c.bot)
                    ok += 1
                except Exception as e:
                    logger.error(f"Send all {i}: {e}")
                    fail += 1
        await msg.reply_text(f"Da gui {ok} lenh. Loi: {fail}")
        return

    if action.startswith("gui"):
        n = int(action.replace("gui", ""))
        if n in WAIT_PHOTO_KEYS:
            data = load()
            key = f"key{n}"
            if key not in data:
                await msg.reply_text(f"LENH {n} CHUA NAP!\nDung /nap{n} de nap truoc.")
                return
            pending[uid] = {"action": "gui_with_photo", "n": n}
            await msg.reply_text(f"GUI ANH/GIF len de bot gui kem lenh {n} len nhom (1 tin nhan)!\n/cancel de huy.", reply_markup=ReplyKeyboardRemove())
        else:
            data = load()
            key = f"key{n}"
            if key not in data:
                await msg.reply_text(f"LENH {n} CHUA NAP!\nDung /nap{n} de nap.")
                return
            try:
                await send_item(data[key], c.bot)
                await msg.reply_text(f"Da gui lenh {n} ({data[key].get('type','?')}) len group!")
            except Exception as e:
                logger.error(f"Send key{n}: {e}")
                await msg.reply_text(f"Loi gui lenh {n}: {e}")
        return

# MAIN

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("xem", xem))
    app.add_handler(CommandHandler("cancel", cancel))
    for i in range(1, 19):
        app.add_handler(CommandHandler(f"nap{i}", nap_cmd))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, universal_handler))
    logger.info("Bot starting, token set: " + str(bool(RAILWAY_API_TOKEN)))
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
