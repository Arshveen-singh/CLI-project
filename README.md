# Vision CLI v3.4.5-beta

**Very Intelligent System I Occasionally Need**

A privacy-first, open-source AI terminal OS built by [Arshveen Singh](https://github.com/Arshveen-singh).
17 AI providers. LLM Council. CodeMode. AutoMode. Skills. Automation. Stocks. Advisor.
Free forever.

```
██╗   ██╗██╗███████╗██╗ ██████╗ ███╗   ██╗     ██████╗██╗     ██╗
██║   ██║██║██╔════╝██║██╔═══██╗████╗  ██║    ██╔════╝██║     ██║
██║   ██║██║███████╗██║██║   ██║██╔██╗ ██║    ██║     ██║     ██║
╚██╗ ██╔╝██║╚════██║██║██║   ██║██║╚██╗██║    ██║     ██║     ██║
 ╚████╔╝ ██║███████║██║╚██████╔╝██║ ╚████║    ╚██████╗███████╗██║
  ╚═══╝  ╚═╝╚══════╝╚═╝ ╚═════╝ ╚═╝  ╚═══╝     ╚═════╝╚══════╝╚═╝
```

> ⚠️ v3.4.5 — stable beta. Report bugs via Issues.

---

## Quickstart — Google Colab

```python
# 1 — Install
!pip install openai groq rich yfinance duckduckgo-search requests beautifulsoup4 wikipedia PyGithub

# 2 — Set API key (Groq is free, no credit card)
import os
os.environ["GROQ_API_KEY"] = "gsk_..."

# 3 — Run
!python vision_cli.py
```

## Quickstart — Local

```bash
git clone https://github.com/Arshveen-singh/Vision-CLI
cd Vision-CLI
pip install -r requirements.txt
python vision_cli.py
```

---

## What makes Vision CLI different

| | Vision CLI | Claude Code | Codex | Gemini CLI |
|--|-----------|-------------|-------|------------|
| Providers | **17 (10 free)** | 1 paid | 1 paid | 1 free |
| LLM Council | ✅ **Unique** | ❌ | ❌ | ❌ |
| AutoMode | ✅ **Unique** | ❌ | ❌ | ❌ |
| Skills system | ✅ | ❌ | ❌ | ❌ |
| Test loop | ✅ | ✅ | ✅ | ✅ |
| Folder watch | ✅ | ✅ | ❌ | ❌ |
| Automation OS | ✅ | ❌ | ❌ | ❌ |
| Stocks/Finance | ✅ | ❌ | ❌ | ❌ |
| Free to use | ✅ | ❌ | ❌ | 🟡 |

---

## Providers (17)

| # | Provider | Free | Best Model |
|---|----------|------|------------|
| 1 | **Groq** | ✅ | Kimi K2, Qwen 3 |
| 2 | **OpenRouter** | ✅ | Kimi K2, DeepSeek R1 |
| 3 | **Ollama** | ✅ local | Qwen 2.5, DeepSeek R1 |
| 4 | **Cerebras** | ✅ | LLaMA 3.3 70B |
| 5 | **SambaNova** | ✅ | LLaMA 405B |
| 6 | **Together** | ✅ | Qwen 2.5 72B |
| 7 | **Fireworks** | ✅ | DeepSeek R1 |
| 8 | **OpenAI** | ❌ | GPT-4o, o1 |
| 9 | **Anthropic** | ❌ | Claude Sonnet 4.5 |
| 10 | **Google** | 🟡 | Gemini 2.0 Flash |
| 11 | **xAI** | ❌ | Grok 3 |
| 12 | **DeepSeek** | ❌ | R1 ($0.07/1M) |
| 13 | **Cohere** | ❌ | Command R+ |
| 14 | **Perplexity** | ❌ | Sonar (web-grounded) |
| 15 | **Mistral** | ❌ | Codestral |
| 16 | **NVIDIA** | ✅ credits | LLaMA 405B |
| 17 | **Bytez** | ✅ | 175k+ HuggingFace |

---

## ⚡ CodeMode — `/codemode`

```bash
/codemode              # enter (model selector + skill injection)
/cm run <task>         # generate → run → auto-fix → verify ⭐
/cm test <file>        # pytest → fail → AI fix → rerun ⭐
/cm multifile <task>   # generate 6 files simultaneously ⭐
/cm watch [folder]     # auto-review files on save ⭐
/cm sandbox <task>     # isolated execution
/cm plan <task>        # architecture before code
/cm build <task>       # direct code generation
/cm review <file>      # Critical/High/Medium/Low severity
/cm swarm <task>       # 5 specialist agents in parallel
/cmgit log 5           # last 5 commits + AI explanation ⭐
/cmgit blame <file>    # git blame + AI context ⭐
/codemode off          # exit
```

## ⚡ AutoMode — `/automode`

```bash
/automode                              # enter
/am workflow check RELIANCE daily 9am # natural language → full automation plan
/am chain /stock RELIANCE → /telegram price update → shell:echo done
/am script monitor bitcoin price       # generate standalone script
/am monitor RELIANCE above 1500        # monitoring + Telegram alerts
/automode off                          # exit
```

## ⚖ LLM Council

```bash
/council is Python dying in the age of AI?
/debate AI will replace programmers in 5 years
/council history                    # past verdicts
/council history compare 1 3        # AI comparison of two sessions
```

## 🔍 Web Search

```bash
?bitcoin price today          # instant search (NEW ⭐)
?how to use FastAPI OAuth2    # search + code example
/search latest AI news        # full search
```

## 💾 Sessions

```bash
/session save "my-project"    # save everything (NEW ⭐)
/session load 1               # restore model, skills, CM/AM, history
/session list                 # all saved sessions
```

## 📁 VISION.md

```bash
/vision.md    # create project context file
```

Edit `VISION.md` in your project root. Vision auto-loads it every session:

```markdown
# Vision Project Context
## Stack
Python + FastAPI + PostgreSQL

## Rules
- Always use type hints
- Use pytest for tests

## Important Files
src/auth.py, src/models/user.py

## Run Commands
uvicorn main:app --reload
pytest tests/
```

## 📊 Stocks

```bash
/stock RELIANCE          # live NSE price, P/E, 52W
/stock AAPL              # US stocks
/stocks banking          # full sector (banking/it/pharma/auto/tata/energy)
/portfolio add TCS 10 3800
/portfolio view          # live P&L
/marketnews
```

## ⚡ Automation

```bash
/automate daily:09:00 | /marketnews | Morning news
/automate interval:30m | /stock RELIANCE | Portfolio watch
/automate daily:09:00 | open:https://youtube.com | Morning YouTube
/automate daily:08:30 | shell:spotify | Morning music
/automations
/autodelete 1
/undo
```

## 🧠 Skills

```bash
/skill load security     # CVE ratings, OWASP mindset
/skill load coding       # production code only
/skill load jarvis       # brief + proactive
/skill load teacher      # Feynman technique
/skill create myskill    # custom skill
/skill marketplace       # community skills
/skill install wtv       # install from GitHub
```

## Full Command Reference

```
── NEW v3.4.7 ───────────────────────
?<query>                  instant web search
/session save/load/list   full state persistence
/vision.md                project context file
/cm test <file>           pytest auto-fix loop
/cm multifile <task>      multi-file generation
/cm watch [folder]        folder watcher
/cm sandbox <task>        isolated execution
/cmgit log [n]            commit history + AI
/cmgit blame <file>       blame + AI context

── CodeMode ⚡ ───────────────────────
/codemode  /cm  /codemode off

── AutoMode ⚡ ───────────────────────
/automode  /am  /automode off
/am workflow  /am chain  /am script
/am monitor  /am status  /am workflows
/ammem add/view/forget

── AI ───────────────────────────────
/model  /provider  /clear  /stream
/refresh  /context

── Skills 🧠 ────────────────────────
/skill list/load/unload/create
/skill edit/reload/active/clear
/skill marketplace  /skill install <n>

── Memory ───────────────────────────
/memory add <key> <val> [#tag]
/memory view [#tag]
/memory forget <key>

── Advisor ──────────────────────────
/advisor <msg>
/goal add/list/done

── Council ⚖ ────────────────────────
/council <query>
/debate <motion>
/councilsetup
/council history/view/compare

── Multi-Agent 🤖 ───────────────────
/agent <task>

── GitHub 📁 ────────────────────────
/ghconnect  /myrepos  /reposelect
/repoload  /repofile  /repoask
/repoedit  /reporeview  /commit
/cmgit status  /cmgit diff  /cmcommit

── Automation ⚡ ─────────────────────
/automate <trigger> | <action> | <desc>
/automations  /autodelete  /undo

── Stocks ───────────────────────────
/stock  /stocks  /recommend  /impact
/portfolio  /marketnews

── Economy 📊 ───────────────────────
/economy  /weeklyreport
/selfimprove  /patterns

── Export ───────────────────────────
/export [label]

── API 🌐 ───────────────────────────
/api  (or --api flag)

── Tools ────────────────────────────
/search  /scrape  /browse  /wiki
/weather  /artifact  /timer  /stopwatch

── Code ─────────────────────────────
/code  /html  /doc  /runfile  /debug  /git

── System ───────────────────────────
/help  /exit  /q  /quit
```

---

## Roadmap

| Version | Status | Features |
|---------|--------|----------|
| v3.0–v3.9 | ✅ | Core rewrite → GitHub → Automation → Streaming |
| v1.4.4-beta | ✅ | CodeMode, AutoMode, Skills, Council History |
| v3.4.5-beta | ✅ | 17 providers, test loop, folder watch, sessions, VISION.md |
| v4.0.0 | 🔲 | pip install, local filesystem awareness |
| v4.1.0 | 🔲 | VS Code extension, IDE integration |
| v4.2.0 | 🔲 | Flutter mobile app |
| v5.0.0 | 🔲 | v2 architecture, proper test suite |

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) — adding a provider is 15 lines.
See [INTEGRATIONS.md](Integrations.md) — WhatsApp, Discord, Calendar, Notion, Spotify.
See [Skills-guide.md](Skills-guide.md) — create and share custom skills.

---

## License

MIT — free forever.

Built by **Arshveen Singh** • Delhi, India
Contact: Arshveensingh@proton.me
