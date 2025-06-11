#                     __            __ ___.    
#      ___.__._____ _/  |_ ___.__._/  |\_ |__  
#     <   |  |\__  \\   __<   |  |\   __\ __ \ 
#      \___  | / __ \|  |  \___  | |  | | \_\ \
#      / ____|(____  /__|  / ____| |__| |___  /
#      \/          \/      \/               \/ 
#
# Questo bot Telegram consente di scaricare contenuti multimediali (video, audio, immagini) da piattaforme come YouTube e Instagram.
# Utilizza le librerie `yt-dlp` e `gallery-dl` per gestire i download e supporta diverse funzionalità:
#
# Funzionalità principali:
# - Scarica video e audio da YouTube, Instagram e altre piattaforme supportate da `yt-dlp`.
# - Gestisce i post di Instagram (foto e video) utilizzando `gallery-dl`.
# - Supporta il download di audio in formato MP3 se specificato nel messaggio.
# - Recupera dettagli del video (descrizione, durata, uploader, ecc.) per i video scaricati.
# - Invia i file scaricati come messaggi multimediali su Telegram.
# - Supporta l'invio di gruppi di media (es. più immagini in un unico messaggio).
# - Aggiunge reazioni ai messaggi con link validi ("👍") o segnala errori con reazioni ("💔").
# - Elimina i file scaricati dal server dopo l'invio per risparmiare spazio.
#
# Sicurezza:
# - Controlla che solo gli utenti autorizzati (definiti tramite la variabile d'ambiente `ALLOWED_IDS`) possano interagire con il bot.
#
# Logging:
# - Registra le attività del bot, con opzione per salvare i log su file (abilitabile tramite `LOG_TO_FILE`).
#
# Reazioni:
# - Aggiunge una reazione "👍" ai messaggi che contengono un link valido.
# - Aggiunge una reazione "💔" in caso di errore durante il download o l'invio.
#
# Come funziona:
# 1. L'utente invia un messaggio contenente un link al bot.
# 2. Il bot verifica se l'utente è autorizzato e se il messaggio contiene un link valido.
# 3. In base al tipo di contenuto (audio, video, immagini), il bot utilizza `yt-dlp` o `gallery-dl` per scaricare i file.
# 4. I file scaricati vengono inviati all'utente come messaggi multimediali.
# 5. Dopo l'invio, i file vengono eliminati dal server per mantenere pulita la directory di lavoro.

import os
import re
import asyncio
import tempfile
from telegram import Update, InputMediaPhoto, InputMediaVideo, InputMediaAudio
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters
import logging
import shutil
import humanize
import subprocess
import json
from telegram.constants import ParseMode
from telegram.error import TelegramError, NetworkError

# Variabili d'ambiente
TOKEN = os.environ.get("BOT_TOKEN")
ALLOWED_IDS = set(map(int, os.getenv("ALLOWED_IDS", "").split(",")))
COOKIES_PATH = "/app/cookies/cookies.txt"
DOWNLOAD_DIR = "/app/downloads"
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

# Configurazione timeout e chunk size
CHUNK_SIZE = 50 * 1024 * 1024  # 50MB per chunk
MAX_RETRIES = 3
RETRY_DELAY = 5  # secondi

def get_video_details(url, cookies_path):
    """Recupera dettagli video (descrizione, durata, uploader, uploader_url, extractor, e like_count) da yt-dlp."""
    try:
        cmd = ["yt-dlp", "-J", "--cookies", cookies_path, url]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        if result.returncode != 0:
            raise Exception(f"Errore durante l'esecuzione di yt-dlp: {result.stderr.strip()}")
        
        data = json.loads(result.stdout)
        description = data.get("description", "Descrizione non disponibile")
        duration_seconds = int(data.get("duration", 0))
        duration_formatted = format_duration(duration_seconds)
        uploader = data.get("uploader", "Uploader sconosciuto")
        uploader_url = data.get("uploader_url", "")
        extractor = data.get("extractor", "Extractor sconosciuto")
        like_count = data.get("like_count", 0)
        like_count_formatted = format_like_count(like_count)

        return description, duration_formatted, uploader, uploader_url, extractor, like_count_formatted
    except Exception as e:
        logging.error(f"Errore nel recupero dei dettagli video: {e}")
        return "Descrizione non disponibile", "Durata sconosciuta", "Uploader sconosciuto", "", "Extractor sconosciuto", "N/D"
def format_duration(seconds):
    """Converte i secondi in formato minuti:secondi."""
    try:
        seconds = int(seconds)
        minutes, seconds = divmod(seconds, 60)
        return f"{minutes}:{seconds:02}"
    except ValueError:
        return "Durata non valida"
        
def format_like_count(number):
    """Converte i numeri grandi in formato abbreviato con suffissi."""
    try:
        number = int(number)
        if number >= 1_000_000:
            return f"{number // 1_000_000}M"  # Milioni
        elif number >= 1_000:
            return f"{number // 1_000}k"  # Migliaia
        else:
            return str(number)  # Numeri piccoli senza suffisso
    except ValueError:
        return "N/D"  # Valore di default in caso di errore

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
                "--merge-output-format", "mp4",  # Separato correttamente
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

