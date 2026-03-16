# Vision CLI — Requirements

## Python Version
Python 3.10 or higher

## Installation

```bash
pip install -r requirements.txt
playwright install chromium
```

## Required Packages

```
rich
groq
ddgs
playwright
beautifulsoup4
requests
wikipedia
easyocr
yfinance
openai
speechrecognition
pyttsx3
edge-tts
textual
pygame
yt-dlp
```

## API Keys

| Service | Required | Get It |
|---|---|---|
| Groq | ✅ (if using Groq) | [console.groq.com](https://console.groq.com) |
| OpenRouter | ✅ (if using OpenRouter) | [openrouter.ai](https://openrouter.ai) |
| Ollama | ✅ (if using Ollama) | [ollama.com](https://ollama.com) — local, no key needed |

## Environment Variables

```bash
# Set before running
export GROQ_API_KEY=your_key_here
export OPENROUTER_API_KEY=your_key_here
export HF_TOKEN=your_token_here      # optional
```

On Windows:
```cmd
set GROQ_API_KEY=your_key_here
set OPENROUTER_API_KEY=your_key_here
```

## Optional System Dependencies

| Tool | Why | Install |
|---|---|---|
| `mpv` | Better audio playback | [mpv.io](https://mpv.io) |
| `ffmpeg` | Required by yt-dlp for audio | [ffmpeg.org](https://ffmpeg.org) |
| `portaudio` | Required for microphone input | `brew install portaudio` / `apt install portaudio19-dev` |

## Running

```bash
# Normal terminal
python vision_cli.py

# Cloud (Google Colab)
# Run directly in a notebook cell — no flags needed
```

## Notes

- Voice input (`/mic on`) only works on local PC, not Colab
- Browser control (Playwright) works in headless mode on Colab
- Image generation uses Pollinations.ai (free, no key) with HuggingFace as fallback
- All persistent data saved to `vision_data.json` and `vision_chats/` folder
