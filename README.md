![image](https://github.com/user-attachments/assets/20eadb48-f19c-44c4-b17c-b7e96beaa504)
# Yet Another yt-dlp Telegram Bot 🎥📥

This project is a Telegram bot that allows you to download videos and audio using [yt-dlp](https://github.com/yt-dlp/yt-dlp) or [gallery-dl](https://github.com/mikf/gallery-dl) directly on Telegram. You can send links of videos and posts from platforms like YouTube and Instagram, and the bot will send you the files as media. The bot also supports images from Instagram, which are sent as a media group with a single caption. 📲✨

## Features 🌟

- Downloads videos and audio using the fabulous [yt-dlp](https://github.com/yt-dlp/yt-dlp). 🎧🎬
- Handles Instagram posts using [gallery-dl](https://github.com/mikf/gallery-dl). 📸📲
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
```

## Environment Variables 🔑
- **BOT_TOKEN**: Your Telegram bot token (required for authentication). 🆔
  Ask it here [@BotFather](https://t.me/BotFather)
- **ALLOWED_IDS**: A comma-separated list of user IDs authorized to interact with the bot. 🔗Ask yours here [@getmyid_bot](https://t.me/getmyid_bot)
- **LOG_TO_FILE**: Enable this to log the console output to a file if your choice.
- **LOG_FILE_PATH**: Full directory to the .log file 

## Create your cookies.txt file 🍪
1. Log in to Instagram/Tiktok/Youtube in your browser. 🌍
2. Export the cookies using a browser extension like "EditThisCookie". 🔐
3. Save the cookies as a `.txt` file, and name it `cookies.txt`. 💾
4. Place this `cookies.txt` file and mount the volume in the docker-compose.

## How It Works ⚡
1. Send a video or post link (YouTube, Instagram) to the bot. 📨
2. The bot downloads the content and sends you the files. ⬇️
3. If the link is an Instagram post with multiple images, the bot will send all images in a single message as a media group. 📸🎨
   
# Demo Pics 🤳

### Instagram Reel - handled by yt-dlp

![image](https://github.com/user-attachments/assets/2573f840-121f-4981-bf5e-0611a21b9c95)


### Instagram Photos Post - handled by gallery-dl

![image](https://github.com/user-attachments/assets/e756bb59-fc2e-4cfb-bcff-b20dc1400c80)


### Tiktok Video - handled by yt-dlp

![image](https://github.com/user-attachments/assets/8ed6f77a-1cd9-4f30-bd31-881b55f2a2ab)

## Todo List ✔️
- Use aiogram with local api to handle bigger files easily
- Fix Instagram photos post caption
- Fix Telegram photos post
- More variables to control max file size, max files to download per photos post, custom caption
- Cleanup code
  
## Contributing 💡
If you want to contribute to this project, feel free to fork the repository and send a pull request with improvements or bug fixes. 🛠️

## License 📜
This project is licensed under the MIT License - see the LICENSE file for details.
