# Vision CLI — Changelog

All notable changes to Vision CLI are documented here.

---

## v4.0 — JARVIS Mode
**Multi-agent task engine**
- `/agent <task>` — spawns specialized sub-agents in parallel, coordinator merges results
- Auto-decomposes complex tasks into 2–3 specialized roles
- Parallel execution via threading, coordinator synthesizes final answer

---

## v3.9 — Automation Engine
**Scheduler + integrations**
- Automation scheduler with `daily:HH:MM` and `interval:Nm/Nh` triggers
- Runs in background thread, checks every 30 seconds
- `/automate`, `/automations`, `/autodelete` commands
- Telegram integration — `/telegramsetup`, `/telegram`, `/telegramread`
- Email integration (SMTP) — `/emailsetup`, `/email`

---

## v3.8 — GitHub Integration
**Full developer tooling**
- `/ghconnect` — connect GitHub personal access token
- `/myrepos` — list your repos with stars, language, last updated
- `/repoload <user/repo>` — load repo structure + files into context
- `/repofile <path>` — read a specific file from loaded repo
- `/repoask <question>` — ask questions about the loaded repo
- `/reporeview` — LLM Council reviews the loaded codebase
- `/commit <message>` — git add, commit, push

---

## v3.7 — Streaming + Vision
**Real-time responses and image understanding**
- Streaming responses via Rich Live display
- `/stream` command to toggle streaming on/off
- `/vision <image_path> [question]` — image understanding via vision-capable models
- Base64 image encoding for vision API calls

---

## v3.6 — Smart Memory
**Persistent, tagged, auto-extracted memory**
- Auto-memory: extracts facts from conversations silently in background
- Tagged memory: `#personal`, `#stock`, `#weather`, `#council`, `#code`, `#goal`, `#auto`
- `/memory view #tag` — filter by tag
- Memory injected into all AI calls including council, advisor, and agents
- Council verdicts auto-saved to memory

---

## v3.5 — 9 Providers
**Full multi-provider expansion**
- Together AI (`api.together.xyz/v1`)
- Fireworks AI (`api.fireworks.ai/inference/v1`)
- Mistral AI (`api.mistral.ai/v1`)
- Cerebras (`api.cerebras.ai/v1`) — Groq-speed inference
- NVIDIA NIM (`integrate.api.nvidia.com/v1`) — free 405B Llama
- SambaNova (`api.sambanova.ai/v1`) — free 405B Llama
- Bytez — custom wrapper for 175k+ HuggingFace models
- Suggested model lists for each new provider
- `/q` and `/quit` as exit aliases (important for Colab)

---

## v3.4 — Bug Fixes
- `validate_model()`: bumped `max_tokens` from 1 → 10 (some models reject 1)
- Unknown validation errors now PASS with yellow warning instead of rejecting
- Fixed NoneType crash when model returns empty response
- Chairman `max_tokens` reduced 1536 → 800 (OpenRouter free tier limit)
- Null-check on chairman response before `strip_think()`

---

## v3.3 — Model List + Stability
- Fixed model ID: `moonshotai/kimi-k2-instruct-0905` → `moonshotai/kimi-k2`
- Fixed model ID: `google/gemini-flash-1.5` → `google/gemini-2.0-flash-001`
- Added: `openai/gpt-5.3-chat`, `x-ai/grok-4.20-multi-agent-beta`, `inception/mercury-2`, `openai/gpt-4o`

---

## v3.2 — LLM Council + Custom Model Selector
**The flagship features**
- LLM Council: parallel subordinate calls + chairman synthesis
- Debate Mode: models argue FOR/AGAINST/SKEPTIC/DEVIL'S ADVOCATE
- Custom model selector — free-input, not locked to list
- `validate_model()` — fires test call before accepting any model ID
- Separate selectors for main model and council setup
- `/council <query>`, `/debate <motion>`, `/councilsetup` commands
- Auto-triggers council setup on first `/council` or `/debate`

---

## v3.1 — Provider Expansion
- OpenRouter added alongside Groq and Ollama
- Rate limiting per model

---

## v3.0 — Core Rewrite
- Python rewrite from scratch
- Rich UI (panels, tables, markdown rendering)
- Persistent storage via `vision_data.json`
- Memory, goals, portfolio tracking
- Advisor mode with separate conversation history
- Music player (yt-dlp + pygame)
- Timer, stopwatch
- Image generation (Pollinations → HuggingFace fallback)
- TTS + voice input
- Stock data (yfinance, Indian NSE support)
- Code generation, debug, run
- Web search, scrape, wiki, weather, OCR

---

## v1.0–v2.x — Early Versions
- Basic CLI chat with Groq
- Initial stock and advisor features
- Vision CLI name established
