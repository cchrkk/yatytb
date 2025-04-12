# Use Python 3.11 on Alpine as the base image
FROM python:3.11-alpine
RUN apk update && apk add --no-cache ffmpeg && rm -rf /var/cache/apk/*

# Ensure 'wheel' is installed
RUN pip install --upgrade pip wheel

# Install Python dependencies directly
RUN pip install python-telegram-bot yt-dlp gallery-dl humanize dotenv

# Create directories for downloads and cookies
RUN mkdir -p /app/downloads /app/cookies

# Set the working directory
WORKDIR /app

# Copy the bot into the container
COPY bot.py .

# Set environment variables (modify the values as needed)
ENV ALLOWED_IDS=changeme
ENV BOT_TOKEN=changeme
ENV LOG_TO_FILE=false
ENV LOG_FILE_PATH=bot.log

# Create a volume for downloads
VOLUME ["/app/downloads"]

# Start the bot
CMD ["python", "bot.py"]
