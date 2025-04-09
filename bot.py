import os
import re
import asyncio
import tempfile
from telegram import Update, InputMediaPhoto, InputMediaVideo, InputMediaAudio
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters
import logging
import shutil
import humanize
from moviepy import VideoFileClip

# Variabili d'ambiente    
TOKEN = os.environ.get("BOT_TOKEN")
ALLOWED_IDS = set(map(int, os.getenv("ALLOWED_IDS", "").split(",")))
COOKIES_PATH = os.path.join(os.getenv("COOKIE_DIR", "/app/cookies"), "cookies.txt")
DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "/app/downloads")
LOG_TO_FILE = os.getenv("LOG_TO_FILE", "false").lower() == "true"
LOG_FILE_PATH = os.getenv("LOG_FILE_PATH", "bot.log")

# Configurazione logging
handlers = [logging.StreamHandler()]
if LOG_TO_FILE and LOG_FILE_PATH:
    try:
        handlers.append(logging.FileHandler(LOG_FILE_PATH))
    except Exception as e:
        logging.error(f"Errore durante la configurazione del file di log: {e}")

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s',
    handlers=handlers
)

# Ridurre il rumore nei log
for logger_name in ["telegram", "httpx", "asyncio"]:
    logging.getLogger(logger_name).setLevel(logging.WARNING)

def calculate_duration(filepath):
    """Calcola la durata di un video usando MoviePy."""
    try:
        with VideoFileClip(filepath) as clip:
            duration = int(clip.duration)
            minutes, seconds = divmod(duration, 60)
            hours, minutes = divmod(minutes, 60)
            return f"{hours}:{minutes:02}:{seconds:02}" if hours else f"{minutes}:{seconds:02}"
    except Exception as e:
        logging.error(f"Errore nel calcolo della durata: {e}")
        return "Durata sconosciuta"

