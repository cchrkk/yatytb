# Usa Python 3.11 su Alpine come immagine base
FROM python:3.11-alpine

# Installa ffmpeg e le dipendenze necessarie per ffmpeg
RUN apk update && apk add --no-cache \
    ffmpeg \
    && rm -rf /var/cache/apk/*
COPY requirements.txt .
# Installa le dipendenze Python
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

# Crea un volume per i download
VOLUME ["/app/downloads"]

# Avvia il bot
CMD ["python", "bot.py"]
