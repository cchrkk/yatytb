import os
import re
import shlex
import asyncio
import aiofiles
from telegram import Update, InputMediaPhoto, InputMediaVideo, InputMediaAudio
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters
import yt_dlp
import humanize
import subprocess
import logging
import shutil
import requests

def add_reaction(bot_token, chat_id, message_id, reaction):
    try:
        url = f"https://api.telegram.org/bot{bot_token}/addMessageReaction"
        payload = {
            "chat_id": chat_id,
            "message_id": message_id,
            "reaction": reaction
        }
        response = requests.post(url, data=payload)
        if response.status_code == 200:
            logging.info(f"Reazione '{reaction}' aggiunta al messaggio {message_id} nella chat {chat_id}")
        else:
            logging.error(f"Errore durante l'aggiunta della reazione: {response.json()}")
    except Exception as e:
        logging.error(f"Errore durante la chiamata HTTP per aggiungere la reazione: {e}")

def delete_folder(folder_path):
    try:
        if os.path.exists(folder_path):
            shutil.rmtree(folder_path)  # Rimuove la cartella e tutto il contenuto
            logging.info(f"Cartella rimossa con successo: {folder_path}")
        else:
            logging.warning(f"Cartella non trovata: {folder_path}")
    except PermissionError as e:
        logging.error(f"Accesso negato durante la rimozione della cartella: {folder_path} - {e}")
    except Exception as e:
        logging.error(f"Errore generico durante la rimozione della cartella: {folder_path} - {e}")

# Elenco dei logger da limitare
loggers_to_limit = [
    "concurrent.futures",
    "concurrent",
    "asyncio",
    "telegram.request.BaseRequest",
    "telegram.request",
    "telegram",
    "httpx",
    "rich",
    "telegram.request.HTTPXRequest",
    "telegram.Bot",
    "telegram.ext.AIORateLimiter",
    "telegram.ext",
    "telegram.ext.ExtBot",
    "tornado.access",
    "tornado",
    "tornado.application",
    "tornado.general",
    "telegram.ext.Updater",
    "telegram.ext.Application",
    "telegram.ext.JobQueue",
    "telegram.ext.ConversationHandler",
    "urllib3.util.retry",
    "urllib3.util",
    "urllib3",
    "urllib3.connection",
    "urllib3.response",
    "urllib3.connectionpool",
    "urllib3.poolmanager",
    "charset_normalizer",
    "requests"
]

# Imposta tutti i logger al livello WARNING o ERROR
for logger_name in loggers_to_limit:
    logging.getLogger(logger_name).setLevel(logging.WARNING)

# Configura il logger generale
logging.basicConfig(
    level=logging.INFO,  # Mostra solo gli errori del tuo script
    format='[%(asctime)s] %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()  # Per Docker
    ]
)




