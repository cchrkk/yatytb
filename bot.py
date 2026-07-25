import os
import re
import asyncio
import logging
import shutil
import json

from telegram import Update, InputMediaPhoto, InputMediaVideo
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CommandHandler,
    ContextTypes,
    filters,
)
from telegram.constants import ParseMode

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


# Semaforo: un download alla volta
download_lock = asyncio.Lock()


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


def escape_md(text):
    for ch in ("_", "*", "[", "`"):
        text = text.replace(ch, "\\" + ch)
    return text


async def get_yt_metadata(url):
    proc = await asyncio.create_subprocess_exec(
        "yt-dlp", "-J", "--cookies", COOKIES_PATH, url,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=60)
    return json.loads(stdout.decode())


async def build_caption(url):
    try:
        d = await get_yt_metadata(url)
        full = d.get("description", "") or ""
        desc = (full[:200] + "...") if len(full) > 200 else full
        desc = escape_md(desc)
        dur = format_duration(d.get("duration", 0))
        uploader = escape_md(d.get("uploader", "sconosciuto") or "sconosciuto")
        uploader_url = d.get("uploader_url", "") or ""
        ext = escape_md(d.get("extractor", "?") or "?")
        likes = format_count(d.get("like_count", 0))
        filesize = d.get("filesize") or d.get("filesize_approx")
    except Exception:
        desc = "N/D"
        dur = "?"
        uploader = "sconosciuto"
        uploader_url = ""
        ext = "?"
        likes = "N/D"
        filesize = None

    up = f"[{uploader}]({uploader_url})" if uploader_url else uploader
    return (
        f"🔗 [{ext}]({url})\n"
        f"👤 {up}\n"
        f"🕒 *{dur}* | 👍 *{likes}*\n"
        f"📝 {desc}",
        filesize,
    )


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
            cmd = ["gallery-dl", "--cookies", COOKIES_PATH, "-d", DOWNLOAD_DIR, url]
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
                "yt-dlp", "--cookies", COOKIES_PATH,
                "--merge-output-format", "mp4",
                "-o", tmpl, url,
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
            err_text = stderr.decode()
            out = stdout.decode() + err_text
            logging.info("yt-dlp output: %s", out.strip()[:500])
            if proc.returncode != 0:
                raise Exception(err_text.strip() or "yt-dlp fallito")

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
    await update.message.reply_text("⏹ Nessun download in corso da annullare.")


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

        # Una sola chiamata yt-dlp per metadata + filesize
        caption, filesize = await build_caption(url)
        if filesize and filesize > MAX_FILE_SIZE:
            await update.message.reply_text(
                f"⚠️ File troppo grande (> {MAX_FILE_SIZE // 1024 // 1024} MB)."
            )
            await context.bot.set_message_reaction(chat_id, update.message.message_id, "💔")
            return

        async with download_lock:
            files = await download_content(url, is_audio)
        if not files:
            await update.message.reply_text(
                "❌ Nessun file scaricato. Verifica che il link sia valido o che il formato sia supportato."
            )
            await context.bot.set_message_reaction(chat_id, update.message.message_id, "💔")
            return

        media_group = []
        opened_files = []

        try:
            for fp in files:
                ext = os.path.splitext(fp)[1].lower()

                if is_audio and ext == ".mp3":
                    with open(fp, "rb") as f:
                        await update.message.reply_audio(
                            f, caption=f"🔗 [Link]({url})", parse_mode=ParseMode.MARKDOWN
                        )
                    os.remove(fp)
                    continue

                fh = open(fp, "rb")
                opened_files.append(fh)

                if ext in (".jpg", ".jpeg", ".png"):
                    media_group.append(
                        InputMediaPhoto(
                            fh,
                            caption=caption if not media_group else None,
                            parse_mode=ParseMode.MARKDOWN,
                        )
                    )
                elif ext in (".mp4", ".webm"):
                    media_group.append(
                        InputMediaVideo(
                            fh,
                            caption=caption if not media_group else None,
                            parse_mode=ParseMode.MARKDOWN,
                        )
                    )
                else:
                    fh.close()
                    opened_files.remove(fh)
                    with open(fp, "rb") as f:
                        await update.message.reply_document(f)
                    os.remove(fp)

            if media_group:
                for chunk in [media_group[i : i + 10] for i in range(0, len(media_group), 10)]:
                    await update.message.reply_media_group(media=chunk)

        finally:
            for fh in opened_files:
                fh.close()

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
        r"""
                     __            __ ___.
      ___.__._____ _/  |_ ___.__._/  |\_ |__
     <   |  |\__  \\   __<   |  |\   __\ __ \
      \___  | / __ \|  |  \___  | |  | | \_\ \
      / ____|(____  /__|  / ____| |__| |___  /
      \/          \/      \/               \/
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

    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    logging.info("Bot avviato")

    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        pass
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Bot fermato dall'utente")
    except Exception as e:
        logging.error("Errore main: %s", e)
    logging.info("Bot terminato")
