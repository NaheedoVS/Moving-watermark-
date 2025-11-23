import os
import asyncio
import uuid
import tempfile
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.handlers import RawUpdateHandler
from pyrogram.raw.types import UpdateShortSent
from dotenv import load_dotenv
from utils import get_user_settings, set_user_settings
from ffmpeg_helper import add_watermark_video
from pdf_helper import add_watermark_to_pdf
from flask import Flask, request, jsonify

load_dotenv()

# === ENV ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH")
HEROKU_APP_NAME = os.getenv("HEROKU_APP_NAME", "vwmark-30729364d005")  # Tera app name

if not all([BOT_TOKEN, API_ID, API_HASH]):
    raise RuntimeError("Env vars set kar!")

app_pyro = Client("movable-watermark-bot", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)

def safe_tmpfile(suffix=""):
    return os.path.join(tempfile.gettempdir(), f"{uuid.uuid4().hex}{suffix}")

# =================== PYROGRAM HANDLERS (same as before) ===================
@app_pyro.on_message(filters.command("start") & filters.private)
async def start(c: Client, m: Message):
    await m.reply_text(
        "Hello! I will watermark videos and PDFs.\n\n"
        "Commands:\n/settext <text>\n/setcolor <black|white>\n/setsize <10-200>\n"
        "/setdirection <static|left-right|top-bottom>\n/setcrf <number>\n"
        "/setres <original|1080|720|480>\n/togglecompress <on|off>\n/showsettings\n\n"
        "Bhej video ya PDF!"
    )

@app_pyro.on_message(filters.command("settext") & filters.private)
async def set_text(c: Client, m: Message):
    user = m.from_user
    if not user: return
    args = m.text.split(" ", 1)
    if len(args) < 2: return await m.reply_text("Usage: /settext text")
    s = get_user_settings(user.id)
    s["text"] = args[1].strip()
    set_user_settings(user.id, s)
    await m.reply_text(f"Text set: {s['text']}")

@app_pyro.on_message(filters.command("setcolor") & filters.private)
async def set_color(c: Client, m: Message):
    user = m.from_user
    if not user: return
    args = m.text.split(" ", 1)
    color = args[1].strip().lower() if len(args) > 1 else ""
    if color not in ("white", "black"): return await m.reply_text("white or black?")
    s = get_user_settings(user.id)
    s["color"] = color
    set_user_settings(user.id, s)
    await m.reply_text(f"Color: {color}")

@app_pyro.on_message(filters.command("setsize") & filters.private)
async def set_size(c: Client, m: Message):
    user = m.from_user
    if not user: return
    try:
        size = int(m.text.split()[1])
        if not 10 <= size <= 200: raise ValueError
    except: return await m.reply_text("Size 10-200")
    s = get_user_settings(user.id)
    s["size"] = size
    set_user_settings(user.id, s)
    await m.reply_text(f"Size: {size}")

@app_pyro.on_message(filters.command("setdirection") & filters.private)
async def set_direction(c: Client, m: Message):
    user = m.from_user
    if not user: return
    val = m.text.split(maxsplit=1)[1].lower() if len(m.text.split()) > 1 else ""
    if val not in ("static", "left-right", "top-bottom"): return await m.reply_text("static|left-right|top-bottom")
    s = get_user_settings(user.id)
    s["direction"] = val
    set_user_settings(user.id, s)
    await m.reply_text(f"Direction: {val}")

@app_pyro.on_message(filters.command("setcrf") & filters.private)
async def set_crf(c: Client, m: Message):
    user = m.from_user
    if not user: return
    try:
        crf = int(m.text.split()[1])
        if not 0 <= crf <= 51: raise ValueError
    except: return await m.reply_text("CRF 0-51")
    s = get_user_settings(user.id)
    s["crf"] = crf
    set_user_settings(user.id, s)
    await m.reply_text(f"CRF: {crf}")

@app_pyro.on_message(filters.command("setres") & filters.private)
async def set_res(c: Client, m: Message):
    user = m.from_user
    if not user: return
    val = m.text.split(maxsplit=1)[1].lower() if len(m.text.split()) > 1 else ""
    if val not in ("original", "1080", "720", "480"): return await m.reply_text("original|1080|720|480")
    s = get_user_settings(user.id)
    s["resolution"] = val
    set_user_settings(user.id, s)
    await m.reply_text(f"Res: {val}")