async def send_large_file(update: Update, filepath: str, caption: str, is_video: bool = False):
    """Gestisce l'invio di file grandi in chunk."""
    try:
        file_size = os.path.getsize(filepath)
        if file_size <= CHUNK_SIZE:
            # Se il file è piccolo, invialo normalmente
            with open(filepath, "rb") as file:
                if is_video:
                    await update.message.reply_video(file, caption=caption, parse_mode=ParseMode.MARKDOWN)
                else:
                    await update.message.reply_document(file, caption=caption, parse_mode=ParseMode.MARKDOWN)
            return True

        # Per file grandi, dividi in chunk
        with open(filepath, "rb") as file:
            for i in range(0, file_size, CHUNK_SIZE):
                chunk = file.read(CHUNK_SIZE)
                temp_chunk = tempfile.NamedTemporaryFile(delete=False)
                temp_chunk.write(chunk)
                temp_chunk.close()
                temp_chunk_path = temp_chunk.name

                for attempt in range(MAX_RETRIES):
                    try:
                        with open(temp_chunk_path, "rb") as chunk_file:
                            if is_video:
                                await update.message.reply_video(
                                    chunk_file,
                                    caption=caption if i == 0 else None,
                                    parse_mode=ParseMode.MARKDOWN
                                )
                            else:
                                await update.message.reply_document(
                                    chunk_file,
                                    caption=caption if i == 0 else None,
                                    parse_mode=ParseMode.MARKDOWN
                                )
                        break
                    except (TelegramError, NetworkError) as e:
                        if attempt == MAX_RETRIES - 1:
                            raise e
                        await asyncio.sleep(RETRY_DELAY)
                    finally:
                        try:
                            if os.path.exists(temp_chunk_path):
                                os.unlink(temp_chunk_path)
                        except Exception as e:
                            logging.error(f"Errore durante l'eliminazione del file temporaneo {temp_chunk_path}: {e}")

        return True
    except Exception as e:
        logging.error(f"Errore durante l'invio del file grande {filepath}: {e}")
        return False

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestisce i messaggi ricevuti dal bot."""
    if not update.message or not update.message.text:
        return

    user_id = update.message.from_user.id
    chat_id = update.message.chat.id

    # Controlla se il messaggio contiene un link
    text = update.message.text.strip()
    link_match = re.search(r'https?://\S+', text)

    if link_match:  # Reazione 👍 solo se c'è un link
        try:
            await context.bot.set_message_reaction(chat_id, update.message.message_id, "👍")
        except Exception as e:
            logging.error(f"Errore durante l'aggiunta della reazione 👍: {e}")
    else:
        logging.info("Messaggio ricevuto senza link: nessuna reazione 👍")


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
        asyncio.create_task(delayed_cleanup_download_dir())
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
                caption = f"🔗 [Link]({url})"
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
                    caption = f"🔗 [Link]({url})"
                    media_group.append(InputMediaPhoto(open(filepath, "rb"), caption=caption, parse_mode=ParseMode.MARKDOWN))
                elif file_extension in ['.mp4', '.webm']:
                    description, duration, uploader, uploader_url, extractor, like_count_formatted = get_video_details(url, COOKIES_PATH)
                    uploader_hyperlink = f"[{uploader}]({uploader_url})" if uploader_url else uploader
                    caption = (
                        f"🔗 [Link {extractor}]({url})\n"
                        f"👤 {uploader_hyperlink}\n"
                        f"🕒 *{duration}* | 👍 *{like_count_formatted}*\n"
                        f"📝 {description}\n"
                    )
                    
                    # Usa la nuova funzione per file grandi
                    if size_bytes > 50 * 1024 * 1024:
                        success = await send_large_file(update, filepath, caption, is_video=True)
                        if not success:
                            await context.bot.set_message_reaction(chat_id, update.message.message_id, "💔")
                            return
                    else:
                        media_group.append(InputMediaVideo(open(filepath, "rb"), caption=caption, parse_mode=ParseMode.MARKDOWN))
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
    # Avvia la cancellazione ritardata della cartella downloads
    asyncio.create_task(delayed_cleanup_download_dir())

async def delayed_cleanup_download_dir(delay_seconds=10):
    """Attende delay_seconds e poi elimina tutti i file nella cartella DOWNLOAD_DIR, lasciando la cartella intatta."""
    await asyncio.sleep(delay_seconds)
    try:
        if os.path.exists(DOWNLOAD_DIR):
            for filename in os.listdir(DOWNLOAD_DIR):
                file_path = os.path.join(DOWNLOAD_DIR, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.remove(file_path)
                        logging.info(f"File eliminato: {file_path}")
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                        logging.info(f"Cartella eliminata: {file_path}")
                except Exception as e:
                    logging.error(f"Errore durante l'eliminazione di {file_path}: {e}")
    except Exception as e:
        logging.error(f"Errore durante la pulizia della cartella {DOWNLOAD_DIR}: {e}")

if __name__ == "__main__":
    if not TOKEN or not ALLOWED_IDS:
        logging.error("TOKEN o ALLOWED_IDS non configurati correttamente")
        exit(1)

    app = ApplicationBuilder().token(TOKEN).read_timeout(300).write_timeout(300).build()
    app.add_handler(MessageHandler(filters.ALL, handle_message))
    app.run_polling()
