# Yet Another yt-dlp Telegram Bot 🎥📥

This project is a Telegram bot that allows you to download videos and audio using [yt-dlp](https://github.com/yt-dlp/yt-dlp) or [gallery-dl](https://github.com/mikf/gallery-dl) directly on Telegram. You can send links of videos and posts from platforms like YouTube and Instagram, and the bot will send you the files as media. The bot also supports images from Instagram, which are sent as a media group with a single caption. 📲✨

## Features 🌟

- Downloads videos and audio using the fabulous [yt-dlp](https://github.com/yt-dlp/yt-dlp). 🎧🎬
- Handles Instagram posts using [gallery-dl](https://github.com/mikf/gallery-dl). 📸📲
- Supports sending video and image files on Telegram. 💬📹
- Allows customization of allowed user IDs via Docker environment variables. 🔒
- Supports integration with a custom Telegram Bot API for handling large files. 🚀

## Prerequisites ⚙️

- Docker 🐳
- Docker Compose 🛠️
- Telegram (duh 🫠)

## Ghcr.io Compose Example 🚀

```yaml
version: "3.8"
services:
  yatytb:
    container_name: yatytb
    image: ghcr.io/cchrkk/yatytb:latest
    environment:
      - BOT_TOKEN=${BOT_TOKEN} # REQUIRED: Bot token from BotFather
      - ALLOWED_IDS=${ALLOWED_IDS} # REQUIRED: Set allowed IDs separated by comma
      # Optional:- LOG_TO_FILE=false
      # Optional:- LOG_FILE_PATH=bot.log
    volumes:
      - ./cookies.txt:/app/cookies/cookies.txt  # Optional: Only set if cookies needed
    depends_on:
      - telegram-api

  telegram-api:
    container_name: yatytb-telegram-api
    image: aiogram/telegram-bot-api:latest
    environment:
      - TELEGRAM_API_ID=${TELEGRAM_API_ID} # REQUIRED: Telegram API ID
      - TELEGRAM_API_HASH=${TELEGRAM_API_HASH} # REQUIRED: Telegram API Hash
      - TELEGRAM_BOT_TOKEN=${BOT_TOKEN} # REQUIRED: Bot token
    ports:
      - "8081:8081"
```

## Environment Variables 🔑
Required
- **BOT_TOKEN**: Your Telegram bot token (required for authentication). 🆔 Ask it here [@BotFather](https://t.me/BotFather)
- **ALLOWED_IDS**: A comma-separated list of user IDs authorized to interact with the bot. 🔗Ask yours here [@getmyid_bot](https://t.me/getmyid_bot)
- **LOG_TO_FILE**: Enable this to log the console output to a file if your choice.
- **LOG_FILE_PATH**: Full directory to the .log file.
- **TELEGRAM_API_ID**: Your Telegram API ID (required for the custom Telegram Bot API). 🆔
- **TELEGRAM_API_HASH**: Your Telegram API Hash (required for the custom Telegram Bot API). 🔑

## Create your cookies.txt file 🍪
1. Log in to Instagram/Tiktok/Youtube in your browser. 🌍
2. Export the cookies using a browser extension like [Get cookies.txt LOCALLY](https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc) or ["EditThisCookie"](https://www.editthiscookie.com) . 🔐 ([read more here](https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp))
3. Save the cookies as a `.txt` file, and name it `cookies.txt`. 💾
4. Place this `cookies.txt` file in the project directory and ensure it is mounted as a volume in `/app/cookies/cookies.txt` in the container.

**Note**: If the `cookies.txt` file is not provided, some features (e.g., downloading tiktok/private content/etc.) may not work.

## How It Works ⚡
1. Send a video or post link (YouTube, Instagram) to the bot. 📨
2. The bot downloads the content and sends you the files. ⬇️
3. If the link is an Instagram post with multiple images, the bot will send all images in a single message as a media group. 📸🎨
   
# Demo Pics 🤳

### Instagram Reel - handled by yt-dlp

![image](https://github.com/user-attachments/assets/062420f5-919e-43b5-80dc-d0cc6db04373)

### Instagram Photos Post - handled by gallery-dl

![image](https://github.com/user-attachments/assets/2b7467a7-f201-4123-8941-e36c59fd8052)

### Tiktok Video - handled by yt-dlp

![image](https://github.com/user-attachments/assets/43697ddc-04a6-4b72-9c9f-7bd0c72f0936)

## Contributing 💡
If you want to contribute to this project, feel free to fork the repository and send a pull request with improvements or bug fixes. 🛠️

## License 📜
This project is licensed under the MIT License - see the LICENSE file for details.
