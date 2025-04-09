# Usa Python 3.11 su Alpine come immagine base
FROM python:3.11-alpine

# Installa gli strumenti di build
RUN apk update && apk add --repository=http://dl-cdn.alpinelinux.org/alpine/edge/testing/ --no-cache \
    ffmpeg \
    curl \
    ca-certificates \
    libmagic \
    py3-moviepy \
    py3-imageio-ffmpeg \
    && rm -rf /var/cache/apk/*

# Copia il file requirements.txt
COPY requirements.txt .
# Assicurati che 'wheel' sia installato
RUN pip install --upgrade pip wheel
# Installa le dipendenze Python
COPY requirements.txt .
RUN pip install -r requirements.txt

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