# Funzione per leggere e pulire gli ID consentiti dalle variabili di ambiente
def get_allowed_ids():
    try:
        raw_ids = os.getenv("ALLOWED_IDS", "")
        # Rimuovi spazi e virgolette e converti in set di interi
        return set(map(int, raw_ids.replace('"', '').replace("'", "").split(",")))
    except ValueError as e:
        logging.error(f"Errore nella conversione degli ALLOWED_IDS: {e}")
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
        logging.error(f"Errore nel calcolo durata: {e}")
        return "Durata sconosciuta"

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    chat_id = update.message.chat.id
    total_size_bytes = 0  # Inizializza la variabile per calcolare il peso totale
    link_match = None  # Inizializza `link_match` come None per evitare errori

    # Controlla se l'utente o il gruppo è nell'elenco consentito
    if user_id not in ALLOWED_IDS and chat_id not in ALLOWED_IDS:
        return

    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()
    link_match = re.search(r'https?://\S+', text)  # Cerca il link nel messaggio

    # Aggiungi la reazione solo se viene trovato un link
    if link_match:
        try:
            await context.bot.set_message_reaction(
                chat_id=chat_id,
                message_id=update.message.message_id,
                reaction="👍"  # Emoji della reazione
            )
        except Exception as e:
            logging.error(f"Errore durante l'aggiunta della reazione: {e}")

    if not link_match:
        return


    url = link_match.group(0)
    is_audio = "audio" in text.lower()
    
    logging.info(f"URL ricevuto: {url}")
    description = ""
    downloaded_files = []

    instagram_folder = os.path.join(DOWNLOAD_DIR, 'instagram')
    # Cancellare la cartella solo se si sta gestendo un URL Instagram
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

            # Elimina la cartella solo se viene usata
            delete_folder(instagram_folder)

        except Exception as e:
            logging.error(f"Errore con gallery-dl: {e}")
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

        if "audio" in text.lower():
            ytdlp_cmd += ["-x", "--audio-format", "mp3"]
            logging.info("Scaricamento solo audio richiesto")
        else:
            logging.info("Scaricamento video richiesto")

        try:
            logging.info(f"Esecuzione yt-dlp: {' '.join(ytdlp_cmd)}")
            proc = await asyncio.create_subprocess_exec(
                *ytdlp_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            logging.info(f"yt-dlp output:\n{stdout.decode()}\n{stderr.decode()}")
        except Exception as e:
            logging.error(f"Errore con yt-dlp: {e}")
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
    caption = f"@{update.message.from_user.username or 'utente'} \n"
    caption += f"[🔗LINK]({url})"

    # Gestisci le immagini separatamente dai video
    for filepath in downloaded_files:
        try:
            size_bytes = os.path.getsize(filepath)
            total_size_bytes += size_bytes  # Somma il peso del file corrente
            size_human = humanize.naturalsize(size_bytes)

            file_extension = os.path.splitext(filepath)[1].lower()
            if file_extension in ['.jpg', '.jpeg', '.png']:
                media_group.append(InputMediaPhoto(open(filepath, "rb")))
            elif file_extension == '.mp4':
                duration = get_duration_from_file(filepath)
                caption_media = caption + f" | 🕒 {duration} | 💾 {size_human}\n"
                media_group.append(InputMediaVideo(open(filepath, "rb"), caption=caption_media, parse_mode='Markdown'))
            elif file_extension == '.mp3':
                media_group.append(InputMediaAudio(open(filepath, "rb"), parse_mode='Markdown'))
            else:
                logging.warning(f"Tipo di file non supportato: {filepath}")
        except Exception as e:
            logging.error(f"Errore durante l'invio del file {filepath}: {e}")

    # Cancella i file SOLO dopo l'invio
    for filepath in downloaded_files:
        try:
            os.remove(filepath)  # Rimuovi i file scaricati
        except Exception as e:
            logging.error(f"Errore durante la rimozione del file {filepath}: {e}")

    from itertools import islice

    # Funzione per dividere la lista in chunk
    def chunk_list(seq, size):
        it = iter(seq)
        return iter(lambda: list(islice(it, size)), [])

    # Dividi i file in gruppi e inviali separatamente
    if media_group:
        from itertools import islice

        # Funzione per dividere la lista in chunk
        def chunk_list(seq, size):
            it = iter(seq)
            return iter(lambda: list(islice(it, size)), [])

        # Dividi i file in gruppi e inviali separatamente
        for media_chunk in chunk_list(media_group, 10):  # Max 10 elementi
            try:
                await update.message.reply_media_group(media=media_chunk)
            except Exception as e:
                logging.error(f"Errore durante l'invio del gruppo: {e}")

        # Mostra il messaggio finale solo se ci sono più di una foto
        if len([item for item in media_group if isinstance(item, InputMediaPhoto)]) > 1:
            total_size_human = humanize.naturalsize(total_size_bytes)
            final_caption = f"@{update.message.from_user.username or 'utente'} |  [🔗LINK]({url}) \n💾 {total_size_human}"
            await update.message.reply_text(final_caption, parse_mode='Markdown')
if __name__ == "__main__":
    if not TOKEN or not ALLOWED_IDS:
        logging.error("TOKEN del bot o ALLOWED_IDS non impostati correttamente")
        exit(1)

    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL, handle_message))
    app.run_polling()
