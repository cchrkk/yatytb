FROM python:3.11-slim

RUN apt update && apt install -y ffmpeg && \
    pip install moviepy python-telegram-bot yt-dlp aiofiles humanize gallery-dl && \
    mkdir -p /app/downloads /app/cookies

WORKDIR /app
COPY bot.py .
#COPY cookies.txt /app/cookies/cookies.txt
ENV ALLOWED_IDS=changeme
ENV BOT_TOKEN=changeme
VOLUME ["/app/downloads"]

CMD ["python", "bot.py"]
