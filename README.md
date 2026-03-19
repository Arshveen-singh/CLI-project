# Vision CLI v1.4.4-beta

**Very Intelligent System I Occasionally Need**

A privacy-first, open-source AI terminal agent built by [Arshveen Singh](https://github.com/Arshveen-singh). Run any LLM from your terminal — with multi-model council debates, self-improving engine, GitHub integration, automation scheduling, skills system, and more.

```
██╗   ██╗██╗███████╗██╗ ██████╗ ███╗   ██╗     ██████╗██╗     ██╗
██║   ██║██║██╔════╝██║██╔═══██╗████╗  ██║    ██╔════╝██║     ██║
██║   ██║██║███████╗██║██║   ██║██╔██╗ ██║    ██║     ██║     ██║
╚██╗ ██╔╝██║╚════██║██║██║   ██║██║╚██╗██║    ██║     ██║     ██║
 ╚████╔╝ ██║███████║██║╚██████╔╝██║ ╚████║    ╚██████╗███████╗██║
  ╚═══╝  ╚═╝╚══════╝╚═╝ ╚═════╝ ╚═╝  ╚═══╝     ╚═════╝╚══════╝╚═╝
```

---

## What is Vision CLI?

Vision CLI is a Python terminal AI agent that grows with you. It's not a coding agent — it's a full AI operating system for your terminal.

- **10 AI providers** — Groq, OpenRouter, Ollama, Together, Fireworks, Mistral, Cerebras, NVIDIA NIM, SambaNova, Bytez
- **LLM Council** — multiple models answer in parallel, Chairman synthesizes the verdict
- **Debate Mode** — models argue FOR/AGAINST/SKEPTIC/DEVIL'S ADVOCATE on any motion
- **Skills System** — load/create custom skill files that change Vision's entire behavior instantly
- **Self-Improving Engine** — tracks usage patterns, suggests automations, optimizes model selection
- **Personal AI Economy** — tracks your time, productivity, weekly AI reports
- **Predictive Automation** — learns your habits, acts before you ask
- **GitHub Integration** — load repos, ask questions, multi-model code review
- **Smart Memory** — auto-extracts facts across sessions, tagged storage
- **Automation Scheduler** — `daily:09:00`, `interval:30m`, `open:url`, `shell:cmd`
- **Real-time streaming** responses
- **Multi-agent task engine** — parallel sub-agents, coordinator merges results
- **Advisor Mode** — brutally honest personal advisor, separate from Vision
- **100% open source, MIT licensed**

---

## Quickstart — Google Colab

```python
# 1 — Install
!pip install openai groq rich yfinance duckduckgo-search requests beautifulsoup4 wikipedia PyGithub

# 2 — Set API key
import os
os.environ["GROQ_API_KEY"] = "gsk_..."           # Groq (free, fastest)
os.environ["OPENROUTER_API_KEY"] = "sk-or-..."   # OR OpenRouter (any model)

# 3 — Run
!python vision_cli_v4.py
```

---

## Quickstart — Local

```bash
git clone https://github.com/Arshveen-singh/Vision-CLI
cd Vision-CLI
pip install -r requirements.txt
python vision_cli_v4.py
```

---

## Providers

| # | Provider | Free Tier | Speed | Best For |
|---|----------|-----------|-------|----------|
| 1 | **Groq** | ✅ Generous | ⚡ Ultra fast | Daily use |
| 2 | **OpenRouter** | ✅ Some models | 🔥 Varies | Access any model |
| 3 | **Ollama** | ✅ Fully free | 🖥️ Local | Privacy, offline |
| 4 | **Together AI** | ✅ Free tier | ⚡ Fast | Open source models |
| 5 | **Fireworks** | ✅ Free tier | ⚡ Fast | Inference speed |
| 6 | **Mistral** | ❌ Paid | 🔥 Fast | Official Mistral |
| 7 | **Cerebras** | ✅ Free tier | ⚡⚡ Groq-speed | LLaMA at extreme speed |
| 8 | **NVIDIA NIM** | ✅ Free credits | 🔥 Fast | Free 405B Llama |
| 9 | **SambaNova** | ✅ Free | 🔥 Fast | Free 405B Llama |
| 10 | **Bytez** | ✅ Free tier | 🔄 Variable | 175k+ HuggingFace models |

---

## Features

### ⚖ LLM Council
```
/council is learning to code more valuable than a degree in 2026?

→ Kimi K2:    deep analytical take
→ DeepSeek:   reasoning-heavy counter
→ Gemini:     fast pragmatic answer
→ LLaMA:      open-source perspective

⚖ Chairman: synthesized verdict with confidence level
```

### ⚔ Debate Mode
```
/debate AI will replace programmers in 5 years

→ Kimi:    FOR    — argues with benchmarks + unit economics
→ Qwen:    AGAINST — strong counter with MIT study data
→ GPT:     SKEPTIC — challenges both sides
→ LLaMA:   DEVIL'S ADVOCATE

⚖ Chairman: judges the debate + gives real answer
```

### 🧠 Skills System

Load built-in skills or create your own:

```bash
/skill list                  # see all skills
/skill load security         # Vision becomes a cybersecurity analyst
/skill load coding           # production-only code, always error-handled
/skill load jarvis           # brief, proactive, "sir" energy
/skill load teacher          # Feynman technique, patient explanations
/skill create myskill        # create your own
/skill clear                 # back to default
```

**Custom skill format** — create `vision_skills/myskill.md`:

```markdown
# Skill: My Skill Name

## Role
What Vision becomes when this skill is active.
Example: "You are a Hinglish-speaking desi tech analyst."

## Rules
- Always do X
- Never do Y
- When asked about Z, respond with...

## Style
Tone, format, length preferences.
Example: "Casual Hinglish, short punchy replies, never formal."
```

Then: `/skill load myskill`

### 🔮 Self-Improving Engine

```bash
/selfimprove     # analyze usage → suggest automations + model optimizations
/economy         # personal AI dashboard — sessions, time, top commands
/weeklyreport    # AI-generated weekly productivity report
/patterns        # show learned predictive patterns
```

Vision tracks every command silently. After enough usage:
- Identifies which models work best per task type
- Suggests automations based on your habits
- Shows your most productive hours and days
- Generates actionable weekly reports

### ⚡ Automation Scheduler

```bash
/automate daily:09:00 | /marketnews | Morning market news
/automate interval:30m | /stock RELIANCE | Portfolio watch
/automate daily:09:00 | open:https://youtube.com | Morning YouTube
/automate daily:08:30 | shell:spotify | Morning music
/automate daily:07:00 | chat:Summarize today's AI news | Telegram briefing

/automations          # list all
/autodelete 1         # remove #1
```

Trigger formats: `daily:HH:MM` — `interval:Nm` — `interval:Nh`
Action formats: `/command` — `open:url` — `shell:cmd` — `chat:prompt`

### 📁 GitHub Integration

```bash
/ghconnect                           # connect GitHub token
/myrepos                             # list your repos
/repoload Arshveen-singh/Vision-CLI  # load repo into context
/repofile src/main.py                # read specific file
/repoask how does auth work?         # ask about loaded repo
/reporeview                          # Council reviews codebase
/commit "feat: add skills"           # stage all → commit → push
```

Council + GitHub = multi-model PR review with chairman verdict.

### 📊 Stocks

```bash
/stock RELIANCE          # live NSE price, P/E, 52W range, sector
/stock AAPL              # US stocks work too
/stocks banking          # full sector overview
/recommend growth stocks for 2026
/impact Russia-Ukraine war on markets
/portfolio add TCS 10 3800
/portfolio view          # live P&L dashboard
/marketnews              # latest headlines
```

Indian sectors: `banking` `it` `pharma` `auto` `tata` `energy` `fmcg` `adani` `smallcap`

---

## Full Command Reference

```
── AI ──────────────────────────────────
/model          Switch model
/provider       Switch provider
/clear          Clear conversation + session context
/stream         Toggle streaming
/refresh        Redraw input box (Colab fix)

── Skills 🧠 ────────────────────────────
/skill list
/skill load <name>
/skill unload <name>
/skill create <name>
/skill edit <name>
/skill reload <name>
/skill active
/skill clear

── Self-Improving 🔮 ────────────────────
/economy
/weeklyreport
/selfimprove
/patterns

── Memory ───────────────────────────────
/memory add <key> <value> [#tag]
/memory view [#tag]
/memory forget <key>

── Chats ────────────────────────────────
/chats save <name>
/chats list
/chats load <#>

── Music 🎵 ─────────────────────────────
/play <song>
/pause  /resume  /stop  /skip
/queue <song>
/nowplaying
/volume <0-100>

── Timer ────────────────────────────────
/timer <minutes>
/stopwatch start/stop/lap/check

── Image ────────────────────────────────
/imagine <prompt>
/vision <image_path> [question]

── Advisor ──────────────────────────────
/advisor <message>
/goal add <goal>
/goal list
/goal done <#>

── Council ⚖ ────────────────────────────
/council <query>
/debate <motion>
/councilsetup

── Multi-Agent 🤖 ───────────────────────
/agent <complex task>

── GitHub 📁 ────────────────────────────
/ghconnect
/myrepos
/repoload <user/repo>
/repofile <path>
/repoask <question>
/reporeview
/commit <message>

── Integrations 🔗 ──────────────────────
/telegramsetup
/telegram <message>
/telegramread
/emailsetup
/email <to> | <subject> | <body>

── Automation ⚡ ─────────────────────────
/automate <trigger> | <action> | <desc>
/automations
/autodelete <#>

── Stocks ───────────────────────────────
/stock <SYMBOL>
/stocks <sector>
/recommend <query>
/impact <event>
/portfolio add <SYM> <qty> <price>
/portfolio view
/portfolio remove <SYM>
/marketnews [query]

── Code ─────────────────────────────────
/code <file.py> <what to build>
/html <file.html> <what to build>
/doc  <file.md> <what to write>
/runfile <file>
/debug <file>
/git <command>

── Tools ────────────────────────────────
/search <query>
/scrape <url>
/browse <url>
/wiki <topic>
/weather <city>
/ocr <image>
/artifact <name>

── System ───────────────────────────────
/help
/exit  /q  /quit
```

---

## Roadmap

| Version | Status | Features |
|---------|--------|----------|
| v3.5 | ✅ Done | 9 providers |
| v3.6 | ✅ Done | Smart auto-memory, tagged memory |
| v3.7 | ✅ Done | Real-time streaming, vision input |
| v3.8 | ✅ Done | GitHub integration |
| v3.9 | ✅ Done | Telegram, Email, Automation scheduler |
| v4.0 | ✅ Done | Multi-agent task engine |
| v4.1 | ✅ Done | Self-improving engine, economy, predictive automation |
| v4.2 | ✅ Done | Skills system, refresh hotkey, identity fix, advisor context fix |
| v4.3 | ✅ Done | Rolling context summarization, auto web search in chat |
| v4.4 | 🔲 Open | Wake word detection, always-on mode |
| v4.5 | 🔲 Open | Flutter mobile companion app |

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) — adding a provider is 15 lines, adding an integration is 30.

---

## License

MIT — free forever.

Built by **Arshveen Singh** • Delhi, India
