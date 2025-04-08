import os
import re
import shlex
import asyncio
import aiofiles
from telegram import Update, InputMediaPhoto, InputMediaVideo
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters
import yt_dlp
import humanize
import subprocess

# Funzione per leggere e pulire gli ID consentiti dalle variabili di ambiente
def get_allowed_ids():
    try:
        raw_ids = os.getenv("ALLOWED_IDS", "")
        # Rimuovi spazi e virgolette e converti in set di interi
        return set(map(int, raw_ids.replace('"', '').replace("'", "").split(",")))
    except ValueError as e:
        print(f"Errore nella conversione degli ALLOWED_IDS: {e}")
        return set()

# Leggi gli ID consentiti e altre variabili di ambiente
ALLOWED_IDS = get_allowed_ids()
TOKEN = os.environ.get("BOT_TOKEN")
COOKIES_PATH = os.path.join(os.getenv("COOKIE_DIR", "/app/cookies"), "cookies.txt")
DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "/app/downloads")

def get_duration_from_file(filepath):
    if not os.path.isfile(filepath):
        return "File non trovato"

    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                filepath
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        duration_str = result.stdout.strip()
        if not duration_str:
            return "Durata sconosciuta"
        duration = float(duration_str)
        
        hours = int(duration // 3600)
        minutes = int((duration % 3600) // 60)
        seconds = int(duration % 60)

        if hours:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes}:{seconds:02d}"
    except Exception as e:
        print(f"Errore nel calcolo durata: {e}")
        return "Durata sconosciuta"

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    chat_id = update.message.chat.id

    # Controlla se l'utente o il gruppo è nell'elenco consentito
    if user_id not in ALLOWED_IDS and chat_id not in ALLOWED_IDS:
        return

    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()
    link_match = re.search(r'https?://\S+', text)
    if not link_match:
        return

    url = link_match.group(0)
    is_audio = "audio" in text.lower()

    print(f"URL ricevuto: {url}")

    downloaded_files = []

    # Se è un post Instagram (non reel), usa gallery-dl
    if re.match(r'https://(www\.)?instagram\.com/p/', url):
        try:
            print("Uso gallery-dl per questo URL")
            cmd = [
                "gallery-dl",
                "--cookies", COOKIES_PATH,
                "-d", DOWNLOAD_DIR,
                url
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            print(f"gallery-dl output:\n{result.stdout}\n{result.stderr}")

            # Naviga nella cartella e prendi i file
            instagram_folder = os.path.join(DOWNLOAD_DIR, 'instagram')
            if os.path.exists(instagram_folder):
                for root, dirs, files in os.walk(instagram_folder):
                    for file in files:
                        downloaded_files.append(os.path.join(root, file))
            
        except Exception as e:
            print(f"Errore con gallery-dl: {e}")
            await update.message.reply_text("Errore con gallery-dl")

    else:
        # Altrimenti usa yt-dlp (audio/video/reel ecc.)
        output_template = os.path.join(DOWNLOAD_DIR, '%(title).80s.%(ext)s')
        ytdlp_cmd = [
            "yt-dlp",
            "--cookies", COOKIES_PATH,
            "-o", output_template,
            url
        ]

        if is_audio:
            ytdlp_cmd += ["-x", "--audio-format", "mp3"]

        try:
            print(f"Esecuzione yt-dlp: {' '.join(ytdlp_cmd)}")
            proc = await asyncio.create_subprocess_exec(
                *ytdlp_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            print(f"yt-dlp output:\n{stdout.decode()}\n{stderr.decode()}")
        except Exception as e:
            print(f"Errore con yt-dlp: {e}")
            await update.message.reply_text("Errore con yt-dlp")

    # Trova file scaricati
    if not downloaded_files:
        downloaded_files = sorted(
            [os.path.join(DOWNLOAD_DIR, f) for f in os.listdir(DOWNLOAD_DIR)],
            key=os.path.getmtime,
            reverse=True
        )

    if not downloaded_files:
        return

    # Inizializza lista per le immagini da inviare
    media_group = []
    caption = f"@{update.message.from_user.username or 'utente'} | "
    caption += f"[🔗LINK]({url})"

    # Gestisci le immagini separatamente dai video
    for filepath in downloaded_files[:5]:
        try:
            size_bytes = os.path.getsize(filepath)
            size_human = humanize.naturalsize(size_bytes)
            duration = get_duration_from_file(filepath)

            caption_media = caption + f" | 🕒 {duration} | 💾 {size_human}\n"

            # Controlla se il file è immagine o video tramite estensione
            file_extension = os.path.splitext(filepath)[1].lower()
            if file_extension in ['.jpg', '.jpeg', '.png']:
                media_group.append(InputMediaPhoto(open(filepath, "rb"), caption=caption_media, parse_mode='Markdown'))
            elif file_extension == '.mp4':
                media_group.append(InputMediaVideo(open(filepath, "rb"), caption=caption_media, parse_mode='Markdown'))
            else:
                print(f"Tipo di file non supportato: {filepath}")
            
            os.remove(filepath)
        except Exception as e:
            print(f"Errore durante l'invio del file {filepath}: {e}")

    # Se ci sono più file, invia come media group
    if media_group:
        await update.message.reply_media_group(media=media_group)

if __name__ == "__main__":
    if not TOKEN or not ALLOWED_IDS:
        print("TOKEN del bot o ALLOWED_IDS non impostati correttamente")
        exit(1)

    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL, handle_message))
    app.run_polling()
