# Vision CLI v2.0 — Project Glasseye

**Very Intelligent System I Occasionally Need**


██╗   ██╗██╗███████╗██╗ ██████╗ ███╗   ██╗     ██████╗██╗     ██╗
██║   ██║██║██╔════╝██║██╔═══██╗████╗  ██║    ██╔════╝██║     ██║
██║   ██║██║███████╗██║██║   ██║██╔██╗ ██║    ██║     ██║     ██║
╚██╗ ██╔╝██║╚════██║██║██║   ██║██║╚██╗██║    ██║     ██║     ██║
 ╚████╔╝ ██║███████║██║╚██████╔╝██║ ╚████║    ╚██████╗███████╗██║
  ╚═══╝  ╚═╝╚══════╝╚═╝ ╚═════╝ ╚═╝  ╚═══╝     ╚═════╝╚══════╝╚═╝
                                                                 
                                                                 
> "Vision sees everything."

A privacy-first, open-source autonomous developer OS built by
[Arshveen Singh](https://github.com/Arshveen-singh). 
The ground-up rebuild of Vision CLI v1.4.4 — done right this time.
Modular. Portable. Self-evolving. Inspired by Claude Mythos and
Project Glasswing.

---

## What's new in v2.0?

v1.4.4 was a proof of concept. v2.0 is the real thing.

- Proper modular architecture (not one giant file)
- Shadow sandbox — Docker execution, you see only success
- Obsidian vault memory — Vision's brain lives in your notes
- Multi-agent debate — two AIs argue until code is bulletproof
- Telegram approval gateway — approve risky actions from phone
- Claude Code style TUI with pixel cat mascot =^.^=
- Hybrid routing across 17 providers — free tier first, always
- Runs fully portable from a USB drive
- Zero cloud dependency for memory and skills

---

## Quickstart

```bash
git clone https://github.com/Arshveen-singh/Vision-CLI
cd Vision-CLI
pip install -r requirements.txt
python main.py start
```

First run → setup screen asks for API keys  
Then → model selector → boot sequence → Vision is live

---

## Providers (17)

| # | Provider | Free | Best Model |
|---|----------|------|------------|
| 1 | Groq | ✅ | Kimi K2 |
| 2 | OpenRouter | ✅ | DeepSeek R1 |
| 3 | Cerebras | ✅ | LLaMA 3.3 70B |
| 4 | SambaNova | ✅ | LLaMA 405B |
| 5 | Together | ✅ | Qwen 2.5 72B |
| 6 | Fireworks | ✅ | DeepSeek R1 |
| 7 | NVIDIA | ✅ credits | LLaMA 405B |
| 8 | Bytez | ✅ | 175k+ HuggingFace |
| 9 | Ollama | ✅ local | Qwen 2.5 |
| 10 | OpenAI | ❌ | GPT-4o |
| 11 | Anthropic | ❌ | Claude Sonnet |
| 12 | Google | 🟡 | Gemini Flash |
| 13 | xAI | ❌ | Grok 3 |
| 14 | DeepSeek | ❌ | R1 |
| 15 | Mistral | ❌ | Codestral |
| 16 | Cohere | ❌ | Command R+ |
| 17 | Perplexity | ❌ | Sonar |

Switch anytime with `/model` or `/provider`

---

## Core Features

### =^.^= Vibe Check TUI
Claude Code style terminal interface. Pure ANSI,
no heavy frameworks. Pixel cat mascot reacts to
every state. Feels alive.

### 🧠 Neural Vault Memory
Vision's memory lives in your Obsidian vault as
plain markdown files. Read it. Edit it. Delete it.
Full transparency, zero cloud.

### 🐳 Shadow Sandbox
Every risky command runs in a Docker container
first. You only see successful results applied
to your real filesystem. Never breaks anything.

### ⚔ Multi-Agent Debate
/debate <your code>
→ Builder:  writes clean implementation
→ Critic:   attacks security + edge cases
→ Round 2:  Builder defends + fixes
→ Verdict:  improved code + full debate log

### 📱 Telegram Gateway
Every risky action sends an approval request to
your phone. Approve or reject from anywhere.
Vision waits. Asynchronously.

### 🔀 Hybrid Model Router
Simple tasks → fast free model (Groq/Cerebras)  
Complex tasks → smart model (DeepSeek R1/Kimi K2)  
Target: 90% cost reduction vs always using big models

### 🐚 Natural Language Shell

show me all python files modified today
Vision suggests: find . -name "*.py" -mtime -1
Run it? (y/n)


---

## Commands
── Core ─────────────────────────────────
/model          Switch model mid-conversation
/provider       Switch provider
/key add        Add new API key live
/key list       Show active providers
/setup          Re-run first time setup
/memory         Show what Vision remembers
── Agents ───────────────────────────────
/debate <code>  Multi-agent code review
/research <q>   Deep recursive web research
/scan           Security scan your own code
── System ───────────────────────────────
/checkpoint     Save current environment state
/rollback       Rewind to last checkpoint
/stop           Stop current browser/task
/exit           Save session memory + quit

---

## Architecture
vision-cli/
├── core/           # router, sandbox, memory, checkpoints
├── agents/         # coder, critic, researcher, security
├── interfaces/     # tui, voice, telegram gateway
├── integrations/   # github, browser, iot, life os
├── skills/         # auto-learned tool registry
└── main.py         # entry point

---

## Roadmap

| Version | Status | Features |
|---------|--------|----------|
| v1.4.4 | ✅ Done | Original — 10 providers, council, debate, skills |
| v2.0 | 🔨 Building | Ground up rebuild — modular, sandbox, vault memory |
| v2.1 | 🔲 Open | Voice interface, wake word "Vision" |
| v2.2 | 🔲 Open | Life OS — calendar, Gmail briefings |
| v2.3 | 🔲 Open | Self-modifying codebase |
| v3.0 | 🔲 Dream | Weekend startup mode, zero-day pattern hunter |

---

## Contributing

Adding a provider = 15 lines.  
Adding a skill = one YAML file.  
See [CONTRIBUTING.md](CONTRIBUTING.md)

---

## Inspiration

Inspired by Claude's Mythos persona and Anthropic's
Project Glasswing — the belief that powerful AI
tooling should belong to every developer, not just
40-partner consortiums with $100M budgets.

---

## License

MIT — free forever.

Built by **Arshveen Singh** • Delhi, India  
Contact: Arshveensingh@proton.me
