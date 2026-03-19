# Vision CLI — Changelog

---
## v.1.4.4-beta - Major Update
**Major update includes**
 - Setup wizard — first launch only, guides through provider + key + test
 - Actionable errors — every API failure gets a specific fix suggestion
 - Data cleanup — auto-archive old entries, size cap on vision_data.json
 - /export — full session → clean markdown file
 - Auto web search — Vision detects uncertainty → auto DuckDuckGo → answers with sources
 - /undo — undo stack for memory + automations
 - Multi-session Council — save verdicts, compare across sessions
 - Skill marketplace — /skill install <name> pulls from GitHub
 - API mode — --api flag → local Flask server on localhost (no cloud, no server needed)
 - GitHub Actions CI — automatic test runs on PR

   ---
## v4.3 — Bigger Context Window
**Rolling summarization — no context ever lost**

- **Rolling context summarization** replaces hard 20-message trim
  - `MAX_HISTORY = 40` — double the old limit before compression kicks in
  - When history hits 40, oldest 20 messages compressed into ~200 word summary block
  - Last 20 messages always kept verbatim for sharp short-term memory
  - Compression runs in background thread — never blocks your response
  - Summaries chain: older summaries stack, nothing discarded
  - Works independently for main chat AND advisor history
- **`/context`** command — shows context window status
  - Live message counts, summary size, compression settings
- **`/clear`** now resets everything — history, advisor history, rolling summaries, council/agent context
- **`conversation_summary` + `advisor_summary`** globals — injected into system prompt automatically
- **`get_conversation_context()`** — injects rolling summary into every chat call
- Advisor summary also injected into advisor context so long advisor sessions retain full memory

---

## v4.2 — Skills System + Stability
**Skills, refresh, identity, advisor context fix**

- **Skills System** — `vision_skills/` directory with `.md` skill files
  - 5 built-in skills auto-created: `coding`, `security`, `research`, `teacher`, `jarvis`
  - `/skill load/unload/list/active/clear/create/edit/reload`
  - Skills inject into system prompt — stack multiple simultaneously
  - User-created skills: any `.md` file in `vision_skills/` folder
- **`/refresh`** — redraws input box, fixes disappearing prompt in Colab
- **Identity fix** — Vision always responds as Vision, never leaks underlying model name
- **Advisor context fix** — `/clear` now resets `last_council_verdict` and `last_agent_result`
  so fresh sessions don't bleed old debates into Advisor responses
- **Bytez HTML error fix** — `validate_model()` now hard-rejects HTML error pages
  (`Cannot POST`, `<!DOCTYPE`) instead of warning + passing
- **Bytez URL fix** — corrected endpoint from `api.bytez.com/models/v1` → `api.bytez.com/v1`
- **Bytez warning** — displays routing notice on provider selection (Bytez may fallback silently)

---

## v4.1 — Self-Improving Engine
**Usage tracking, economy, predictive automation**

- **Self-Improving Engine** — `_track_usage()` logs every command silently
  - `/selfimprove` — analyzes patterns → suggests automations + model optimizations
  - `_track_model_score()` — records model performance per task type
  - `_suggest_predictive_automations()` — auto-generates automation suggestions from habits
- **Personal AI Economy** — `/economy` dashboard
  - Tracks total sessions, total time, commands used, memories saved
  - Top command frequency table
  - Peak usage hour + most active day
- **Weekly Reports** — `/weeklyreport` — AI-generated productivity analysis
- **Predictive Automation** — `/patterns` shows learned patterns
  - `predictive_check()` runs on startup — suggests actions based on time-of-day habits
- **`/clear` now also resets** `last_council_verdict` and `last_agent_result`
- **Economy update on exit** — session duration logged automatically

---

## v4.0 — Multi-Agent Task Engine
**Parallel specialized sub-agents**

- `/agent <task>` — Vision decomposes complex tasks into 2-4 specialized roles
- Agents run in parallel threads simultaneously
- Coordinator merges all results into one comprehensive answer
- `last_agent_result` injected into Vision + Advisor context
- `spawn_agents()` + `_plan_agents()` functions

