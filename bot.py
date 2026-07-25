import os
import re
import asyncio
import logging
import shutil
import subprocess
import json
from datetime import datetime

from telegram import Update, InputMediaPhoto, InputMediaVideo
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CommandHandler,
    ContextTypes,
    filters,
)
from telegram.constants import ParseMode
from telegram.error import TelegramError

TOKEN = os.environ.get("BOT_TOKEN")
ALLOWED_IDS = set(
    int(x.strip()) for x in os.getenv("ALLOWED_IDS", "").split(",") if x.strip()
)
COOKIES_PATH = os.getenv("COOKIES_PATH", "/app/cookies/cookies.txt")
DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "/app/downloads")
LOG_TO_FILE = os.getenv("LOG_TO_FILE", "false").lower() == "true"
LOG_FILE_PATH = os.getenv("LOG_FILE_PATH", "bot.log")
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE_MB", "2000")) * 1024 * 1024

# Logging
handlers = [logging.StreamHandler()]
if LOG_TO_FILE and LOG_FILE_PATH:
    try:
        handlers.append(logging.FileHandler(LOG_FILE_PATH))
    except Exception as e:
        logging.error("Errore file log: %s", e)

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s - %(message)s",
    handlers=handlers,
)

for logger_name in ("telegram", "httpx", "asyncio"):
    logging.getLogger(logger_name).setLevel(logging.WARNING)

# Coda download
download_queue = asyncio.Queue()
# --- Utility ---
def validate_env():
    errors = []
    if not TOKEN:
        errors.append("BOT_TOKEN non impostato")
    if not ALLOWED_IDS:
        errors.append("ALLOWED_IDS non impostato (almeno un ID)")
    if COOKIES_PATH and not os.path.exists(COOKIES_PATH):
        logging.warning("cookies.txt non trovato in %s", COOKIES_PATH)
    return errors


def format_duration(seconds):
    try:
        seconds = int(seconds)
        m, s = divmod(seconds, 60)
        return f"{m}:{s:02d}"
    except ValueError:
        return "?"


def format_count(n):
    try:
        n = int(n)
        if n >= 1_000_000:
            return f"{n // 1_000_000}M"
        if n >= 1_000:
            return f"{n // 1_000}k"
        return str(n)
    except ValueError:
        return "N/D"


