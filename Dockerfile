FROM python:3.13-alpine

RUN apk update && apk add --no-cache ffmpeg nodejs npm && rm -rf /var/cache/apk/*

RUN pip install --no-cache-dir \
    python-telegram-bot \
    yt-dlp \
    gallery-dl \
    humanize

RUN mkdir -p /app/downloads /app/cookies

WORKDIR /app

COPY bot.py .

ENV ALLOWED_IDS=changeme
ENV BOT_TOKEN=changeme
ENV LOG_TO_FILE=false
ENV LOG_FILE_PATH=bot.log
ENV MAX_FILE_SIZE_MB=2000
ENV COOKIES_PATH=/app/cookies/cookies.txt
ENV DOWNLOAD_DIR=/app/downloads

VOLUME ["/app/downloads"]

ENTRYPOINT ["python", "bot.py"]
