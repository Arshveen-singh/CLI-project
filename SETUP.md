# Vision CLI — Setup Guide

## Quick Start (5 minutes)

### 1. Clone the repo
```bash
git clone https://github.com/Arshveen-singh/CLI-project.git
cd CLI-project
```

### 2. Install dependencies
```bash
pip install rich groq ddgs playwright beautifulsoup4 requests wikipedia easyocr yfinance openai speechrecognition pyttsx3 pygame yt-dlp
playwright install chromium
```

### 3. Set your API key
**Linux / Mac:**
```bash
export GROQ_API_KEY=your_key_here
```

**Windows:**
```cmd
set GROQ_API_KEY=your_key_here
```

**Google Colab:**
```python
import os
os.environ["GROQ_API_KEY"] = "your_key_here"
```

### 4. Run it
```bash
python vision_cli.py
```

---

## Getting API Keys

### Groq (Free, Recommended)
1. Go to [console.groq.com](https://console.groq.com)
2. Sign up / Log in
3. Click **API Keys** → **Create new key**
4. Copy and set as `GROQ_API_KEY`

### OpenRouter (Optional)
1. Go to [openrouter.ai](https://openrouter.ai)
2. Sign up → **Keys** → **Create key**
3. Set as `OPENROUTER_API_KEY`



---

## Platform-Specific Setup

### Windows
```cmd
# Install Python from python.org first, then:
pip install rich groq ddgs playwright beautifulsoup4 requests wikipedia easyocr yfinance openai speechrecognition pyttsx3 pygame yt-dlp
playwright install chromium
set GROQ_API_KEY=your_key_here
python vision_cli.py
```

> **Note:** For voice input on Windows, also install:
> ```cmd
> pip install pyaudio
> ```
> If pyaudio fails, download the wheel from [here](https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio)

### Linux / Mac
```bash
# Ubuntu/Debian — install portaudio first for mic support
sudo apt install portaudio19-dev ffmpeg
pip install -r requirements.txt
playwright install chromium
```

### Google Colab
```python
# Cell 1 — Install
!pip install rich groq ddgs playwright beautifulsoup4 requests wikipedia easyocr yfinance openai pygame yt-dlp -q
!playwright install chromium

# Cell 2 — Set API key
import os
os.environ["GROQ_API_KEY"] = "your_key_here"

# Cell 3 — Run directly in cell (no !python needed)
# Paste the full vision_cli.py code and run
```
> **Note:** Voice input and custom terminal modes don't work on Colab

---

## First Run Walkthrough

When you run `vision_cli.py` you'll see:

```
1. Select AI Provider  →  choose Groq (option 1)
2. Select Model        →  choose Kimi K2 (option 1) or any model
3. Help menu appears   →  you're ready!
```

**Try these first:**
```
/weather Delhi          → test weather widget
/stock TATAMOTORS       → test Indian stocks
/stock AAPL             → test US stocks
/wiki India             → test Wikipedia
/search latest AI news  → test web search
/advisor hello          → meet your personal advisor
/memory add name Arsh   → test persistent memory
/imagine a sunset       → test image generation
/timer 25               → 25 min study timer
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError` | Run `pip install <module_name>` |
| `playwright not found` | Run `playwright install chromium` |
| `GROQ_API_KEY not set` | Set env variable or enter key when prompted |
| `Stock not found` | Use NSE symbol e.g. `TATAMOTORS`, `INFY`, or US symbol e.g. `AAPL` |
| `Mic not working` | Install `pyaudio` and check mic permissions |
| `Image gen failed` | Pollinations.ai may be slow — wait and retry, or add HF_TOKEN |
| `easyocr slow first run` | Downloads model on first use — be patient |

---

## Features Overview

| Command | Description |
|---|---|
| Chat | Just type anything |
| `/advisor <msg>` | Personal advisor mode |
| `/stock <SYM>` | Live stock price (Indian + US) |
| `/stocks <sector>` | Browse sector stocks |
| `/portfolio add/view` | Track your investments |
| `/memory add/view` | Persistent memory across sessions |
| `/imagine <prompt>` | AI image generation |
| `/weather <city>` | Weather widget |
| `/search <query>` | Web search |
| `/wiki <query>` | Wikipedia lookup |
| `/code <file> <prompt>` | Generate Python files |
| `/timer <minutes>` | Study countdown timer |
| `/mic on` | Voice input (PC only) |
| `/play <song>` | Play music via YouTube |

---

## Contact
**Arshveen Singh** — [Arshveensingh@proton.me](mailto:Arshveensingh@proton.me)
GitHub: [@Arshveen-singh](https://github.com/Arshveen-singh)