---

## v3.9 — Automation Engine + Integrations
**Scheduler, Telegram, Email**

- Automation scheduler — `daily:HH:MM` and `interval:Nm/Nh` triggers
- Background thread checks every 30 seconds
- `/automate`, `/automations`, `/autodelete`
- `open:url` — opens URL in browser via automation
- `shell:cmd` — runs any system command via automation
- `chat:prompt` — AI generates reply → sends via Telegram
- Telegram integration — `/telegramsetup`, `/telegram`, `/telegramread`
- Email integration (SMTP) — `/emailsetup`, `/email`

---

## v3.8 — GitHub Integration
**Full developer tooling**

- `/ghconnect` — connect GitHub personal access token
- `/myrepos` — list repos with stars, language, last updated
- `/repoload <user/repo>` — load repo structure + files into context
- `/repofile <path>` — read specific file from loaded repo
- `/repoask <question>` — ask about loaded repo
- `/reporeview` — LLM Council reviews loaded codebase
- `/commit <message>` — git add, commit, push

---

## v3.7 — Streaming + Vision Input
**Real-time responses, image understanding**

- Real-time streaming via Rich Live display
- `/stream` command to toggle streaming on/off
- Groq streaming auto-disabled on startup (Colab compatibility)
- `/vision <image_path> [question]` — base64 image input to vision models

---

## v3.6 — Smart Memory
**Persistent, tagged, auto-extracted**

- Auto-memory — extracts facts from conversations silently in background thread
- Tagged memory — `#personal`, `#stock`, `#weather`, `#council`, `#code`, `#goal`
- `/memory view #tag` — filter by tag
- Memory injected into all AI calls — chat, council, advisor, agents
- Council verdicts auto-saved to memory with `#council` tag

---

## v3.5 — 9 Providers
**Full multi-provider expansion**

- Together AI, Fireworks, Mistral, Cerebras, NVIDIA NIM, SambaNova, Bytez
- Suggested model lists for each provider
- `/q` and `/quit` as exit aliases (Colab safety)
- `validate_model()` HTML error detection
- `get_max_tokens()` — Groq auto-caps at 1024, others at 2048
- `current_provider_name` global for provider-aware behavior

---

## v3.4 — Bug Fixes
- `max_tokens` 1 → 10 in validation (some models reject 1)
- Unknown validation errors warn + PASS instead of blocking
- NoneType crash on empty model response fixed
- Chairman `max_tokens` 1536 → 800 (OpenRouter free tier)
- Null-check before `strip_think()`

---

## v3.3 — Model List + Model ID Fixes
- `moonshotai/kimi-k2-instruct-0905` → `moonshotai/kimi-k2` (OpenRouter)
- `google/gemini-flash-1.5` → `google/gemini-2.0-flash-001`
- Added: GPT-5.3, Grok 4.20, Mercury 2, GPT-4o

---

## v3.2 — LLM Council + Custom Model Selector
**The flagship feature**

- LLM Council — parallel subordinate calls + Chairman synthesis
- Debate Mode — FOR/AGAINST/SKEPTIC/DEVIL'S ADVOCATE positions
- Custom model selector — free-input, not locked to list
- `validate_model()` — fires test call before accepting any model
- Separate selectors for main model and council
- `/council`, `/debate`, `/councilsetup`
- Auto-triggers council setup on first use

---

## v3.0 — Core Rewrite
- Python rewrite from scratch with Rich UI
- Persistent storage — `vision_data.json`
- Memory, goals, portfolio
- Advisor mode with separate conversation history
- Music player (yt-dlp + pygame)
- Timer, stopwatch
- Image generation (Pollinations → HuggingFace fallback)
- TTS + voice input
- Stock data — yfinance, NSE support, Indian sectors
- Code generation, debug, run
- Web search, scrape, wiki, weather, OCR

---

## v1.0–v2.x — Early Versions
- Basic CLI chat with Groq
- Initial stock and advisor features
- Vision CLI name established
