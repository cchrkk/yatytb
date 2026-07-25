# Yet Another yt-dlp Telegram Bot 🎥📥

This project is a Telegram bot that allows you to download videos and audio using [yt-dlp](https://github.com/yt-dlp/yt-dlp) or [gallery-dl](https://github.com/mikf/gallery-dl) directly on Telegram. You can send links of videos and posts from platforms like YouTube and Instagram, and the bot will send you the files as media. The bot also supports images from Instagram, which are sent as a media group with a single caption. 📲✨

## Features 🌟

- Downloads videos and audio using [yt-dlp](https://github.com/yt-dlp/yt-dlp) with EJS challenge solving 🎧🎬
- Handles Instagram posts using [gallery-dl](https://github.com/mikf/gallery-dl) 📸📲
- Supports sending video and image files on Telegram 💬📹
- **Local Bot API** (`yatytb-tg-api`) — bypass the 50 MB Telegram upload limit 🚀
- `/start` and `/help` commands
- Download queue (one file at a time)
- Cookie auth for restricted sites 🍪
- Docker Compose ready 🐳

## Prerequisites ⚙️

- Docker 🐳
- Docker Compose 🛠️
- Telegram (duh 🫠)
- API ID and API Hash from [my.telegram.org/apps](https://my.telegram.org/apps)

## Docker Compose 🚀

```yaml
services:
  yatytb-tg-api:
    container_name: yatytb-tg-api
    image: aiogram/telegram-bot-api:latest
    environment:
      - TELEGRAM_API_ID=${TELEGRAM_API_ID}
      - TELEGRAM_API_HASH=${TELEGRAM_API_HASH}
    volumes:
      - yatytb-tg-api-data:/data
    restart: always

  yatytb:
    container_name: yatytb
    image: ghcr.io/cchrkk/yatytb:latest
    depends_on:
      - yatytb-tg-api
    environment:
      - BOT_TOKEN=${BOT_TOKEN}
      - ALLOWED_IDS=${ALLOWED_IDS}
      - BASE_URL=http://yatytb-tg-api:8081/bot{token}
      - MAX_FILE_SIZE_MB=2000
      - LOG_TO_FILE=false
      - COOKIES_PATH=/app/cookies/cookies.txt
      - DOWNLOAD_DIR=/app/downloads
    volumes:
      - ./cookies.txt:/app/cookies/cookies.txt
    restart: always
    stop_grace_period: 30s
    stop_signal: SIGTERM

volumes:
  yatytb-tg-api-data:
```

## Environment Variables 🔑

| Variable | Required | Default | Description |
|---|---|---|---|
| `BOT_TOKEN` | ✅ | — | Token from [@BotFather](https://t.me/BotFather) |
| `TELEGRAM_API_ID` | ✅ | — | From [my.telegram.org/apps](https://my.telegram.org/apps) |
| `TELEGRAM_API_HASH` | ✅ | — | From [my.telegram.org/apps](https://my.telegram.org/apps) |
| `ALLOWED_IDS` | ✅ | — | Comma-separated user IDs allowed to use the bot |
| `BASE_URL` | ❌ | — | Local Bot API URL (`http://yatytb-tg-api:8081/bot{token}`) |
| `MAX_FILE_SIZE_MB` | ❌ | 2000 | Max download size (Telegram upload limit is 50 MB without local API) |
| `COOKIES_PATH` | ❌ | `/app/cookies/cookies.txt` | Path to cookies.txt |
| `DOWNLOAD_DIR` | ❌ | `/app/downloads` | Download directory |
| `LOG_TO_FILE` | ❌ | `false` | Enable file logging |
| `LOG_FILE_PATH` | ❌ | `bot.log` | Log file path |

### Finding your IDs

- Your user ID: ask [@getmyid_bot](https://t.me/getmyid_bot)
- Chat ID (for groups): use `/start` in a group and check the bot logs

## Passing Cookies 🍪

### Why Pass Cookies?
Passing cookies to `yt-dlp` or `gallery-dl` is useful for:
1. Bypassing login requirements when an extractor doesn't support explicit login functionality.
2. Handling CAPTCHA challenges on certain websites (e.g., YouTube, CloudFlare).

### Export from browser (easy way)
Use these extensions to download the cookies.txt file:
- **[Get cookies.txt LOCALLY](https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc?pli=1)** for Chromium-based browsers
- **[cookies.txt](https://addons.mozilla.org/en-US/firefox/addon/cookies-txt)** for Firefox

## How It Works ⚡

1. Send a video or post link (YouTube, Instagram) to the bot 📨
2. The bot downloads the content and sends you the files ⬇️
3. If the link is an Instagram post with multiple images, the bot will send all images in a single message as a media group 📸🎨

## Demo Pics 🤳

### Instagram Reel
![image](https://github.com/user-attachments/assets/2573f840-121f-4981-bf5e-0611a21b9c95)

### Instagram Photos Post
![image](https://github.com/user-attachments/assets/e756bb59-fc2e-4cfb-bcff-b20dc1400c80)

### Tiktok Video
![image](https://github.com/user-attachments/assets/8ed6f77a-1cd9-4f30-bd31-881b55f2a2ab)

## Contributing 💡

If you want to contribute to this project, feel free to fork the repository and send a pull request with improvements or bug fixes. 🛠️

## License 📜

This project is licensed under the MIT License - see the LICENSE file for details.
