# Vision CLI

```
██╗   ██╗██╗███████╗██╗ ██████╗ ███╗   ██╗     ██████╗██╗     ██╗
██║   ██║██║██╔════╝██║██╔═══██╗████╗  ██║    ██╔════╝██║     ██║
██║   ██║██║███████╗██║██║   ██║██╔██╗ ██║    ██║     ██║     ██║
╚██╗ ██╔╝██║╚════██║██║██║   ██║██║╚██╗██║    ██║     ██║     ██║
 ╚████╔╝ ██║███████║██║╚██████╔╝██║ ╚████║    ╚██████╗███████╗██║
  ╚═══╝  ╚═╝╚══════╝╚═╝ ╚═════╝ ╚═╝  ╚═══╝     ╚═════╝╚══════╝╚═╝
```

**Your terminal. Now with superpowers.**

A fast, beautiful, memory-aware AI agent that transforms your command line into a personal JARVIS. Built with Rich UI, Groq-speed inference, and India-first finance tools.

One file. Zero bloat. Runs instantly.

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Groq](https://img.shields.io/badge/Groq-Powered-F55036?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-00e5cc?style=for-the-badge)
![Version](https://img.shields.io/badge/Version-3.0.0-7b4fff?style=for-the-badge)
![Made in India](https://img.shields.io/badge/Made%20in-India-FF9933?style=for-the-badge)

---

## ✦ What is Vision CLI?

Vision CLI is a one-file AI agent for your terminal. It combines real-time web search, Indian stock market data, a personal advisor, persistent memory, image generation, voice control, and a full code assistant — all wrapped in a stunning Rich console with teal war-room aesthetics.

---

## ⚡ Quick Start

```bash
git clone https://github.com/Arshveen-singh/CLI-project.git
cd CLI-project
pip install -r requirements.txt
playwright install chromium
export GROQ_API_KEY=your_key_here
python vision_cli.py
```

Get your free Groq key → [console.groq.com](https://console.groq.com)

---

## ✦ Features

### 🤖 AI Chat
- 3 providers — **Groq**, **OpenRouter**, **Ollama**
- Models: Kimi K2, Qwen 3 32B, LLaMA 3.3 70B, Claude, Gemini, DeepSeek + more
- Switch provider or model anytime mid-session
- History trimming + rate limiting built in

### 🧠 Persistent Memory
- Remembers facts across every session
- Memory shared across chat, advisor, and finance modes
- Add, view, forget memories anytime

### 📈 Indian Stock Market
- Live NSE/BSE prices + US stocks (AAPL, TSLA, MSFT etc.)
- 9 sector dashboards (banking, IT, pharma, auto, Tata, Adani...)
- Portfolio tracker with real-time P&L
- AI stock recommendations + war/event market impact analysis
- Live market news

### 🎯 Personal Advisor
- Brutally honest business partner and life advisor
- Remembers your goals, portfolio, and past conversations
- Evaluates ideas, tracks goals, gives real financial advice
- Sees context from your main chat automatically

### 🛠 Developer Tools
- Generate Python, HTML, and Markdown files
- Run, debug, and fix code with AI
- Git integration
- Inline Python execution

### 🌐 Web Tools
- Web search, scraping, headless browser, Wikipedia, weather

### 🎨 Media
- AI image generation (Pollinations.ai + HuggingFace fallback)
- Stream any song via YouTube
- OCR — extract text from images

### ⏱ Productivity
- Study timer, stopwatch, voice input toggle
- Save and restore conversations
- Artifact maker — save AI replies as files

---

## 📋 Commands

```
── AI ──────────────────────────────────────────────────────
/model                    Switch model
/provider                 Switch provider
/clear                    Clear chat history

── Memory ──────────────────────────────────────────────────
/memory add <key> <val>   Save a memory
/memory view              View all memories
/memory forget <key>      Delete a memory

── Advisor ─────────────────────────────────────────────────
/advisor <message>        Personal advisor
/goal add/list/done       Goal tracker

── Stocks ──────────────────────────────────────────────────
/stock <SYMBOL>           Live price (NSE/BSE/US)
/stocks <sector>          Sector dashboard
/recommend <query>        AI stock picks
/impact <event>           Market impact analysis
/portfolio add/view       Portfolio + P&L
/marketnews               Market news

── Code ────────────────────────────────────────────────────
/code <file> <prompt>     Generate .py
/html <file> <prompt>     Generate .html
/doc  <file> <prompt>     Generate .md
/runfile <file>           Run a file
/debug <file>             AI fixes a file
/run <code>               Inline Python
/git <command>            Git command

── Tools ───────────────────────────────────────────────────
/search   /scrape   /browse   /wiki   /weather
/imagine  /play     /ocr      /artifact
/chats save/list/load
/mic on/off   /timer   /stopwatch
/help   /exit
```

---

## 🔑 API Keys

| Service | Required | Free |
|---|---|---|
| [Groq](https://console.groq.com) | If using Groq | ✅ Yes |
| [OpenRouter](https://openrouter.ai) | If using OpenRouter | ✅ Free tier |
| Ollama | If running locally | ✅ Local |

---

## 🗂 Project Structure

```
CLI-project/
├── vision_cli.py       — The entire CLI (one file)
├── vision_data.json    — Persistent data (auto-created)
├── vision_chats/       — Saved conversations (auto-created)
├── requirements.txt    — pip dependencies
├── SETUP.md            — Setup guide
├── REQUIREMENTS.md     — Requirements docs
├── CHANGELOG.md        — Version history
├── CONTRIBUTING.md     — How to contribute
├── .gitignore
└── LICENSE
```

---

## 🛠 Built With

[Rich](https://github.com/Textualize/rich) · [Groq](https://groq.com) · [yfinance](https://github.com/ranaroussi/yfinance) · [Playwright](https://playwright.dev) · [EasyOCR](https://github.com/JaidedAI/EasyOCR) · [yt-dlp](https://github.com/yt-dlp/yt-dlp) · [DuckDuckGo Search](https://github.com/deedy5/ddgs) · [Pollinations.ai](https://pollinations.ai)

---

## 📄 License

MIT — do whatever you want with it.

---

## 👨‍💻 Author

**Arshveen Singh**
[Arshveensingh@proton.me](mailto:Arshveensingh@proton.me) · [github.com/Arshveen-singh](https://github.com/Arshveen-singh)

---

> Built on a Sunday. On dad's PC. While listening to Zafarnama. 💀
