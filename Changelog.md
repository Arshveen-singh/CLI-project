# Changelog

All notable changes to Vision CLI are documented here.
Format inspired by [Keep a Changelog](https://keepachangelog.com).

---

## [1.4.4-beta] — 2026-03-19

### Added — CodeMode (`/codemode`, `/cm`)
- New dedicated developer environment with a full ASCII banner on entry
- `CODEMODE_SYSTEM_PROMPT` — separate system prompt for CodeMode, distinct from the skill file
  - Enforces: no pseudocode, error handling on every function, inline comments always
  - Security mindset: silently checks every response for hardcoded secrets, injection vectors
  - Structured output format: root cause → code → run command → what to test → next step
  - Identity: responds as "Vision CM", never leaks underlying model
- `CODEMODE_SKILL` — `.md` skill file stacked on top of system prompt for additional context
- Input prompt changes from `[YOU] →` to `[YOU:CM] →` when active
- Coding-specific model selector on entry — ranked by provider with Free/Paid tags
- API key setup check on first enter — guides user to get key if missing

### Added — CodeMode Sub-modes
| Command | What it does |
|---------|-------------|
| `/cm plan <task>` | Architecture diagram + file tree + numbered steps + risks before any code |
| `/cm build <task>` | Full production code generation |
| `/cm review <file>` | Deep review with Critical / High / Medium / Low severity ratings |
| `/cm debug <file>` | Root cause in one sentence + fix |
| `/cm refactor <file>` | Refactor in-place, behavior unchanged |
| `/cm swarm <task>` | 5 specialist agents in parallel |
| `/cm swarm-select <task>` | Pick a different model per swarm agent |
| `/cm search <query>` | Coding-specific web search with code examples |

### Added — Agent Swarm
- 5 specialist roles run in parallel threads: Architect, Security, Reviewer, Optimizer, TestWriter
- Each agent gets a role-specific system directive + the shared CodeMode system prompt
- Coordinator (current model) merges all results into a final synthesized verdict
- `/cm swarm-select` lets you assign a different model to each agent role

### Added — GitHub Improvements
- `/reposelect` — interactive numbered repo picker (replaces manual `user/repo` typing)
- `/repoload` with no argument now opens the interactive picker
- `/repoedit <path> | <instruction>` — AI edits a file from the loaded repo in-place
  - Shows `+N / -N` line diff before writing
  - Options: save locally / save + push to GitHub / cancel
  - Auto-generates conventional commit message on push
- `/repoask` now uses `CODEMODE_SYSTEM_PROMPT` when in CodeMode
- Repo load now also fetches `.css`, `.html`, `.sh`, `.gitignore`, `.env.example` files
- Loaded repo auto-saved to CM memory when CodeMode is active

### Added — File Editing
- `/apply` — writes last generated code block directly to disk (no copy-paste)
- `/apply <filename>` — write to a specific file
- `/edit <file> <instruction>` — AI edits an existing local file in-place, shows diff

### Added — CM Memory
- Separate memory namespace for CodeMode, independent of main Vision memory
- `/cmmem add <key> <val>` — save project context (stack, patterns, decisions)
- `/cmmem view` — display all CM memories in a table
- `/cmmem forget <key>` — delete a CM memory
- Injected into all CodeMode prompts automatically

### Added — CM Git Commands
- `/cmgit status` — git status with AI-suggested commit message
- `/cmgit diff` — git diff with plain-English explanation of every change
- `/cmcommit` — auto-generates conventional commit message and pushes
- `/cmcommit "message"` — uses provided message and pushes

### Added — Auto Web Search in CodeMode
- Queries containing "how to", "docs for", "npm", "pip", "library for", "install", "syntax for" auto-trigger DuckDuckGo search
- Returns synthesized answer with minimal working code example and source link
- Bypasses normal chat path — faster for lookup queries

### Changed
- All CodeMode API calls now use `CODEMODE_SYSTEM_PROMPT` as system message (previously used `CODEMODE_SKILL` directly)
- Main chat panel border turns green in CodeMode instead of blue
- `actionable_error()` used throughout CodeMode instead of raw exception strings

---

## [4.4.0] — 2026-03-15

### Added
- **Setup wizard** — runs on first launch only, guides through provider selection, API key entry, and feature overview
- **`/export [label]`** — exports full session (chat, council verdict, agent results, memories, goals, portfolio) to a dated markdown file
- **`/undo`** — undoes last memory add, automation add, or goal add
- **`/undo history`** — shows the undo stack (last 10 reversible actions)
- **Multi-session Council history** — every council and debate verdict saved persistently
  - `/council history` — list all past sessions
  - `/council history view <#>` — read full verdict
  - `/council history compare <#> <#>` — AI comparison of two past verdicts
- **Skill marketplace** — `/skill marketplace` browses GitHub-hosted community skills, `/skill install <n>` downloads and installs
- **Local API mode** — `/api` or `python vision_cli.py --api` starts a Flask server on `localhost:7842`
  - Endpoints: `POST /chat`, `POST /advisor`, `GET /memory`, `POST /memory`, `GET /stock/<SYM>`, `GET /status`
  - 100% local — no cloud, no external server required
- **Auto web search** — detects uncertainty phrases in Vision's reply ("I don't know", "my knowledge cutoff") and auto-searches DuckDuckGo, then enhances the answer with sources

### Fixed
- `actionable_error()` — all API errors now show human-readable fix suggestions instead of raw tracebacks
- `vision_data.json` auto-archives at 5MB and trims aggressively — prevents unbounded file growth
- `load_data()` now migrates old data files by adding missing keys, prevents crashes on version upgrade

---

## [4.3.0] — 2026-03-12

### Added
- **Rolling context summarization** — replaces the hard 20-message trim
  - `MAX_HISTORY = 40` messages before compression kicks in
  - Oldest 20 messages compressed into ~200 word summary block (background thread, never blocks)
  - Last 20 messages always kept verbatim
  - Separate rolling summaries for main chat and advisor
  - Summaries chain — older context stacks, nothing discarded
- **`/context`** — shows live context window status, message counts, summary size, compression settings

### Fixed
- `/clear` now resets rolling summaries, council verdict, and agent result — full fresh session

---

## [4.2.0] — 2026-03-10

### Added
- **Skills system** — loadable `.md` files that reshape Vision's entire behavior
  - 5 built-in skills auto-created on first run: `coding`, `security`, `research`, `teacher`, `jarvis`
  - `/skill list`, `/skill load <n>`, `/skill unload <n>`, `/skill create <n>`, `/skill edit <n>`, `/skill reload <n>`, `/skill active`, `/skill clear`
  - Multiple skills stack simultaneously
  - Custom skills: any `.md` file in `vision_skills/` with `## Role`, `## Rules`, `## Style` sections
- **`/refresh`** — redraws the input box (fixes disappearing prompt in Colab)

### Fixed
- Vision always identifies as Vision — never leaks underlying model name to user
- Advisor no longer references stale council verdicts from previous sessions
- `validate_model()` hard-rejects HTML error pages (`Cannot POST`, `<!DOCTYPE`) instead of warning + passing
- Bytez API endpoint corrected

---

## [4.1.0] — 2026-03-07

### Added
- **Self-improving engine** — silent usage tracking on every command
  - `/selfimprove` — analyzes patterns, suggests automations, recommends best model per task type
  - `/economy` — personal AI dashboard (sessions, total time, top commands, peak hours)
  - `/weeklyreport` — AI-generated productivity report
  - `/patterns` — shows learned predictive automation patterns
- **Predictive automation** — `predictive_check()` runs on startup, suggests automations based on time-of-day usage patterns
- Economy stats updated automatically on session exit

---

## [4.0.0] — 2026-03-04

### Added
- **Multi-agent task engine** — `/agent <complex task>`
  - Decomposes task into 2-4 specialist sub-agent roles via `_plan_agents()`
  - All agents run in parallel threads simultaneously
  - Coordinator merges all results into one comprehensive answer
  - `last_agent_result` injected into Vision and Advisor context

---

## [3.9.0] — 2026-02-28

### Added
- **Automation scheduler** — background thread checks every 30 seconds
  - Trigger formats: `daily:HH:MM`, `interval:Nm`, `interval:Nh`
  - Action formats: `/command`, `open:url`, `shell:cmd`, `chat:prompt`
  - `/automate`, `/automations`, `/autodelete`
- **Telegram** — `/telegramsetup`, `/telegram <msg>`, `/telegramread`
- **Email (SMTP)** — `/emailsetup`, `/email <to> | <subject> | <body>`

---

## [3.8.0] — 2026-02-24

### Added
- **GitHub integration** — `/ghconnect`, `/myrepos`, `/repoload`, `/repofile`, `/repoask`, `/reporeview`, `/commit`
- `/reporeview` runs LLM Council on loaded codebase

---

## [3.7.0] — 2026-02-20

### Added
- Real-time streaming via Rich `Live` display
- `/stream` toggle
- `/vision <image_path>` — base64 image input for vision-capable models

### Fixed
- Groq streaming auto-disabled on startup (Colab compatibility — Rich Live doesn't render)
- `get_max_tokens()` — Groq capped at 1024, others at 2048, prevents mid-response cutoffs

---

## [3.6.0] — 2026-02-16

### Added
- Auto-memory — background thread extracts facts from every conversation silently
- Tagged memory — `#personal`, `#stock`, `#weather`, `#council`, `#code`, `#goal`, `#auto`
- `/memory add <key> <val> [#tag]`, `/memory view [#tag]`, `/memory forget <key>`
- Memory injected into all AI calls: main chat, advisor, council, agents

---

## [3.5.0] — 2026-02-12

### Added
- Together AI, Fireworks, Mistral, Cerebras, NVIDIA NIM, SambaNova, Bytez (total: 9 providers + Bytez)
- Suggested model lists per provider
- `validate_model()` — test API call before accepting any model ID
- `current_provider_name` global for provider-aware behavior
- `/q` and `/quit` as exit aliases (Colab safety — Ctrl+C kills kernel)

---

## [3.2.0] — 2026-02-05

### Added
- **LLM Council** — parallel subordinate calls + Chairman synthesis — `/council`, `/councilsetup`
- **Debate Mode** — assigns FOR / AGAINST / SKEPTIC / DEVIL'S ADVOCATE — `/debate`
- Custom model selector — free-input, not locked to suggested list
- Council verdicts auto-saved to memory with `#council` tag

---

## [3.0.0] — 2026-01-28

### Added
- Full Python rewrite with Rich terminal UI
- Persistent storage via `vision_data.json`
- Memory, goals, portfolio, advisor mode
- Music player (yt-dlp + pygame), timer, stopwatch
- Image generation (Pollinations → HuggingFace fallback)
- TTS + voice input
- Stock data (yfinance, NSE + US markets, Indian sectors)
- Code generation, debug, file runner
- Web search (DuckDuckGo), scrape, wiki, weather, OCR