async def download_content(url, is_audio):
    """Gestisce il download del contenuto usando yt-dlp o gallery-dl."""
    try:
        if "instagram.com/p/" in url:
            # Usa gallery-dl per i post di Instagram
            logging.info("Utilizzo di gallery-dl per il download di un post da Instagram")
            cmd = [
                "gallery-dl",
                "--cookies", COOKIES_PATH,
                "-d", DOWNLOAD_DIR,
                url
            ]
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            logging.info(f"Output di gallery-dl:\n{stdout.decode()}\n{stderr.decode()}")

            if result.returncode != 0:
                raise Exception(f"Errore durante il download con gallery-dl: {stderr.decode()}")

            # Ritorna solo i file scaricati, ignorando le directory
            return sorted(
                [
                    os.path.join(root, file)
                    for root, _, files in os.walk(DOWNLOAD_DIR)
                    for file in files
                ],
                key=os.path.getmtime,
                reverse=True
            )
        else:
            # Usa yt-dlp per reel di Instagram e altri URL
            output_template = os.path.join(DOWNLOAD_DIR, '%(title).80s.%(ext)s')
            ytdlp_cmd = [
                "yt-dlp",
                "--cookies", COOKIES_PATH,
                "-o", output_template,
                url
            ]
            if is_audio:
                ytdlp_cmd += ["-x", "--audio-format", "mp3"]

            logging.info(f"Esecuzione di yt-dlp: {' '.join(ytdlp_cmd)}")
            proc = await asyncio.create_subprocess_exec(
                *ytdlp_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            logging.info(f"yt-dlp output:\n{stdout.decode()}\n{stderr.decode()}")

            if "ERROR:" in stderr.decode():
                raise Exception("Errore durante il download con yt-dlp")

            return sorted(
                [os.path.join(DOWNLOAD_DIR, f) for f in os.listdir(DOWNLOAD_DIR) if os.path.isfile(os.path.join(DOWNLOAD_DIR, f))],
                key=os.path.getmtime,
                reverse=True
            )
    except Exception as e:
        logging.error(f"Errore durante il download: {e}")
        return []

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestisce i messaggi ricevuti dal bot."""
    if not update.message or not update.message.text:
        return

    user_id = update.message.from_user.id
    chat_id = update.message.chat.id

    # Aggiungi reazione iniziale 👍
    try:
        await context.bot.set_message_reaction(chat_id, update.message.message_id, "👍")
    except Exception as e:
        logging.error(f"Errore durante l'aggiunta della reazione iniziale: {e}")

    # Controlla se l'utente è autorizzato
    if user_id not in ALLOWED_IDS and chat_id not in ALLOWED_IDS:
        return

    text = update.message.text.strip()
    link_match = re.search(r'https?://\S+', text)
    if not link_match:
        return

    url = link_match.group(0)
    is_audio = "audio" in text.lower()
    logging.info(f"URL ricevuto: {url}")

    # Scarica il contenuto
    downloaded_files = await download_content(url, is_audio)
    if not downloaded_files:
        await context.bot.set_message_reaction(chat_id, update.message.message_id, "💔")
        return

    # Prepara e invia i file
    media_group = []
    username = f"@{update.message.from_user.username}" if update.message.from_user.username else "utente"

    for filepath in downloaded_files:
        try:
            size_bytes = os.path.getsize(filepath)
            size_human = humanize.naturalsize(size_bytes)
            file_extension = os.path.splitext(filepath)[1].lower()

            if is_audio and file_extension == '.mp3':
                # Invia solo il file audio se "audio" è specificato
                caption = f"{username}\n🔗 [Link]({url})"
                await update.message.reply_audio(open(filepath, "rb"), caption=caption, parse_mode="Markdown")
                
                # Cancella il file MP3 dopo l'invio
                try:
                    os.remove(filepath)
                    logging.info(f"File audio eliminato: {filepath}")
                except Exception as e:
                    logging.error(f"Errore durante l'eliminazione del file audio {filepath}: {e}")
                
                return  # Esci dopo aver inviato l'audio
            elif not is_audio:
                if file_extension in ['.jpg', '.jpeg', '.png']:
                    caption = f"{username}\n🔗 [Link]({url})"
                    media_group.append(InputMediaPhoto(open(filepath, "rb"), caption=caption, parse_mode="Markdown"))
                elif file_extension in ['.mp4', '.webm']:
                    duration = calculate_duration(filepath)
                    caption = f"{username}\n🔗 [Link]({url})\n🕒 *{duration}* | 💾 *{size_human}*"
                    media_group.append(InputMediaVideo(open(filepath, "rb"), caption=caption, parse_mode="Markdown"))
                else:
                    logging.warning(f"Tipo di file non supportato: {filepath}")
        except Exception as e:
            logging.error(f"Errore durante la preparazione del file {filepath}: {e}")

    # Invia i file multimediali (immagini e video) solo se "audio" non è specificato
    if not is_audio and media_group:
        for media_chunk in [media_group[i:i + 10] for i in range(0, len(media_group), 10)]:
            try:
                await update.message.reply_media_group(media=media_chunk)
            except Exception as e:
                logging.error(f"Errore durante l'invio del gruppo di media: {e}")
                await context.bot.set_message_reaction(chat_id, update.message.message_id, "💔")
                return

    # Cancella tutti i file dopo l'invio
    for filepath in downloaded_files:
        try:
            os.remove(filepath)
            logging.info(f"File eliminato: {filepath}")
        except Exception as e:
            logging.error(f"Errore durante l'eliminazione del file {filepath}: {e}")

    await context.bot.set_message_reaction(chat_id, update.message.message_id, "👌")

if __name__ == "__main__":
    if not TOKEN or not ALLOWED_IDS:
        logging.error("TOKEN o ALLOWED_IDS non configurati correttamente")
        exit(1)

    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL, handle_message))
    app.run_polling()