@app_pyro.on_message(filters.command("togglecompress") & filters.private)
async def toggle_compress(c: Client, m: Message):
    user = m.from_user
    if not user: return
    val = m.text.split(maxsplit=1)[1].lower() if len(m.text.split()) > 1 else ""
    if val not in ("on", "off"): return await m.reply_text("on|off")
    s = get_user_settings(user.id)
    s["compress"] = (val == "on")
    set_user_settings(user.id, s)
    await m.reply_text(f"Compress: {'ON' if s['compress'] else 'OFF'}")

@app_pyro.on_message(filters.command("showsettings") & filters.private)
async def show_settings(c: Client, m: Message):
    user = m.from_user
    if not user: return
    s = get_user_settings(user.id)
    txt = "\n".join([f"{k}: {v}" for k, v in s.items()])
    await m.reply_text(f"Settings:\n{txt}")

@app_pyro.on_message(filters.document & filters.private)
async def handle_pdf(c: Client, m: Message):
    if m.document.mime_type != "application/pdf": return await m.reply_text("PDF only!")
    user = m.from_user
    s = get_user_settings(user.id)
    msg = await m.reply_text("PDF processing...")
    in_path, out_path = safe_tmpfile(".pdf"), safe_tmpfile(".pdf")
    try:
        await m.download(in_path)
        add_watermark_to_pdf(in_path, out_path, s["text"], s["size"], s["color"])
        await c.send_document(m.chat.id, out_path, caption="Watermarked PDF ready!")
        await msg.delete()
    except Exception as e:
        await msg.edit(f"Error: {e}")
    finally:
        for p in (in_path, out_path):
            try: os.remove(p)
            except: pass

@app_pyro.on_message(filters.video & filters.private)
async def handle_video(c: Client, m: Message):
    user = m.from_user
    if not user: return
    s = get_user_settings(user.id)
    msg = await m.reply_text("Video processing...")
    in_path, out_path = safe_tmpfile(".mp4"), safe_tmpfile(".mp4")
    try:
        await m.download(in_path)
        await add_watermark_video(in_path, out_path, s["text"], s.get("color", "white"), s.get("size", 36),
                                  s.get("direction", "static"), s.get("crf", 23), s.get("resolution", "original"))
        await c.send_video(m.chat.id, out_path, caption="Watermarked video ready!")
        await msg.delete()
    except Exception as e:
        await msg.edit(f"Error: {e}")
    finally:
        for p in (in_path, out_path):
            try: os.remove(p)
            except: pass

# =================== WEBHOOK HANDLER ===================
@app_pyro.on_raw_update()
async def raw_handler(client, update, users, chats):
    # Process raw updates for webhook
    if isinstance(update, UpdateShortSent):
        # Handle the update (Pyrogram will dispatch to handlers automatically)
        pass

# =================== FLASK WEB SERVER FOR WEBHOOK ===================
flask_app = Flask(__name__)

@flask_app.route('/webhook', methods=['POST'])
def webhook():
    json_data = request.get_json()
    if json_data:
        # Forward to Pyrogram (in production, use idle or loop)
        asyncio.create_task(app_pyro.handle_update(json_data))
    return jsonify({"status": "ok"})

@flask_app.route('/', defaults={'path': ''})
@flask_app.route('/<path:path>')
def catch_all(path):
    return "Telegram Watermark Bot is running! Send messages on Telegram."

# =================== MAIN ===================
async def start_pyrogram():
    await app_pyro.start()
    me = await app_pyro.get_me()
    webhook_url = f"https://{HEROKU_APP_NAME}.herokuapp.com/webhook"
    await app_pyro.set_webhook(url=webhook_url)
    print(f"Bot started! Webhook set to {webhook_url}")
    # Add raw handler
    app_pyro.add_handler(RawUpdateHandler(raw_handler))
    await asyncio.Event().wait()

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    flask_app.run(host="0.0.0.0", port=port, debug=False)

if __name__ == "__main__":
    if os.getenv("WERKZEUG_RUN_MAIN") == "true":  # For web dyno
        run_flask()
    else:  # For worker (if needed)
        asyncio.run(start_pyrogram())
