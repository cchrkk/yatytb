
# Yet Another yt-dlp Telegram Bot 🎥📥

This project is a Telegram bot that allows you to download videos and audio using `yt-dlp` or `gallery-dl` directly on Telegram. You can send links of videos and posts from platforms like YouTube and Instagram, and the bot will send you the files as media. The bot also supports images from Instagram, which are sent as a media group with a single caption. 📲✨

## Features 🌟

- Downloads videos and audio using `yt-dlp`. 🎧🎬
- Handles Instagram posts using `gallery-dl`. 📸📲
- Supports sending video and image files on Telegram. 💬📹
- Allows customization of allowed user IDs via Docker environment variables. 🔒

## Prerequisites ⚙️

- Docker 🐳
- Docker Compose 🛠️
- Telegram (duh 🫠)

## Ghcr.io Compose Example 🚀

```yaml
version: "3.8"
services:
  tg-downloader:
    image: ghcr.io/cchrkk/yatytb:latest  # Usa l'immagine dal GitHub Container Registry
    environment:
      - BOT_TOKEN=YOUR_BOT_TOKEN # Required
      - ALLOWED_IDS=YOUR_ALLOWED_CHAT_OR_GROUP_IDS # Required, comma-separated
    volumes:
      - /root/cookies.txt:/app/cookies/cookies.txt  # Optional
```

## Environment Variables 🔑
- **BOT_TOKEN**: Your Telegram bot token (required for authentication). 🆔
  Ask it here [@BotFather](https://t.me/BotFather)
- **ALLOWED_IDS**: A comma-separated list of user IDs authorized to interact with the bot. 👥

## Create your cookies.txt file 🍪
1. Log in to Instagram/Tiktok/Youtube in your browser. 🌍
2. Export the cookies using a browser extension like "EditThisCookie". 🔐
3. Save the cookies as a `.txt` file, and name it `cookies.txt`. 💾
4. Place this `cookies.txt` file and mount the volume in the docker-compose.

## How It Works ⚡
1. Send a video or post link (YouTube, Instagram) to the bot. 📨
2. The bot downloads the content and sends you the files. ⬇️
3. If the link is an Instagram post with multiple images, the bot will send all images in a single message as a media group. 📸🎨

![image](https://github.com/user-attachments/assets/b11edc73-09d5-49de-86fe-79b7e98f1efc)

## Contributing 💡
If you want to contribute to this project, feel free to fork the repository and send a pull request with improvements or bug fixes. 🛠️

## License 📜
This project is licensed under the MIT License - see the LICENSE file for details.