def build_caption(url, extractor="link"):
    desc, dur, uploader, uploader_url, ext, likes = "N/D", "?", "sconosciuto", "", "?", "N/D"
    try:
        result = subprocess.run(
            ["yt-dlp", "-J", "--cookies", COOKIES_PATH, url],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0:
            d = json.loads(result.stdout)
            full = d.get("description", "")
            desc = (full[:200] + "...") if len(full) > 200 else full
            dur = format_duration(d.get("duration", 0))
            uploader = d.get("uploader", "sconosciuto")
            uploader_url = d.get("uploader_url", "")
            ext = d.get("extractor", "?")
            likes = format_count(d.get("like_count", 0))
    except Exception:
        pass

    up = f"[{uploader}]({uploader_url})" if uploader_url else uploader
    return (
        f"🔗 [{ext}]({url})\n"
        f"👤 {up}\n"
        f"🕒 *{dur}* | 👍 *{likes}*\n"
        f"📝 {desc}"
    )


async def get_filesize(url):
    try:
        proc = await asyncio.create_subprocess_exec(
            "yt-dlp", "-J", "--cookies", COOKIES_PATH, url,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
        d = json.loads(stdout.decode())
        return d.get("filesize") or d.get("filesize_approx")
    except Exception:
        return None


async def cleanup():
    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR, exist_ok=True)
        return
    for entry in os.listdir(DOWNLOAD_DIR):
        path = os.path.join(DOWNLOAD_DIR, entry)
        try:
            if os.path.isfile(path) or os.path.islink(path):
                os.remove(path)
            elif os.path.isdir(path):
                shutil.rmtree(path)
        except Exception as e:
            logging.error("Errore pulizia %s: %s", path, e)


async def download_content(url, is_audio):
    try:
        if "instagram.com/p/" in url:
            cmd = [
                "gallery-dl",
                "--cookies", COOKIES_PATH,
                "-d", DOWNLOAD_DIR,
                url,
            ]
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            logging.info("gallery-dl: %s", stdout.decode().strip())
            if proc.returncode != 0:
                raise Exception(stderr.decode().strip() or "gallery-dl fallito")
        else:
            tmpl = os.path.join(DOWNLOAD_DIR, "%(title).80s.%(ext)s")
            cmd = [
                "yt-dlp",
                "--cookies", COOKIES_PATH,
                "--merge-output-format", "mp4",
                "-o", tmpl,
                url,
            ]
            if is_audio:
                cmd += ["-x", "--audio-format", "mp3"]
            logging.info("yt-dlp: %s", " ".join(cmd))
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            out = stdout.decode() + stderr.decode()
            logging.info("yt-dlp output: %s", out.strip()[:500])
            if "ERROR:" in stderr.decode():
                raise Exception(stderr.decode().strip())

        files = []
        for root, _, fs in os.walk(DOWNLOAD_DIR):
            for f in fs:
                path = os.path.join(root, f)
                if os.path.isfile(path):
                    files.append(path)
        return sorted(files, key=os.path.getmtime, reverse=True)
    except Exception as e:
        logging.error("Download fallito: %s", e)
        return []


# --- Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎥 *YATYTB Bot*\n\n"
        "Invia un link (YouTube, Instagram, TikTok, ecc.) e ti rimando il video.\n"
        "Scrivi `audio` prima del link per scaricare solo l'audio.\n\n"
        "Comandi:\n"
        "/start — questo messaggio\n"
        "/help — aiuto dettagliato\n"
        "/cancel — annulla il download in corso",
        parse_mode=ParseMode.MARKDOWN,
    )


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *Aiuto*\n\n"
        "Esempi:\n"
        "`https://youtube.com/watch?v=...` — scarica video\n"
        "`audio https://youtube.com/watch?v=...` — solo audio MP3\n"
        "`https://instagram.com/p/...` — foto/gallery\n\n"
        "Limite file: fino a 2 GB.\n"
        "Formati supportati: MP4, MP3, JPG, PNG.",
        parse_mode=ParseMode.MARKDOWN,
    )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Annulla il download in coda per l'utente."""
    await update.message.reply_text("⏹ Nessun download da annullare (usa quando sei in coda).")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    user_id = update.message.from_user.id
    chat_id = update.message.chat.id
    text = update.message.text.strip()

    if user_id not in ALLOWED_IDS and chat_id not in ALLOWED_IDS:
        return

    link_match = re.search(r"https?://\S+", text)
    if not link_match:
        return

    url = link_match.group(0)
    is_audio = "audio" in text.lower()
    logging.info("URL: %s | audio=%s | user=%s", url, is_audio, user_id)

    try:
        await context.bot.set_message_reaction(chat_id, update.message.message_id, "👍")

        # Controllo dimensione
        filesize = await get_filesize(url)
        if filesize and filesize > MAX_FILE_SIZE:
            await update.message.reply_text(
                f"⚠️ File troppo grande (> {MAX_FILE_SIZE // 1024 // 1024} MB)."
            )
            await context.bot.set_message_reaction(chat_id, update.message.message_id, "💔")
            return

        files = await download_content(url, is_audio)
        if not files:
            await update.message.reply_text("❌ Nessun file scaricato.")
            await context.bot.set_message_reaction(chat_id, update.message.message_id, "💔")
            return

        # Prepara caption video solo per il primo file
        caption = build_caption(url, "link")
        media_group = []

        for fp in files:
            ext = os.path.splitext(fp)[1].lower()

            if is_audio and ext == ".mp3":
                with open(fp, "rb") as f:
                    await update.message.reply_audio(
                        f, caption=f"🔗 [Link]({url})", parse_mode=ParseMode.MARKDOWN
                    )
                os.remove(fp)
                continue

            if ext in (".jpg", ".jpeg", ".png"):
                media_group.append(
                    InputMediaPhoto(
                        open(fp, "rb"),
                        caption=caption if not media_group else None,
                        parse_mode=ParseMode.MARKDOWN,
                    )
                )
            elif ext in (".mp4", ".webm"):
                media_group.append(
                    InputMediaVideo(
                        open(fp, "rb"),
                        caption=caption if not media_group else None,
                        parse_mode=ParseMode.MARKDOWN,
                    )
                )
            else:
                with open(fp, "rb") as f:
                    await update.message.reply_document(f)
                os.remove(fp)

        if media_group:
            for chunk in [media_group[i : i + 10] for i in range(0, len(media_group), 10)]:
                try:
                    await update.message.reply_media_group(media=chunk)
                except Exception as e:
                    logging.error("Errore media_group: %s", e)

        # Cleanup
        await asyncio.sleep(2)
        await cleanup()
        await context.bot.set_message_reaction(chat_id, update.message.message_id, "👌")

    except Exception as e:
        logging.error("Errore handle_message: %s", e)
        await context.bot.set_message_reaction(chat_id, update.message.message_id, "💔")
        await cleanup()


# --- Main ---
async def main():
    errors = validate_env()
    if errors:
        for e in errors:
            logging.error(e)
        exit(1)

    logging.info(
        """
                     __            __ ___.
      ___.__._____ _/  |_ ___.__._/  |\\_ |__
     <   |  |\\__  \\\\   __<   |  |\\   __\\ __ \\
      \\___  | / __ \\|  |  \\___  | |  | | \\_\\ \\
      / ____|(____  /__|  / ____| |__| |___  /
      \\/          \\/      \\/               \\/
    """
    )

    await cleanup()

    app = (
        ApplicationBuilder()
        .token(TOKEN)
        .read_timeout(300)
        .write_timeout(300)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_handler))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(MessageHandler(filters.ALL, handle_message))

    print("🤖 Bot avviato — premi Ctrl+C per fermarlo")
    await app.run_polling()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Bot fermato dall'utente")
    except Exception as e:
        logging.error("Errore main: %s", e)
    logging.info("Bot terminato")
