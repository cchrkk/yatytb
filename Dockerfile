# Usa Python 3.11 su Alpine come immagine base
FROM python:3.11-alpine
RUN apk update && apk add --no-cache ffmpeg && rm -rf /var/cache/apk/*

# Assicurati che 'wheel' sia installato
RUN pip install --upgrade pip wheel

# Installa le dipendenze Python direttamente
RUN pip install python-telegram-bot yt-dlp gallery-dl humanize

# Crea le directory per i download e i cookies
RUN mkdir -p /app/downloads /app/cookies

# Imposta la cartella di lavoro
WORKDIR /app

# Copia il bot nel container
COPY bot.py .

# Imposta le variabili d'ambiente (modifica i valori in base alle tue esigenze)
ENV ALLOWED_IDS=changeme
ENV BOT_TOKEN=changeme
ENV LOG_TO_FILE=false
ENV LOG_FILE_PATH=bot.log

# Crea un volume per i download
VOLUME ["/app/downloads"]

# Avvia il bot
CMD ["python", "bot.py"]
