# MIT License — Copyright (c) 2026 Arshveen Singh
# Vision CLI v4.1 — 9 providers, LLM Council, GitHub, Automation,
# Telegram, Email, Scheduler, Multi-agent, Streaming, Vision input, Smart memory.
# Fixes: Groq token cap, Kimi cutoff, Bytez OpenAI-compatible endpoint.

import warnings
warnings.filterwarnings("ignore")

import os, re, subprocess, requests, asyncio
import json, time, sys, threading, base64
from datetime import datetime
from pathlib import Path
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.text import Text
from rich import box

console = Console()

# ══════════════════════════════════════════════════════════════════
# PERSISTENT STORAGE
# ══════════════════════════════════════════════════════════════════
DATA_FILE  = "vision_data.json"
CHATS_DIR  = "vision_chats"
MUSIC_DIR  = "vision_music"
AGENTS_DIR = "vision_agents"
for d in [CHATS_DIR, MUSIC_DIR, AGENTS_DIR]:
    Path(d).mkdir(exist_ok=True)

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {
        "memory": {}, "goals": [], "portfolio": {},
        "advisor_history": [], "automations": [],
        "github_token": None, "telegram_token": None,
        "telegram_chat_id": None, "email_config": {},
        "created": datetime.now().strftime("%d/%m/%Y")
    }

def save_data():
    data["memory"]          = memory
    data["goals"]           = goals
    data["portfolio"]       = portfolio
    data["advisor_history"] = advisor_history[-20:]
    data["automations"]     = automations
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

data             = load_data()
memory           = data.get("memory", {})
goals            = data.get("goals", [])
portfolio        = data.get("portfolio", {})
advisor_history  = data.get("advisor_history", [])
automations      = data.get("automations", [])
history               = []
mic_mode              = False
last_request_time     = 0
streaming_mode        = True
current_provider_name = ""   # set at startup + on /provider switch

def get_max_tokens(base=2048):
    """
    Groq free tier has a tight tokens-per-minute (TPM) cap.
    Capping at 1024 prevents mid-response cutoff on Kimi and other large models.
    All other providers use the full base limit.
    """
    return 1024 if current_provider_name == "Groq" else base

# ══════════════════════════════════════════════════════════════════
# RATE LIMITING
# ══════════════════════════════════════════════════════════════════
MODEL_LIMITS = {
    # Groq — Kimi K2 gets throttled hard on free tier, needs more breathing room
    "moonshotai/kimi-k2-instruct-0905": 6,   # Groq model ID — increase delay
    "moonshotai/kimi-k2":               3,   # OpenRouter model ID
    "deepseek/deepseek-r1":             5,
    "llama-3.3-70b-versatile":          2,
    "llama-3.1-8b-instant":             1,
    "anthropic/claude-3.5-sonnet":      3,
    "google/gemini-2.0-flash-001":      1,
    "meta-llama/llama-3.3-70b-instruct":2,
    "openai/gpt-4o":                    2,
    "openai/gpt-4o-mini":               1,
}

def rate_limit(model):
    global last_request_time
    interval = MODEL_LIMITS.get(model, 2)
    elapsed  = time.time() - last_request_time
    if elapsed < interval:
        wait = interval - elapsed
        console.print(f"[yellow]⏳ {wait:.1f}s...[/yellow]", end="\r")
        time.sleep(wait)
    last_request_time = time.time()

# ══════════════════════════════════════════════════════════════════
# SMART MEMORY SYSTEM
# ══════════════════════════════════════════════════════════════════
def get_memory_context():
    if not memory:
        return ""
    facts = "\n".join([f"- {k}: {v['value']} {v.get('tag','')}" for k, v in memory.items()])
    return f"\n\nUser memory:\n{facts}"

def memory_add(key, value, tag=""):
    memory[key] = {
        "value": value, "tag": tag,
        "added": datetime.now().strftime("%d/%m/%Y %H:%M")
    }
    save_data()
    console.print(f"[green]✓ Memory: {key} → {value} {tag}[/green]")

def memory_view(tag_filter=None):
    if not memory:
        console.print("[yellow]No memories.[/yellow]"); return
    table = Table(box=box.ROUNDED, border_style="cyan", padding=(0,1))
    table.add_column("Key",   style="bold cyan")
    table.add_column("Value", style="white")
    table.add_column("Tag",   style="magenta")
    table.add_column("Added", style="dim")
    for k, v in memory.items():
        if tag_filter and v.get("tag","") != tag_filter: continue
        table.add_row(k, v["value"], v.get("tag",""), v["added"])
    console.print(table)

def memory_forget(key):
    if key in memory:
        del memory[key]; save_data()
        console.print(f"[green]✓ Forgot: {key}[/green]")
    else:
        console.print(f"[red]Not found: {key}[/red]")

def auto_memory(client, model, user_input, ai_reply):
    """Auto-detect facts worth remembering. Runs silently in background."""
    def _extract():
        try:
            prompt = (
                f"User said: {user_input}\nAI replied: {ai_reply[:400]}\n\n"
                "Extract facts worth remembering (name, prefs, goals, projects, decisions). "
                'Return ONLY JSON array: [{"key":"...","value":"...","tag":"#personal"}] '
                "or [] if nothing. Max 2 items. Very selective."
            )
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role":"user","content":prompt}],
                max_tokens=150)
            raw = strip_think(resp.choices[0].message.content or "[]")
            raw = re.sub(r"```json|```","",raw).strip()
            items = json.loads(raw)
            for item in items:
                k = item.get("key","").strip()
                v = item.get("value","").strip()
                t = item.get("tag","")
                if k and v and k not in memory:
                    memory[k] = {"value":v,"tag":t,
                                 "added":datetime.now().strftime("%d/%m/%Y %H:%M")}
            if items: save_data()
        except: pass
    threading.Thread(target=_extract, daemon=True).start()

# ══════════════════════════════════════════════════════════════════
# MUSIC PLAYER
# ══════════════════════════════════════════════════════════════════
music_queue   = []
current_song  = None
music_thread  = None
music_playing = False

def download_and_play(query):
    global current_song, music_playing
    try:
        import yt_dlp, pygame
        console.print(f"[yellow]🎵 Searching: {query}...[/yellow]")
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': f'{MUSIC_DIR}/%(title)s.%(ext)s',
            'quiet': True, 'no_warnings': True, 'default_search': 'ytsearch1',
            'postprocessors': [{'key':'FFmpegExtractAudio','preferredcodec':'mp3','preferredquality':'192'}],
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch1:{query}", download=True)
            if 'entries' in info: info = info['entries'][0]
            title = info.get('title', query)
            mins, secs = divmod(int(info.get('duration',0)), 60)
        files = list(Path(MUSIC_DIR).glob("*.mp3"))
        if not files: return
        latest = max(files, key=os.path.getctime)
        current_song = title
        console.print(Panel(
            f"[bold cyan]🎵 Now Playing[/bold cyan]\n\n[white]{title}[/white]\n"
            f"[dim]{mins:02d}:{secs:02d}[/dim]\n\n[dim]/pause /resume /stop /skip[/dim]",
            border_style="cyan"))
        pygame.mixer.init()
        pygame.mixer.music.load(str(latest))
        pygame.mixer.music.play()
        music_playing = True
        while pygame.mixer.music.get_busy() and music_playing: time.sleep(1)
        music_playing = False; current_song = None
        if music_queue: play_music(music_queue.pop(0))
    except Exception as e:
        console.print(f"[red]Music error: {e}[/red]"); music_playing = False

def play_music(query):
    global music_thread
    music_thread = threading.Thread(target=download_and_play, args=(query,), daemon=True)
    music_thread.start()

def pause_music():
    try:
        import pygame
        if pygame.mixer.music.get_busy(): pygame.mixer.music.pause(); console.print("[yellow]⏸ Paused[/yellow]")
        else: console.print("[red]Nothing playing.[/red]")
    except: console.print("[red]Music not initialized.[/red]")

def resume_music():
    try:
        import pygame; pygame.mixer.music.unpause(); console.print("[green]▶ Resumed[/green]")
    except: console.print("[red]Music not initialized.[/red]")

def stop_music():
    global music_playing, current_song
    try:
        import pygame; pygame.mixer.music.stop()
        music_playing = False; current_song = None; music_queue.clear()
        console.print("[red]⏹ Stopped[/red]")
    except: console.print("[red]Music not initialized.[/red]")

def skip_music():
    global music_playing
    try:
        import pygame; pygame.mixer.music.stop(); music_playing = False
        console.print("[cyan]⏭ Skipped[/cyan]")
        if music_queue: play_music(music_queue.pop(0))
    except: console.print("[red]Music not initialized.[/red]")

def show_queue():
    if not music_queue and not current_song:
        console.print("[yellow]Queue empty.[/yellow]"); return
    if current_song: console.print(f"[bold cyan]🎵 Now:[/bold cyan] {current_song}")
    if music_queue:
        table = Table(box=box.ROUNDED, border_style="cyan", padding=(0,1))
        table.add_column("#", style="bold cyan"); table.add_column("Song", style="white")
        for i, s in enumerate(music_queue, 1): table.add_row(str(i), s)
        console.print(table)

def set_volume(vol):
    try:
        import pygame; pygame.mixer.music.set_volume(max(0, min(1, float(vol)/100)))
        console.print(f"[green]🔊 Volume: {vol}%[/green]")
    except: console.print("[red]Error setting volume.[/red]")

# ══════════════════════════════════════════════════════════════════
# TIMER / STOPWATCH
# ══════════════════════════════════════════════════════════════════
stopwatch_start = None; stopwatch_running = False; lap_times = []

def study_timer(minutes):
    secs = int(float(minutes) * 60)
    console.print(f"[bold cyan]⏱ {minutes} min timer started[/bold cyan]")
    def _run():
        for remaining in range(secs, 0, -1):
            m, s = divmod(remaining, 60)
            sys.stdout.write(f"\r[Timer: {m:02d}:{s:02d}]  "); sys.stdout.flush(); time.sleep(1)
        sys.stdout.write("\r"+" "*25+"\r")
        console.print("\n[bold green]✓ TIMER DONE! 🎉[/bold green]")
    threading.Thread(target=_run, daemon=True).start()

def stopwatch_cmd(action):
    global stopwatch_start, stopwatch_running, lap_times
    if action == "start":
        stopwatch_start = time.time(); stopwatch_running = True; lap_times = []
        console.print("[green]✓ Started[/green]")
    elif action == "stop" and stopwatch_running:
        elapsed = time.time()-stopwatch_start; stopwatch_running = False
        m, s = divmod(int(elapsed), 60); console.print(f"[bold green]{m:02d}:{s:02d}[/bold green]")
    elif action == "lap" and stopwatch_running:
        elapsed = time.time()-stopwatch_start; lap_times.append(elapsed)
        m, s = divmod(int(elapsed), 60); console.print(f"[cyan]Lap {len(lap_times)}: {m:02d}:{s:02d}[/cyan]")
    elif action == "check" and stopwatch_running:
        elapsed = time.time()-stopwatch_start
        m, s = divmod(int(elapsed), 60); console.print(f"[cyan]⏱ {m:02d}:{s:02d}[/cyan]")

# ══════════════════════════════════════════════════════════════════
# IMAGE GENERATION
# ══════════════════════════════════════════════════════════════════
def generate_image(prompt):
    filename = f"vision_img_{datetime.now().strftime('%H%M%S')}.jpg"
    console.print("[yellow]Trying Pollinations.ai...[/yellow]")
    try:
        url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(prompt)}?width=512&height=512&nologo=true"
        r = requests.get(url, timeout=30)
        if r.status_code == 200 and "image" in r.headers.get("content-type",""):
            open(filename,"wb").write(r.content)
            console.print(f"[green]✓ Saved: '{filename}'[/green]")
            try:
                from IPython.display import display, Image as IPImage; display(IPImage(filename))
            except: pass
            return
    except: console.print("[yellow]Pollinations failed → HuggingFace...[/yellow]")
    try:
        token = os.environ.get("HF_TOKEN") or input("HuggingFace token: ").strip()
        r = requests.post(
            "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-2-1",
            headers={"Authorization": f"Bearer {token}"}, json={"inputs": prompt}, timeout=60)
        if r.status_code == 200:
            open(filename,"wb").write(r.content)
            console.print(f"[green]✓ Saved: '{filename}'[/green]")
    except Exception as e: console.print(f"[red]{e}[/red]")

# ══════════════════════════════════════════════════════════════════
# TTS + VOICE
# ══════════════════════════════════════════════════════════════════
def speak(text):
    try:
        import pyttsx3; engine = pyttsx3.init()
        engine.setProperty('rate', 175); engine.say(text[:300]); engine.runAndWait()
    except: pass

def listen():
    try:
        import speech_recognition as sr
        r = sr.Recognizer()
        with sr.Microphone() as source:
            console.print("[cyan]🎤 Listening...[/cyan]")
            audio = r.listen(source, timeout=5)
        text = r.recognize_google(audio)
        console.print(f"[cyan]You said: {text}[/cyan]"); return text
    except Exception as e:
        console.print(f"[red]Mic error: {e}[/red]"); return None

# ══════════════════════════════════════════════════════════════════
# SYSTEM PROMPTS
# ══════════════════════════════════════════════════════════════════
BANNER = r"""[bold cyan]
██╗   ██╗██╗███████╗██╗ ██████╗ ███╗   ██╗     ██████╗██╗     ██╗
██║   ██║██║██╔════╝██║██╔═══██╗████╗  ██║    ██╔════╝██║     ██║
██║   ██║██║███████╗██║██║   ██║██╔██╗ ██║    ██║     ██║     ██║
╚██╗ ██╔╝██║╚════██║██║██║   ██║██║╚██╗██║    ██║     ██║     ██║
 ╚████╔╝ ██║███████║██║╚██████╔╝██║ ╚████║    ╚██████╗███████╗██║
  ╚═══╝  ╚═╝╚══════╝╚═╝ ╚═════╝ ╚═╝  ╚═══╝     ╚═════╝╚══════╝╚═╝
[/bold cyan]"""

SYSTEM_PROMPT = """You are Vision — the core AI of Vision CLI v4.0, built by Arshveen Singh.
Sharp, direct, slightly witty, calm under pressure. Never arrogant.
Reason clearly, explain brilliantly, write clean precise code.
Never give one-word replies unless genuinely needed.
Be warm and conversational. Treat the user as intelligent."""

ADVISOR_PROMPT = """You are the Advisor in Vision CLI v4.0 — a brutally honest personal advisor.
You are NOT Vision. Completely separate entity.
The user is sharp, ambitious, thinks way beyond their age.
Brutally honest — no sugarcoating. Business partner, goal tracker, financial advisor.
Speak like a trusted older friend who happens to be a genius.
NEVER give one-word replies. Never preachy. Never lecture. Be real."""

COUNCIL_SUBORDINATE_PROMPT = """You are a council member — one of several AI models giving independent perspective.
Be direct, analytical, opinionated. State your position clearly with reasoning.
A Chairman will synthesize all responses. Make your answer worth citing. No filler."""

COUNCIL_CHAIRMAN_PROMPT = """You are the Chairman of the LLM Council — synthesize multiple AI perspectives into one definitive answer.

Process:
1. Read every response carefully
2. Identify where they AGREE (strong signal)
3. Identify where they DISAGREE (reason through it)
4. Extract best insights from each
5. Deliver ONE final verdict

Format:
## ⚖ Council Verdict
**Consensus:** [what models agreed on]
**Key Conflict:** [where they diverged]
**Final Answer:** [your synthesized verdict]
**Confidence:** [High/Medium/Low and why]

Be authoritative. You are the last word."""

COUNCIL_DEBATE_PROMPT = """You are a council member in a structured debate.
Assigned POSITION — argue it convincingly even if you disagree.
Strong devil's advocate. Use logic, examples, evidence. Never concede.
Steel-man your position. Sharp and persuasive."""

AGENT_PROMPT = """You are a specialized sub-agent in Vision CLI's multi-agent system.
Your role: {role}
Be focused, efficient. Output ONLY what is relevant to your role.
Do not explain your process. Deliver the result directly."""

# ══════════════════════════════════════════════════════════════════
# SUGGESTED MODELS
# ══════════════════════════════════════════════════════════════════
GROQ_SUGGESTED = [
    ("moonshotai/kimi-k2-instruct-0905", "Kimi K2        — Reasoning"),
    ("qwen/qwen3-32b",                   "Qwen 3 32B     — Coding"),
    ("llama-3.3-70b-versatile",          "LLaMA 3.3 70B  — General"),
    ("llama-3.1-8b-instant",             "LLaMA 3.1 8B   — Ultra fast"),
    ("mixtral-8x7b-32768",              "Mixtral 8x7B   — Balanced"),
]
OPENROUTER_SUGGESTED = [
    ("moonshotai/kimi-k2",                "Kimi K2             — Best reasoning"),
    ("deepseek/deepseek-r1",              "DeepSeek R1         — Thinking beast"),
    ("anthropic/claude-3.5-sonnet",       "Claude 3.5 Sonnet   — Best overall"),
    ("google/gemini-2.0-flash-001",       "Gemini 2.0 Flash    — Fast & smart"),
    ("meta-llama/llama-3.3-70b-instruct", "LLaMA 3.3 70B       — Open source"),
    ("openai/gpt-4o",                     "GPT-4o              — OpenAI flagship"),
    ("openai/gpt-4o-mini",                "GPT-4o Mini         — Fast & cheap"),
    ("openai/gpt-5.3-chat",              "GPT-5.3 Chat        — Latest OpenAI"),
    ("qwen/qwen3-32b",                    "Qwen 3 32B          — Coding"),
    ("x-ai/grok-3-mini-beta",            "Grok 3 Mini         — Direct & witty"),
    ("x-ai/grok-4.20-multi-agent-beta",  "Grok 4.20 Agent     — Multi-agent"),
    ("inception/mercury-2",              "Mercury 2           — 1000+ tok/s"),
    ("anthropic/claude-3-haiku",          "Claude 3 Haiku      — Cheapest Claude"),
    ("mistralai/mistral-large",           "Mistral Large       — Sharp & fast"),
    ("nvidia/llama-3.1-nemotron-70b-instruct", "Nemotron 70B  — NVIDIA flagship"),
]
OLLAMA_SUGGESTED = [
    ("llama3.2","LLaMA 3.2 — General"), ("qwen2.5","Qwen 2.5 — Coding"),
    ("mistral","Mistral — Fast"), ("phi3","Phi-3 — Light"),
    ("deepseek-r1","DeepSeek R1 — Local reasoning"), ("gemma2","Gemma 2 — Google"),
]
TOGETHER_SUGGESTED = [
    ("meta-llama/Llama-3.3-70B-Instruct-Turbo", "LLaMA 3.3 70B Turbo"),
    ("Qwen/Qwen2.5-72B-Instruct-Turbo",         "Qwen 2.5 72B"),
    ("deepseek-ai/DeepSeek-R1",                 "DeepSeek R1"),
    ("meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo", "LLaMA 3.1 405B"),
]
FIREWORKS_SUGGESTED = [
    ("accounts/fireworks/models/llama-v3p3-70b-instruct", "LLaMA 3.3 70B"),
    ("accounts/fireworks/models/deepseek-r1",             "DeepSeek R1"),
    ("accounts/fireworks/models/qwen2p5-72b-instruct",    "Qwen 2.5 72B"),
]
MISTRAL_SUGGESTED = [
    ("mistral-large-latest","Mistral Large"), ("mistral-small-latest","Mistral Small"),
    ("codestral-latest","Codestral — Code specialist"),
]
CEREBRAS_SUGGESTED = [
    ("llama3.3-70b","LLaMA 3.3 70B — Groq-speed"),
    ("llama3.1-8b","LLaMA 3.1 8B — Ultra fast"),
]
NVIDIA_SUGGESTED = [
    ("meta/llama-3.1-405b-instruct",           "LLaMA 3.1 405B"),
    ("nvidia/llama-3.1-nemotron-70b-instruct", "Nemotron 70B"),
    ("meta/llama-3.3-70b-instruct",            "LLaMA 3.3 70B"),
    ("deepseek-ai/deepseek-r1",                "DeepSeek R1"),
]
SAMBANOVA_SUGGESTED = [
    ("Meta-Llama-3.1-405B-Instruct","LLaMA 3.1 405B — Free flagship"),
    ("Meta-Llama-3.3-70B-Instruct", "LLaMA 3.3 70B"),
    ("DeepSeek-R1",                 "DeepSeek R1"),
]
BYTEZ_SUGGESTED = [
    ("Qwen/Qwen2-7B-Instruct",          "Qwen 2 7B       — Fast & capable"),
    ("meta-llama/Llama-3.2-3B-Instruct","LLaMA 3.2 3B    — Lightweight"),
    ("microsoft/Phi-3-mini-4k-instruct", "Phi-3 Mini      — Very fast"),
    ("mistralai/Mistral-7B-Instruct-v0.3","Mistral 7B     — Solid general"),
    ("google/gemma-2-9b-it",            "Gemma 2 9B      — Google open"),
]

INDIAN_SECTORS = {
    "banking": ["HDFCBANK","ICICIBANK","SBIN","AXISBANK","KOTAKBANK","INDUSINDBK"],
    "it":      ["TCS","INFY","WIPRO","HCLTECH","TECHM","LTIM"],
    "pharma":  ["SUNPHARMA","DRREDDY","CIPLA","DIVISLAB","BIOCON"],
    "auto":    ["TATAMOTORS","MARUTI","M&M","BAJAJ-AUTO","EICHERMOT"],
    "tata":    ["TCS","TATAMOTORS","TATASTEEL","TATAPOWER","TATACHEM"],
    "energy":  ["RELIANCE","ONGC","NTPC","POWERGRID","ADANIGREEN"],
    "fmcg":    ["HINDUNILVR","ITC","NESTLEIND","BRITANNIA","DABUR"],
    "adani":   ["ADANIENT","ADANIGREEN","ADANIPORTS","ADANIPOWER"],
    "smallcap":["IRFC","RVNL","IRCTC","NYKAA","ZOMATO","PAYTM"],
}

# ══════════════════════════════════════════════════════════════════
# PROVIDER SETUP — 9 providers + Bytez
# ══════════════════════════════════════════════════════════════════
def select_provider():
    console.print(Panel("[bold cyan]Select AI Provider[/bold cyan]", border_style="cyan"))
    providers = [
        ("1","Groq",       "Free, ultra fast"),
        ("2","OpenRouter", "Access any model"),
        ("3","Ollama",     "100% local"),
        ("4","Together",   "Open source, free tier"),
        ("5","Fireworks",  "Fast inference, free tier"),
        ("6","Mistral",    "Official Mistral API"),
        ("7","Cerebras",   "Groq-speed, free tier"),
        ("8","NVIDIA",     "Free credits, 405B Llama"),
        ("9","SambaNova",  "Free 405B Llama"),
        ("10","Bytez",     "175k+ models"),
    ]
    for n, name, desc in providers:
        console.print(f"  [green][{n:>2}][/green] {name:<12} — {desc}")
    while True:
        c = input("\n→ (1-10): ").strip()
        if c in [p[0] for p in providers]: return c
        console.print("[red]Invalid.[/red]")

def setup_provider(provider):
    from openai import OpenAI
    if provider == "1":
        from groq import Groq
        key = os.environ.get("GROQ_API_KEY") or input("Groq API key: ").strip()
        return Groq(api_key=key), "Groq"
    elif provider == "2":
        key = os.environ.get("OPENROUTER_API_KEY") or input("OpenRouter key: ").strip()
        return OpenAI(base_url="https://openrouter.ai/api/v1", api_key=key), "OpenRouter"
    elif provider == "3":
        host = input("Ollama host (Enter=localhost): ").strip() or "http://localhost:11434"
        return OpenAI(base_url=f"{host}/v1", api_key="ollama"), "Ollama"
    elif provider == "4":
        key = os.environ.get("TOGETHER_API_KEY") or input("Together AI key: ").strip()
        return OpenAI(base_url="https://api.together.xyz/v1", api_key=key), "Together"
    elif provider == "5":
        key = os.environ.get("FIREWORKS_API_KEY") or input("Fireworks key: ").strip()
        return OpenAI(base_url="https://api.fireworks.ai/inference/v1", api_key=key), "Fireworks"
    elif provider == "6":
        key = os.environ.get("MISTRAL_API_KEY") or input("Mistral API key: ").strip()
        return OpenAI(base_url="https://api.mistral.ai/v1", api_key=key), "Mistral"
    elif provider == "7":
        key = os.environ.get("CEREBRAS_API_KEY") or input("Cerebras API key: ").strip()
        return OpenAI(base_url="https://api.cerebras.ai/v1", api_key=key), "Cerebras"
    elif provider == "8":
        key = os.environ.get("NVIDIA_API_KEY") or input("NVIDIA NIM key (build.nvidia.com): ").strip()
        return OpenAI(base_url="https://integrate.api.nvidia.com/v1", api_key=key), "NVIDIA"
    elif provider == "9":
        key = os.environ.get("SAMBANOVA_API_KEY") or input("SambaNova key: ").strip()
        return OpenAI(base_url="https://api.sambanova.ai/v1", api_key=key), "SambaNova"
    elif provider == "10":
        return _setup_bytez(), "Bytez"

def _setup_bytez():
    """
    Bytez v3.x supports an OpenAI-compatible REST endpoint.
    No custom wrapper needed — just point OpenAI client at their base URL.
    Model IDs use HuggingFace format e.g. 'Qwen/Qwen2-7B-Instruct'
    Full model list: bytez.com/docs/api
    """
    from openai import OpenAI
    key = os.environ.get("BYTEZ_API_KEY") or input("Bytez API key (bytez.com): ").strip()
    return OpenAI(base_url="https://api.bytez.com/models/v1", api_key=key)

# ══════════════════════════════════════════════════════════════════
# MODEL VALIDATION + SELECTORS
# ══════════════════════════════════════════════════════════════════
def validate_model(client, model_id, provider_name):
    try:
        client.chat.completions.create(
            model=model_id, messages=[{"role":"user","content":"hi"}], max_tokens=10)
        return True, None
    except Exception as e:
        err = str(e)
        if "model" in err.lower() and any(x in err.lower() for x in ["not found","does not exist","invalid model"]):
            return False, f"Model '{model_id}' not found on {provider_name}."
        elif "404" in err:
            return False, f"Model '{model_id}' not found (404)."
        elif "401" in err or "auth" in err.lower():
            return False, "Authentication error — check your API key."
        else:
            console.print(f"[yellow]⚠ Warning (model likely valid): {err[:120]}[/yellow]")
            return True, None

def _get_suggested(provider_name):
    m = {
        "Groq":GROQ_SUGGESTED, "OpenRouter":OPENROUTER_SUGGESTED,
        "Ollama":OLLAMA_SUGGESTED, "Together":TOGETHER_SUGGESTED,
        "Fireworks":FIREWORKS_SUGGESTED, "Mistral":MISTRAL_SUGGESTED,
        "Cerebras":CEREBRAS_SUGGESTED, "NVIDIA":NVIDIA_SUGGESTED,
        "SambaNova":SAMBANOVA_SUGGESTED, "Bytez":BYTEZ_SUGGESTED,
    }
    hints = {
        "Groq":"console.groq.com/docs/models", "OpenRouter":"openrouter.ai/models",
        "Ollama":"run 'ollama list'", "Together":"api.together.xyz/models",
        "Fireworks":"fireworks.ai/models", "Mistral":"docs.mistral.ai",
        "Cerebras":"inference.cerebras.ai", "NVIDIA":"build.nvidia.com/models",
        "SambaNova":"cloud.sambanova.ai", "Bytez":"bytez.com/docs/api (HuggingFace IDs)",
    }
    return m.get(provider_name,[]), hints.get(provider_name,"provider docs")

def _show_model_table(suggested):
    table = Table(box=box.ROUNDED, border_style="cyan", padding=(0,1))
    table.add_column("#", style="bold cyan", no_wrap=True)
    table.add_column("Model ID", style="green")
    table.add_column("Notes", style="dim")
    for i, (mid, desc) in enumerate(suggested, 1):
        name, note = desc.split("—",1) if "—" in desc else (desc,"")
        table.add_row(str(i), mid, note.strip())
    console.print(table)

def _resolve_and_validate(raw, suggested, client, provider_name):
    model_id = suggested[int(raw)-1][0] if (raw.isdigit() and 1<=int(raw)<=len(suggested)) else raw
    console.print(f"[yellow]Checking '{model_id}'...[/yellow]")
    ok, err = validate_model(client, model_id, provider_name)
    if ok:
        console.print(f"[bold green]✓ Model confirmed: {model_id}[/bold green]\n")
        return model_id
    else:
        console.print(f"[bold red]✗ {err}[/bold red]\n[dim]Try again.[/dim]\n")
        return None

def select_model_main(client, provider_name):
    suggested, hint = _get_suggested(provider_name)
    while True:
        console.print(Panel(f"[bold cyan]Select Model — {provider_name}[/bold cyan]\n[dim]{hint}[/dim]", border_style="cyan"))
        if suggested: _show_model_table(suggested)
        console.print("\n[dim]Pick a number or type any model ID directly.[/dim]")
        raw = input("→ Model: ").strip()
        if not raw: continue
        result = _resolve_and_validate(raw, suggested, client, provider_name)
        if result: return result

def select_model_council(client, provider_name):
    suggested, hint = _get_suggested(provider_name)
    console.print(Panel(
        "[bold cyan]⚖ LLM Council — Model Setup[/bold cyan]\n\n"
        "[white]Chairman[/white]     → synthesizes the final verdict\n"
        "[white]Subordinates[/white] → answer independently, in parallel\n\n"
        f"[dim]{hint}[/dim]", border_style="cyan"))
    console.print("\n[bold yellow]Step 1 — CHAIRMAN:[/bold yellow]")
    chairman_id = None
    while not chairman_id:
        if suggested: _show_model_table(suggested)
        raw = input("→ Chairman: ").strip()
        if raw: chairman_id = _resolve_and_validate(raw, suggested, client, provider_name)
    console.print("\n[bold yellow]Step 2 — SUBORDINATES (2–4, type 'done' to finish):[/bold yellow]")
    if suggested: _show_model_table(suggested)
    sub_ids, sub_names = [], []
    while len(sub_ids) < 4:
        slot = len(sub_ids)+1
        suffix = "  [dim](or 'done')[/dim]" if len(sub_ids)>=2 else "  [dim](required)[/dim]"
        raw = input(f"→ Subordinate {slot}{suffix}: ").strip()
        if raw.lower()=="done":
            if len(sub_ids)<2: console.print("[red]Need at least 2.[/red]"); continue
            break
        if not raw: continue
        candidate = suggested[int(raw)-1][0] if (raw.isdigit() and 1<=int(raw)<=len(suggested)) else raw
        if candidate in sub_ids: console.print(f"[yellow]Already added.[/yellow]"); continue
        console.print(f"[yellow]Checking '{candidate}'...[/yellow]")
        ok, err = validate_model(client, candidate, provider_name)
        if ok:
            sub_ids.append(candidate); sub_names.append(candidate.split("/")[-1])
            console.print(f"[bold green]✓ Added: {candidate} ({len(sub_ids)}/4)[/bold green]")
        else:
            console.print(f"[bold red]✗ {err}[/bold red]")
    console.print(Panel(
        f"[bold cyan]⚖ Council Configured[/bold cyan]\n\n"
        f"[yellow]Chairman:[/yellow]    {chairman_id}\n"
        f"[cyan]Subordinates:[/cyan]\n" + "\n".join([f"  • {s}" for s in sub_ids]),
        border_style="cyan"))
    return chairman_id, sub_ids, sub_names, chairman_id.split("/")[-1]

# ══════════════════════════════════════════════════════════════════
# CHAT ENGINE — with streaming
# ══════════════════════════════════════════════════════════════════
def strip_think(text):
    if text is None: return ""
    return re.sub(r"<think>.*?</think>","",text,flags=re.DOTALL).strip()

def chat(client, model, user_input, system=None):
    global history
    history.append({"role":"user","content":user_input})
    if len(history)>20: history = history[-20:]
    rate_limit(model)
    sys_prompt = (system or SYSTEM_PROMPT) + get_memory_context()
    try:
        if streaming_mode:
            return _stream_chat(client, model, sys_prompt)
        else:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role":"system","content":sys_prompt},*history],
                max_tokens=get_max_tokens(2048))
            reply = strip_think(response.choices[0].message.content)
            history.append({"role":"assistant","content":reply})
            return reply
    except Exception as e: return f"Error: {e}"

def _stream_chat(client, model, sys_prompt):
    full_reply = ""
    try:
        stream = client.chat.completions.create(
            model=model,
            messages=[{"role":"system","content":sys_prompt},*history],
            max_tokens=get_max_tokens(2048), stream=True)
        with Live(Text(""), refresh_per_second=15, console=console) as live:
            for chunk in stream:
                delta = chunk.choices[0].delta.content if chunk.choices else None
                if delta:
                    full_reply += delta
                    display = re.sub(r"<think>.*?</think>","",full_reply,flags=re.DOTALL)
                    live.update(Text(display))
        full_reply = strip_think(full_reply)
        history.append({"role":"assistant","content":full_reply})
        return full_reply
    except Exception:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role":"system","content":sys_prompt},*history],
                max_tokens=get_max_tokens(2048))
            reply = strip_think(response.choices[0].message.content)
            history.append({"role":"assistant","content":reply})
            return reply
        except Exception as e: return f"Error: {e}"

def advisor_chat(client, model, user_input):
    global advisor_history
    advisor_history.append({"role":"user","content":user_input})
    if len(advisor_history)>20: advisor_history = advisor_history[-20:]
    rate_limit(model)
    context = f"Goals: {goals}\nPortfolio: {portfolio}\n" if goals or portfolio else ""
    if history:
        context += "\nRecent chat:\n"+"".join([f"{m['role'].upper()}: {m['content'][:200]}\n" for m in history[-6:]])
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role":"system","content":ADVISOR_PROMPT+f"\n\n{context}"+get_memory_context()},
                      *advisor_history],
            max_tokens=get_max_tokens(2048))
        reply = strip_think(response.choices[0].message.content)
        advisor_history.append({"role":"assistant","content":reply})
        save_data(); return reply
    except Exception as e: return f"Error: {e}"

def ask(client, model, prompt, system=None):
    rate_limit(model)
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role":"system","content":(system or SYSTEM_PROMPT)+get_memory_context()},
                      {"role":"user","content":prompt}],
            max_tokens=get_max_tokens(2048))
        return strip_think(response.choices[0].message.content)
    except Exception as e: return f"Error: {e}"

# ══════════════════════════════════════════════════════════════════
# LLM COUNCIL ENGINE
# ══════════════════════════════════════════════════════════════════
def llm_council(client, query, chairman_id, sub_ids, sub_names):
    responses, errors = {}, {}
    console.print(Panel(
        f"[bold cyan]⚖ LLM Council Session[/bold cyan]\n\n"
        f"[white]Query:[/white] {query}\n\n"
        f"[dim]Firing {len(sub_ids)} subordinates in parallel...[/dim]",
        border_style="cyan"))

    def call_model(mid, name):
        try:
            rate_limit(mid)
            resp = client.chat.completions.create(
                model=mid,
                messages=[{"role":"system","content":COUNCIL_SUBORDINATE_PROMPT+get_memory_context()},
                          {"role":"user","content":query}],
                max_tokens=1024)
            raw = resp.choices[0].message.content
            if raw is None: errors[mid]="Empty"; console.print(f"[yellow]⚠ {name} empty[/yellow]")
            else: responses[mid]=strip_think(raw); console.print(f"[green]✓ {name} responded[/green]")
        except Exception as e:
            errors[mid]=str(e); console.print(f"[red]✗ {name} failed: {e}[/red]")

    threads = [threading.Thread(target=call_model, args=(mid,name), daemon=True)
               for mid,name in zip(sub_ids,sub_names)]
    for t in threads: t.start()
    for t in threads: t.join()

    if not responses: console.print("[red]All subordinates failed.[/red]"); return None

    console.print("\n[bold cyan]── Council Members' Responses ──[/bold cyan]\n")
    for mid, name in zip(sub_ids, sub_names):
        if mid in responses:
            console.print(Panel(Markdown(responses[mid]),
                                title=f"[bold white]🤖 {name}[/bold white]", border_style="blue"))
        elif mid in errors:
            console.print(Panel(f"[red]Error: {errors[mid]}[/red]",
                                title=f"[bold red]✗ {name}[/bold red]", border_style="red"))

    console.print(f"\n[bold yellow]⚖ Chairman synthesizing...[/bold yellow]")
    brief = f"Query: \"{query}\"\n\n"+"".join([f"--- {name} ---\n{responses[mid]}\n\n"
             for mid,name in zip(sub_ids,sub_names) if mid in responses])
    brief += "Synthesize into your final verdict."
    try:
        rate_limit(chairman_id)
        resp = client.chat.completions.create(
            model=chairman_id,
            messages=[{"role":"system","content":COUNCIL_CHAIRMAN_PROMPT+get_memory_context()},
                      {"role":"user","content":brief}],
            max_tokens=800)
        verdict = strip_think(resp.choices[0].message.content) or "Empty verdict."
        console.print(Panel(Markdown(verdict),
                            title="[bold yellow]⚖ Chairman's Verdict[/bold yellow]",
                            border_style="yellow"))
        memory[f"council_{datetime.now().strftime('%d%m%y_%H%M')}"] = {
            "value": f"Q: {query[:80]} | V: {verdict[:100]}",
            "tag": "#council", "added": datetime.now().strftime("%d/%m/%Y %H:%M")}
        save_data(); return verdict
    except Exception as e:
        console.print(f"[red]Chairman failed: {e}[/red]"); return None

def llm_debate(client, motion, chairman_id, sub_ids, sub_names):
    positions = ["FOR","AGAINST","SKEPTIC","DEVIL'S ADVOCATE"]
    assigned  = positions[:len(sub_ids)]
    responses = {}
    console.print(Panel(
        f"[bold red]⚔ LLM Council — Debate Mode[/bold red]\n\n"
        f"[white]Motion:[/white] {motion}\n\n" +
        "\n".join([f"  [cyan]{n}[/cyan] → [yellow]{p}[/yellow]" for n,p in zip(sub_names,assigned)]),
        border_style="red"))

    def call_debater(mid, name, pos):
        try:
            rate_limit(mid)
            resp = client.chat.completions.create(
                model=mid,
                messages=[{"role":"system","content":COUNCIL_DEBATE_PROMPT},
                          {"role":"user","content":f"Argue the {pos} position on: \"{motion}\""}],
                max_tokens=1024)
            raw = resp.choices[0].message.content
            if raw: responses[mid]=(pos,strip_think(raw)); console.print(f"[green]✓ {name} ({pos})[/green]")
        except Exception as e: console.print(f"[red]✗ {name}: {e}[/red]")

    threads = [threading.Thread(target=call_debater,args=(mid,name,pos),daemon=True)
               for mid,name,pos in zip(sub_ids,sub_names,assigned)]
    for t in threads: t.start()
    for t in threads: t.join()

    if not responses: console.print("[red]All debaters failed.[/red]"); return None

    console.print("\n[bold red]── Debate Arguments ──[/bold red]\n")
    for mid, name in zip(sub_ids, sub_names):
        if mid in responses:
            pos, reply = responses[mid]
            color = "green" if pos=="FOR" else "red" if pos=="AGAINST" else "yellow"
            console.print(Panel(Markdown(reply),
                                title=f"[bold {color}]{name} — {pos}[/bold {color}]",
                                border_style=color))

    console.print(f"\n[bold yellow]⚖ Chairman deliberating...[/bold yellow]")
    brief = f"Debate: \"{motion}\"\n\n" + "".join([f"--- {name} ({responses[mid][0]}) ---\n{responses[mid][1]}\n\n"
             for mid,name in zip(sub_ids,sub_names) if mid in responses])
    brief += "Who argued better and why? Then give YOUR actual answer."
    try:
        rate_limit(chairman_id)
        resp = client.chat.completions.create(
            model=chairman_id,
            messages=[{"role":"system","content":COUNCIL_CHAIRMAN_PROMPT},
                      {"role":"user","content":brief}],
            max_tokens=800)
        verdict = strip_think(resp.choices[0].message.content) or "Empty verdict."
        console.print(Panel(Markdown(verdict),
                            title="[bold yellow]⚖ Chairman's Judgment[/bold yellow]",
                            border_style="yellow"))
        return verdict
    except Exception as e:
        console.print(f"[red]Chairman failed: {e}[/red]"); return None

# ══════════════════════════════════════════════════════════════════
# MULTI-AGENT ENGINE (v4.0)
# ══════════════════════════════════════════════════════════════════
def spawn_agents(client, model, task):
    console.print(Panel(
        f"[bold magenta]🤖 Multi-Agent Task[/bold magenta]\n\n"
        f"[white]Task:[/white] {task}\n\n[dim]Spawning agents...[/dim]",
        border_style="magenta"))
    agent_roles = _plan_agents(client, model, task)
    agent_results = {}

    def run_agent(role, sub_task):
        try:
            rate_limit(model)
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role":"system","content":AGENT_PROMPT.format(role=role)+get_memory_context()},
                          {"role":"user","content":sub_task}],
                max_tokens=1024)
            result = strip_think(resp.choices[0].message.content or "")
            agent_results[role] = result
            console.print(f"[green]✓ [{role}] done[/green]")
        except Exception as e:
            agent_results[role] = f"Error: {e}"
            console.print(f"[red]✗ [{role}] failed[/red]")

    threads = [threading.Thread(target=run_agent,args=(role,sub_task),daemon=True)
               for role,sub_task in agent_roles.items()]
    for t in threads: t.start()
    for t in threads: t.join()

    for role, result in agent_results.items():
        console.print(Panel(Markdown(result),
                            title=f"[bold magenta]🤖 {role}[/bold magenta]",
                            border_style="magenta"))

    console.print(f"\n[bold cyan]Coordinator merging...[/bold cyan]")
    merge_prompt = (f"Task: {task}\n\nAgent Results:\n" +
                    "".join([f"[{r}]: {res}\n" for r,res in agent_results.items()]) +
                    "\nMerge into one comprehensive final answer.")
    try:
        rate_limit(model)
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role":"system","content":SYSTEM_PROMPT},
                      {"role":"user","content":merge_prompt}],
            max_tokens=1536)
        final = strip_think(resp.choices[0].message.content or "")
        console.print(Panel(Markdown(final),
                            title="[bold cyan]🤖 Coordinator Result[/bold cyan]",
                            border_style="cyan"))
        return final
    except Exception as e:
        console.print(f"[red]Coordinator failed: {e}[/red]"); return None

def _plan_agents(client, model, task):
    try:
        rate_limit(model)
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role":"user","content":
                f"Decompose into 2-3 specialized agent roles: '{task}'\n"
                'Return ONLY JSON: {"Research Agent":"find data on X","Analysis Agent":"analyze it"}'}],
            max_tokens=200)
        raw = re.sub(r"```json|```","", strip_think(resp.choices[0].message.content or "{}")).strip()
        return json.loads(raw)
    except:
        return {"Research Agent":f"Research: {task}", "Analysis Agent":f"Analyze: {task}"}

# ══════════════════════════════════════════════════════════════════
# GITHUB INTEGRATION (v3.8)
# ══════════════════════════════════════════════════════════════════
github_token      = data.get("github_token")
loaded_repo       = None
loaded_repo_files = {}

def github_connect():
    global github_token
    token = os.environ.get("GITHUB_TOKEN") or input("GitHub Personal Access Token: ").strip()
    try:
        from github import Github
        g = Github(token); user = g.get_user()
        github_token = token; data["github_token"] = token; save_data()
        console.print(f"[green]✓ Connected as: {user.login}[/green]")
    except Exception as e: console.print(f"[red]GitHub auth failed: {e}[/red]")

def github_load_repo(repo_name):
    global loaded_repo, loaded_repo_files
    try:
        from github import Github
        g = Github(github_token); repo = g.get_repo(repo_name)
        console.print(f"[yellow]Loading {repo_name}...[/yellow]")
        loaded_repo_files = {}
        queue = list(repo.get_contents("")); file_tree = []
        while queue and len(file_tree) < 100:
            item = queue.pop(0)
            if item.type == "dir": queue.extend(repo.get_contents(item.path))
            else:
                file_tree.append(item.path)
                if item.size < 50000 and any(item.path.endswith(e) for e in
                    ['.py','.js','.ts','.md','.txt','.json','.yaml','.yml','.toml']):
                    try: loaded_repo_files[item.path] = item.decoded_content.decode('utf-8','ignore')
                    except: pass
        loaded_repo = repo_name
        console.print(Panel(
            f"[bold green]✓ Repo loaded: {repo_name}[/bold green]\n\n"
            f"Files: {len(file_tree)} total, {len(loaded_repo_files)} loaded\n"
            f"Stars: {repo.stargazers_count} | Language: {repo.language or 'N/A'}",
            border_style="green"))
    except Exception as e: console.print(f"[red]Error: {e}[/red]")

def github_list_repos():
    try:
        from github import Github
        g = Github(github_token); repos = list(g.get_user().get_repos())[:20]
        table = Table(box=box.ROUNDED, border_style="cyan", padding=(0,1))
        table.add_column("#",style="bold cyan"); table.add_column("Repo",style="green")
        table.add_column("Stars",style="yellow"); table.add_column("Lang",style="white")
        table.add_column("Updated",style="dim")
        for i, r in enumerate(repos, 1):
            table.add_row(str(i), r.full_name, str(r.stargazers_count),
                          r.language or "N/A", r.updated_at.strftime("%d/%m/%Y"))
        console.print(table)
    except Exception as e: console.print(f"[red]Error: {e}[/red]")

def github_read_file(path):
    if loaded_repo and path in loaded_repo_files:
        console.print(Markdown(f"```\n{loaded_repo_files[path]}\n```"))
    elif loaded_repo:
        try:
            from github import Github
            item = Github(github_token).get_repo(loaded_repo).get_contents(path)
            content = item.decoded_content.decode('utf-8','ignore')
            loaded_repo_files[path] = content
            console.print(Markdown(f"```\n{content}\n```"))
        except Exception as e: console.print(f"[red]Error: {e}[/red]")
    else: console.print("[yellow]No repo loaded. Use /repoload <user/repo>[/yellow]")

def github_ask(client, model, question):
    if not loaded_repo: console.print("[yellow]Load a repo first.[/yellow]"); return
    context = f"Repo: {loaded_repo}\n\nFiles:\n"; total = 0
    for path, content in loaded_repo_files.items():
        entry = f"\n--- {path} ---\n{content[:2000]}\n"
        if total + len(entry) > 12000: break
        context += entry; total += len(entry)
    reply = ask(client, model, f"{context}\n\nQuestion: {question}")
    console.print(Panel(Markdown(reply), title=f"[bold green]📁 {loaded_repo}[/bold green]",
                        border_style="green"))

def github_council_review(client, chairman_id, sub_ids, sub_names):
    if not loaded_repo: console.print("[yellow]Load a repo first.[/yellow]"); return
    query = (f"Review codebase: {loaded_repo}\n\n"
             "Focus on code quality, security, performance, architecture, suggestions.")
    llm_council(client, query, chairman_id, sub_ids, sub_names)

def github_commit(message):
    try:
        subprocess.run("git add -A", shell=True, check=True)
        subprocess.run(f'git commit -m "{message}"', shell=True, check=True)
        result = subprocess.run("git push", shell=True, capture_output=True, text=True)
        if result.returncode == 0: console.print(f"[green]✓ Pushed: {message}[/green]")
        else: console.print(f"[red]{result.stderr}[/red]")
    except Exception as e: console.print(f"[red]Error: {e}[/red]")

# ══════════════════════════════════════════════════════════════════
# TELEGRAM INTEGRATION (v3.9)
# ══════════════════════════════════════════════════════════════════
def telegram_setup():
    token   = os.environ.get("TELEGRAM_TOKEN") or input("Telegram Bot Token: ").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID") or input("Your Telegram Chat ID: ").strip()
    data["telegram_token"] = token; data["telegram_chat_id"] = chat_id; save_data()
    console.print("[green]✓ Telegram configured[/green]")

def telegram_send(message):
    token = data.get("telegram_token"); chat_id = data.get("telegram_chat_id")
    if not token or not chat_id:
        console.print("[yellow]Run /telegramsetup first[/yellow]"); return False
    try:
        r = requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                          json={"chat_id":chat_id,"text":message,"parse_mode":"Markdown"},timeout=10)
        if r.status_code==200: console.print("[green]✓ Telegram message sent[/green]"); return True
        else: console.print(f"[red]Telegram error: {r.text[:100]}[/red]"); return False
    except Exception as e: console.print(f"[red]Telegram error: {e}[/red]"); return False

def telegram_read(limit=5):
    token = data.get("telegram_token")
    if not token: console.print("[yellow]Run /telegramsetup first[/yellow]"); return
    try:
        r = requests.get(f"https://api.telegram.org/bot{token}/getUpdates",
                         params={"limit":limit}, timeout=10)
        updates = r.json().get("result",[])
        if not updates: console.print("[yellow]No messages.[/yellow]"); return
        table = Table(box=box.ROUNDED, border_style="cyan", padding=(0,1))
        table.add_column("From",style="bold cyan"); table.add_column("Message",style="white")
        table.add_column("Time",style="dim")
        for u in updates:
            msg = u.get("message",{})
            table.add_row(msg.get("from",{}).get("first_name","?"),
                          msg.get("text","")[:80],
                          datetime.fromtimestamp(msg.get("date",0)).strftime("%H:%M"))
        console.print(table)
    except Exception as e: console.print(f"[red]Error: {e}[/red]")

# ══════════════════════════════════════════════════════════════════
# EMAIL INTEGRATION (v3.9)
# ══════════════════════════════════════════════════════════════════
def email_setup():
    email    = input("Your email address: ").strip()
    password = input("App password: ").strip()
    smtp     = input("SMTP (Enter=smtp.gmail.com): ").strip() or "smtp.gmail.com"
    data["email_config"] = {"email":email,"password":password,"smtp":smtp}; save_data()
    console.print("[green]✓ Email configured[/green]")

def email_send(to, subject, body):
    cfg = data.get("email_config",{})
    if not cfg: console.print("[yellow]Run /emailsetup first[/yellow]"); return
    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        msg = MIMEMultipart()
        msg["From"] = cfg["email"]; msg["To"] = to; msg["Subject"] = subject
        msg.attach(MIMEText(body,"plain"))
        with smtplib.SMTP_SSL(cfg["smtp"],465) as server:
            server.login(cfg["email"],cfg["password"]); server.send_message(msg)
        console.print(f"[green]✓ Email sent to {to}[/green]")
    except Exception as e: console.print(f"[red]Email error: {e}[/red]")

# ══════════════════════════════════════════════════════════════════
# AUTOMATION / SCHEDULER (v3.9)
# ══════════════════════════════════════════════════════════════════
automation_thread = None

def automation_add(trigger, action, description=""):
    auto = {"id":len(automations)+1,"trigger":trigger,"action":action,
            "description":description,"created":datetime.now().strftime("%d/%m/%Y %H:%M"),"last_run":None}
    automations.append(auto); save_data()
    console.print(f"[green]✓ Automation #{auto['id']}: {description or action}[/green]")

def automation_list():
    if not automations: console.print("[yellow]No automations.[/yellow]"); return
    table = Table(box=box.ROUNDED, border_style="cyan", padding=(0,1))
    table.add_column("#",style="bold cyan"); table.add_column("Trigger",style="yellow")
    table.add_column("Action",style="green"); table.add_column("Description",style="white")
    table.add_column("Last Run",style="dim")
    for a in automations:
        table.add_row(str(a["id"]),a["trigger"],a["action"][:40],
                      a.get("description","")[:30],a.get("last_run","Never"))
    console.print(table)

def automation_remove(auto_id):
    global automations
    automations = [a for a in automations if a["id"] != int(auto_id)]
    save_data(); console.print(f"[green]✓ Removed #{auto_id}[/green]")

def _should_run(auto):
    now = datetime.now(); trigger = auto["trigger"]; last = auto.get("last_run")
    last_dt = datetime.strptime(last,"%d/%m/%Y %H:%M") if last else None
    if trigger.startswith("daily:"):
        parts = trigger.split(":")
        target = datetime.strptime(f"{parts[1]}:{parts[2]}","%H:%M").replace(
            year=now.year,month=now.month,day=now.day)
        return now>=target and (not last_dt or last_dt.date()<now.date())
    elif trigger.startswith("interval:"):
        val = trigger.split(":")[1]
        mins = int(val.replace("m","").replace("h",""))*(60 if "h" in val else 1)
        return not last_dt or (now-last_dt).total_seconds()>=mins*60
    return False

def _execute_automation(client, model, action):
    try:
        if action.startswith("/stock "): get_stock(action[7:].strip().upper())
        elif action.startswith("/weather "): weather(action[9:])
        elif action.startswith("/marketnews"): market_news()
        elif action.startswith("/telegram "): telegram_send(action[10:])
        elif action.startswith("chat:"):
            reply = ask(client, model, action[5:])
            telegram_send(f"Vision Auto:\n{reply}")
        elif action == "/portfolio view": portfolio_view()
        else:
            reply = ask(client, model, action)
            console.print(Panel(Markdown(reply), border_style="magenta"))
    except Exception as e: console.print(f"[red]Auto error: {e}[/red]")

def automation_runner(client, model):
    while True:
        try:
            for auto in automations:
                if _should_run(auto):
                    console.print(f"\n[bold magenta]⚡ Auto: {auto.get('description',auto['action'])}[/bold magenta]")
                    _execute_automation(client, model, auto["action"])
                    auto["last_run"] = datetime.now().strftime("%d/%m/%Y %H:%M")
                    save_data()
        except: pass
        time.sleep(30)

def start_automation_runner(client, model):
    global automation_thread
    if automation_thread and automation_thread.is_alive(): return
    automation_thread = threading.Thread(target=automation_runner,args=(client,model),daemon=True)
    automation_thread.start()
    console.print("[dim]⚡ Automation engine started[/dim]")

# ══════════════════════════════════════════════════════════════════
# VISION INPUT (v3.7)
# ══════════════════════════════════════════════════════════════════
def vision_ask(client, model, image_path, question="What do you see?"):
    try:
        with open(image_path,"rb") as f: image_data = base64.b64encode(f.read()).decode("utf-8")
        ext  = Path(image_path).suffix.lower().lstrip(".")
        ext  = "jpeg" if ext=="jpg" else ext
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role":"user","content":[
                {"type":"image_url","image_url":{"url":f"data:image/{ext};base64,{image_data}"}},
                {"type":"text","text":question}]}],
            max_tokens=1024)
        reply = strip_think(resp.choices[0].message.content or "")
        console.print(Panel(Markdown(reply),title="[bold cyan]👁 Vision[/bold cyan]",border_style="cyan"))
        return reply
    except Exception as e: console.print(f"[red]Vision error: {e}[/red]"); return None

# ══════════════════════════════════════════════════════════════════
# STOCKS
# ══════════════════════════════════════════════════════════════════
def get_stock(symbol):
    try:
        import yfinance as yf
        for suffix in [".NS",".BO",""]:
            info = yf.Ticker(symbol+suffix).info
            price = info.get("currentPrice") or info.get("regularMarketPrice")
            if price:
                prev=info.get("previousClose",price); change=price-prev
                pct=(change/prev*100) if prev else 0
                color="green" if change>=0 else "red"; arrow="▲" if change>=0 else "▼"
                currency="₹" if suffix in [".NS",".BO"] else "$"
                table = Table(box=box.ROUNDED,border_style="cyan",show_header=False,padding=(0,1))
                table.add_column("Key",style="bold cyan",no_wrap=True); table.add_column("Value",style="white")
                table.add_row("Stock",f"[bold]{info.get('longName',symbol)}[/bold]")
                table.add_row("Price",f"[bold {color}]{currency}{price:.2f} {arrow} ({pct:+.2f}%)[/bold {color}]")
                table.add_row("52W High",f"{currency}{info.get('fiftyTwoWeekHigh','N/A')}")
                table.add_row("52W Low",f"{currency}{info.get('fiftyTwoWeekLow','N/A')}")
                table.add_row("Mkt Cap",f"{currency}{info.get('marketCap',0)/1e9:.2f}B" if info.get("marketCap") else "N/A")
                table.add_row("P/E",str(round(info.get("trailingPE",0),2)) if info.get("trailingPE") else "N/A")
                table.add_row("Volume",f"{info.get('volume',0):,}")
                table.add_row("Sector",info.get("sector","N/A"))
                console.print(table)
                memory[f"stock_{symbol}"] = {"value":f"₹{price:.2f} ({pct:+.2f}%)",
                    "tag":"#stock","added":datetime.now().strftime("%d/%m/%Y %H:%M")}
                save_data(); return
        console.print(f"[red]'{symbol}' not found.[/red]")
    except Exception as e: console.print(f"[red]Error: {e}[/red]")

def search_stocks(query):
    try:
        import yfinance as yf
        q = query.lower()
        if q in INDIAN_SECTORS:
            table = Table(box=box.ROUNDED,border_style="cyan",padding=(0,1),
                          title=f"[bold cyan]{q.upper()}[/bold cyan]")
            table.add_column("Symbol",style="bold green"); table.add_column("Price",style="white")
            table.add_column("Change",style="white")
            for sym in INDIAN_SECTORS[q]:
                try:
                    info=yf.Ticker(sym+".NS").info; price=info.get("currentPrice") or info.get("regularMarketPrice",0)
                    prev=info.get("previousClose",price); pct=((price-prev)/prev*100) if prev else 0
                    color="green" if pct>=0 else "red"
                    table.add_row(sym,f"₹{price:.2f}",f"[{color}]{'▲' if pct>=0 else '▼'} {pct:+.2f}%[/{color}]")
                except: table.add_row(sym,"N/A","N/A")
            console.print(table)
        else: console.print(f"[yellow]Sectors: {', '.join(INDIAN_SECTORS.keys())}[/yellow]")
    except Exception as e: console.print(f"[red]Error: {e}[/red]")

def stock_recommend(client, model, query):
    console.print("[yellow]Analyzing...[/yellow]")
    reply = ask(client, model, f"Indian/global stock advisor. Query: {query}\nGive specific picks with thesis, risk, time horizon.")
    console.print(Panel(Markdown(reply),title="[bold]Recommendations[/bold]",border_style="cyan"))

def war_impact(client, model, event):
    console.print("[yellow]Analyzing...[/yellow]")
    reply = ask(client, model, f"How does '{event}' impact Indian AND global stocks? Sectors, NSE/NYSE symbols, commodities, currency.")
    console.print(Panel(Markdown(reply),title="[bold]Market Impact[/bold]",border_style="red"))

def portfolio_add(symbol, qty, buy_price):
    portfolio[symbol.upper()] = {"qty":float(qty),"buy_price":float(buy_price)}
    save_data(); console.print(f"[green]✓ {qty}x {symbol.upper()} @ ₹{buy_price}[/green]")

def portfolio_view():
    if not portfolio: console.print("[yellow]Portfolio empty.[/yellow]"); return
    try:
        import yfinance as yf
        table = Table(box=box.ROUNDED,border_style="cyan",padding=(0,1))
        table.add_column("Symbol",style="bold green"); table.add_column("Qty")
        table.add_column("Buy"); table.add_column("Current")
        table.add_column("P&L"); table.add_column("P&L %")
        total_inv=total_cur=0
        for sym, d in portfolio.items():
            try:
                info=yf.Ticker(sym+".NS").info; cur=info.get("currentPrice") or info.get("regularMarketPrice",d["buy_price"])
                inv=d["qty"]*d["buy_price"]; cv=d["qty"]*cur; pnl=cv-inv
                pct=(pnl/inv*100) if inv else 0; color="green" if pnl>=0 else "red"
                table.add_row(sym,str(d["qty"]),f"₹{d['buy_price']:.2f}",f"₹{cur:.2f}",
                              f"[{color}]₹{pnl:+.2f}[/{color}]",f"[{color}]{pct:+.2f}%[/{color}]")
                total_inv+=inv; total_cur+=cv
            except: table.add_row(sym,str(d["qty"]),f"₹{d['buy_price']:.2f}","N/A","N/A","N/A")
        console.print(table)
        pnl=total_cur-total_inv; pct=(pnl/total_inv*100) if total_inv else 0; color="green" if pnl>=0 else "red"
        console.print(f"[bold]Invested:[/bold] ₹{total_inv:.2f}  [bold {color}]P&L: ₹{pnl:+.2f} ({pct:+.2f}%)[/bold {color}]")
    except Exception as e: console.print(f"[red]Error: {e}[/red]")

def market_news(query="indian stock market"):
    from ddgs import DDGS
    results = []
    with DDGS() as ddgs:
        for r in ddgs.text(f"{query} today",max_results=5):
            results.append(f"**{r['title']}**\n{r['body']}\n{r['href']}")
    console.print(Markdown("\n\n".join(results)))

# ══════════════════════════════════════════════════════════════════
# TOOLS
# ══════════════════════════════════════════════════════════════════
def search(query):
    from ddgs import DDGS
    results=[]
    with DDGS() as ddgs:
        for r in ddgs.text(query,max_results=4):
            results.append(f"**{r['title']}**\n{r['body']}\n{r['href']}")
    return "\n\n".join(results)

def scrape(url):
    try:
        from bs4 import BeautifulSoup
        r=requests.get(url,headers={"User-Agent":"Mozilla/5.0"},timeout=10)
        soup=BeautifulSoup(r.text,"html.parser")
        for tag in soup(["script","style","nav","footer"]): tag.decompose()
        return soup.get_text(separator="\n",strip=True)[:3000]
    except Exception as e: return f"Error: {e}"

def wiki(query):
    try:
        import wikipedia
        summary=wikipedia.summary(query,sentences=5); page=wikipedia.page(query)
        return f"**{page.title}**\n\n{summary}\n\n→ {page.url}"
    except Exception as e: return f"Error: {e}"

def weather(city):
    try:
        r=requests.get(f"https://wttr.in/{city}?format=j1",timeout=10,headers={"User-Agent":"curl/7.68.0"})
        dw=r.json(); current=dw["current_condition"][0]; area=dw["nearest_area"][0]
        desc=current["weatherDesc"][0]["value"]
        ICONS={"sunny":"☀️","clear":"🌙","cloud":"☁️","rain":"🌧️","snow":"❄️",
               "fog":"🌫️","thunder":"⛈️","mist":"🌫️","haze":"🌫️","partly":"⛅"}
        icon=next((v for k,v in ICONS.items() if k in desc.lower()),"🌡️")
        table=Table(box=box.ROUNDED,border_style="cyan",show_header=False,padding=(0,1))
        table.add_column("Key",style="bold cyan",no_wrap=True); table.add_column("Value",style="white")
        table.add_row("Location",f"{area['areaName'][0]['value']}, {area['country'][0]['value']}")
        table.add_row("Condition",f"{icon} {desc}")
        table.add_row("Temp",f"{current['temp_C']}C (Feels {current['FeelsLikeC']}C)")
        table.add_row("Humidity",f"{current['humidity']}%")
        table.add_row("Wind",f"{current['windspeedKmph']} km/h")
        console.print(table)
        memory["last_weather_city"]={"value":city,"tag":"#weather","added":datetime.now().strftime("%d/%m/%Y %H:%M")}
        return None
    except Exception as e: return f"Error: {e}"

def generate_code(client, model, prompt, filename):
    code=re.sub(r"```python|```","",ask(client,model,f"Write Python for: {prompt}\nONLY raw Python.")).strip()
    open(filename,"w").write(code); console.print(f"[green]✓ {filename}[/green]")
    console.print(Markdown(f"```python\n{code}\n```"))

def generate_html(client, model, prompt, filename):
    html=re.sub(r"```html|```","",ask(client,model,f"Write HTML/CSS/JS for: {prompt}\nONLY raw HTML.")).strip()
    open(filename,"w").write(html); console.print(f"[green]✓ {filename}[/green]")

def generate_doc(client, model, prompt, filename):
    doc=ask(client,model,f"Write markdown about: {prompt}\nONLY markdown.")
    open(filename,"w").write(doc); console.print(f"[green]✓ {filename}[/green]"); console.print(Markdown(doc))

def run_file(filename):
    try:
        result=subprocess.run(["python",filename],capture_output=True,text=True,timeout=30)
        console.print(Panel(result.stdout or result.stderr,title=f"[bold]{filename}[/bold]",border_style="green"))
    except Exception as e: console.print(f"[red]{e}[/red]")

def debug_file(client, model, filename):
    try:
        code=open(filename).read()
        fixed=re.sub(r"```python|```","",ask(client,model,f"Fix ONLY:\n\n{code}")).strip()
        open(filename,"w").write(fixed); console.print(f"[green]✓ Fixed: {filename}[/green]")
        console.print(Markdown(f"```python\n{fixed}\n```"))
    except Exception as e: console.print(f"[red]{e}[/red]")

def git_cmd(command):
    result=subprocess.run(f"git {command}",shell=True,capture_output=True,text=True)
    console.print(Panel((result.stdout or result.stderr).strip(),title="[bold]Git[/bold]",border_style="cyan"))

def make_artifact(name, content):
    try:
        if "```python" in content or content.strip().startswith(("def ","import ")):
            ext=".py"; content=re.sub(r"```python|```","",content).strip()
        elif "```html" in content or "<html" in content:
            ext=".html"; content=re.sub(r"```html|```","",content).strip()
        else: ext=".md"
        filename=f"{name.replace(' ','_')}{ext}"
        open(filename,"w").write(content); return f"✓ Saved: '{filename}'"
    except Exception as e: return f"Error: {e}"

def ocr(image_path):
    try:
        import easyocr; console.print("[yellow]Reading...[/yellow]")
        return "\n".join(easyocr.Reader(["en"],gpu=False).readtext(image_path,detail=0))
    except Exception as e: return f"Error: {e}"

async def _browse_async(url):
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=True); page=await browser.new_page()
        await page.goto(url,timeout=15000); title=await page.title()
        content=await page.inner_text("body"); await browser.close()
        return f"**{title}**\n\n{content[:2000]}"

def browse(url): return asyncio.run(_browse_async(url))

# ══════════════════════════════════════════════════════════════════
# CHAT LIBRARY
# ══════════════════════════════════════════════════════════════════
def save_chat(name):
    if not history: console.print("[red]No chat to save.[/red]"); return
    filename=f"{CHATS_DIR}/{name.replace(' ','_')}_{datetime.now().strftime('%d%m%Y_%H%M')}.json"
    with open(filename,"w") as f:
        json.dump({"name":name,"date":datetime.now().strftime("%d/%m/%Y %H:%M"),"messages":history},f,indent=2)
    console.print(f"[green]✓ Saved: '{filename}'[/green]")

def list_chats():
    files=sorted(Path(CHATS_DIR).glob("*.json"))
    if not files: console.print("[yellow]No saved chats.[/yellow]"); return
    table=Table(box=box.ROUNDED,border_style="cyan",padding=(0,1))
    table.add_column("#",style="bold cyan"); table.add_column("Name",style="white")
    table.add_column("Date",style="dim"); table.add_column("Messages",style="white")
    for i, f in enumerate(files,1):
        d=json.load(open(f))
        table.add_row(str(i),d.get("name",f.stem),d.get("date","N/A"),str(len(d.get("messages",[]))))
    console.print(table)

def load_chat(index):
    global history
    files=sorted(Path(CHATS_DIR).glob("*.json"))
    try:
        d=json.load(open(files[int(index)-1])); history=d["messages"]
        console.print(f"[green]✓ Loaded: {d['name']} ({len(history)} messages)[/green]")
    except Exception as e: console.print(f"[red]Error: {e}[/red]")

# ══════════════════════════════════════════════════════════════════
# HELP
# ══════════════════════════════════════════════════════════════════
def show_help(provider_name, model_name=""):
    console.print(Panel(f"""
[bold cyan]Commands:[/bold cyan]

  [bold white]── AI ──[/bold white]
  [green]/model  /provider  /clear  /stream[/green]

  [bold white]── Memory ──[/bold white]
  [green]/memory add <key> <val> [#tag]  /memory view [#tag]  /memory forget <key>[/green]

  [bold white]── Chats ──[/bold white]
  [green]/chats save <n>  /chats list  /chats load <#>[/green]

  [bold white]── Music 🎵 ──[/bold white]
  [green]/play  /pause  /resume  /stop  /skip  /queue  /nowplaying  /volume[/green]

  [bold white]── Voice ──[/bold white]
  [green]/mic on  /mic off[/green]

  [bold white]── Timer ──[/bold white]
  [green]/timer <min>  /stopwatch start/stop/lap/check[/green]

  [bold white]── Image ──[/bold white]
  [green]/imagine <prompt>  /vision <image_path> [question][/green]

  [bold white]── Advisor ──[/bold white]
  [green]/advisor <msg>  /goal add/list/done[/green]

  [bold white]── Council ⚖ ──[/bold white]
  [green]/council <query>  /debate <motion>  /councilsetup[/green]

  [bold white]── Multi-Agent 🤖 ──[/bold white]
  [green]/agent <complex task>[/green]

  [bold white]── GitHub 📁 ──[/bold white]
  [green]/ghconnect  /myrepos  /repoload <user/repo>  /repofile <path>[/green]
  [green]/repoask <question>  /reporeview  /commit <msg>[/green]

  [bold white]── Integrations 🔗 ──[/bold white]
  [green]/telegramsetup  /telegram <msg>  /telegramread[/green]
  [green]/emailsetup  /email <to> | <subject> | <body>[/green]

  [bold white]── Automation ⚡ ──[/bold white]
  [green]/automate <trigger> | <action> | <desc>  /automations  /autodelete <#>[/green]
  [dim]Triggers: daily:09:00   interval:30m   interval:2h[/dim]

  [bold white]── Stocks ──[/bold white]
  [green]/stock  /stocks  /recommend  /impact  /portfolio  /marketnews[/green]

  [bold white]── Code ──[/bold white]
  [green]/code  /html  /doc  /runfile  /debug  /run  /git[/green]

  [bold white]── Tools ──[/bold white]
  [green]/search  /scrape  /browse  /wiki  /weather  /ocr  /artifact[/green]

  [green]/help  /exit  /q[/green]
  [dim]Provider: {provider_name} | Model: {model_name} | Stream: {'ON' if streaming_mode else 'OFF'} | Mic: {'ON 🎤' if mic_mode else 'OFF'} | 🎵 {current_song or 'Nothing'}[/dim]
""", title="[bold]VISION CLI v4.1[/bold]", border_style="cyan"))

# ══════════════════════════════════════════════════════════════════
# STARTUP
# ══════════════════════════════════════════════════════════════════
console.print(BANNER)
console.print(f"\n[bold cyan]  Vision CLI v4.1 — JARVIS Mode Active[/bold cyan]")
if memory:
    console.print(f"[dim]  ✓ {len(memory)} memories | {len(goals)} goals | "
                  f"{len(portfolio)} stocks | {len(automations)} automations[/dim]\n")

provider_choice = select_provider()
client, provider_name = setup_provider(provider_choice)
current_provider_name = provider_name
model = select_model_main(client, provider_name)
# Groq + Rich Live streaming doesn't render properly in Colab — auto-disable
if provider_name == "Groq":
    streaming_mode = False
    console.print("[dim]ℹ Streaming auto-disabled for Groq (Colab compatibility)[/dim]")
show_help(provider_name, model)

council_chairman_id  = None
council_sub_ids      = []
council_sub_names    = []
council_chairman_name = ""

if automations:
    start_automation_runner(client, model)

last_reply = ""

# ══════════════════════════════════════════════════════════════════
# MAIN LOOP
# ══════════════════════════════════════════════════════════════════
while True:
    try:
        user = listen() if mic_mode else input("[YOU] → ").strip()
        if mic_mode and not user: user = input("[YOU 🎤] → ").strip()
    except (EOFError, KeyboardInterrupt):
        save_data(); stop_music(); console.print("\n[bold red]Bye![/bold red]"); break

    if not user: continue

    elif user in ("/exit","/q","/quit"):
        save_data(); stop_music(); console.print("[bold red]Bye![/bold red]"); break
    elif user == "/clear":
        history.clear(); console.print("[green]✓ Cleared[/green]")
    elif user == "/help":
        show_help(provider_name, model)
    elif user == "/model":
        model = select_model_main(client, provider_name)
    elif user == "/provider":
        provider_choice = select_provider()
        client, provider_name = setup_provider(provider_choice)
        current_provider_name = provider_name
        # Groq streaming doesn't render in Colab — auto-disable
        if provider_name == "Groq":
            streaming_mode = False
            console.print("[dim]ℹ Streaming auto-disabled for Groq[/dim]")
        else:
            streaming_mode = True
            console.print("[dim]ℹ Streaming enabled[/dim]")
        model = select_model_main(client, provider_name)
        council_chairman_id=None; council_sub_ids=[]; council_sub_names=[]
        history.clear(); console.print("[dim]Council config reset.[/dim]")
    elif user == "/stream":
        streaming_mode = not streaming_mode
        console.print(f"[green]Streaming: {'ON' if streaming_mode else 'OFF'}[/green]")
    elif user == "/mic on":
        mic_mode=True; console.print("[green]🎤 Mic ON[/green]")
    elif user == "/mic off":
        mic_mode=False; console.print("[yellow]🔇 Mic OFF[/yellow]")

    # Music
    elif user.startswith("/play "):   play_music(user[6:])
    elif user == "/pause":            pause_music()
    elif user == "/resume":           resume_music()
    elif user == "/stop":             stop_music()
    elif user == "/skip":             skip_music()
    elif user.startswith("/queue "): music_queue.append(user[7:]); console.print("[green]✓ Queued[/green]")
    elif user == "/nowplaying":       show_queue()
    elif user.startswith("/volume "): set_volume(user[8:])

    # Memory
    elif user.startswith("/memory add "):
        parts = user[12:].split(" ", 2)
        if len(parts) == 2: memory_add(parts[0], parts[1])
        elif len(parts) == 3:
            if parts[2].startswith("#"): memory_add(parts[0], parts[1], parts[2])
            else: memory_add(parts[0], f"{parts[1]} {parts[2]}")
    elif user.startswith("/memory view"):
        tag = user[13:].strip() or None; memory_view(tag)
    elif user.startswith("/memory forget "):
        memory_forget(user[15:])

    # Chats
    elif user.startswith("/chats save "):  save_chat(user[12:])
    elif user == "/chats list":            list_chats()
    elif user.startswith("/chats load "):  load_chat(user[12:])

    # Timer
    elif user.startswith("/timer "):      study_timer(user[7:])
    elif user.startswith("/stopwatch "): stopwatch_cmd(user[11:].strip())

    # Image / Vision
    elif user.startswith("/imagine "):    generate_image(user[9:])
    elif user.startswith("/vision "):
        parts = user[8:].split(" ", 1)
        vision_ask(client, model, parts[0], parts[1] if len(parts)>1 else "What do you see?")

    # Advisor
    elif user.startswith("/advisor "):
        console.print("[yellow]Advisor thinking...[/yellow]")
        reply = advisor_chat(client, model, user[9:])
        last_reply = reply
        console.print(Panel(Markdown(reply),title="[bold cyan]Your Advisor[/bold cyan]",border_style="cyan"))
        if mic_mode: speak(reply[:300])
    elif user.startswith("/goal add "):
        goals.append({"goal":user[10:],"done":False,"added":datetime.now().strftime("%d/%m/%Y")})
        save_data(); console.print("[green]✓ Goal added[/green]")
    elif user == "/goal list":
        if not goals: console.print("[yellow]No goals.[/yellow]")
        else:
            table=Table(box=box.ROUNDED,border_style="cyan",padding=(0,1))
            table.add_column("#",style="bold cyan"); table.add_column("Goal")
            table.add_column("Status"); table.add_column("Added",style="dim")
            for i, g in enumerate(goals,1):
                table.add_row(str(i),g["goal"],"[green]✓[/green]" if g["done"] else "[yellow]⏳[/yellow]",g["added"])
            console.print(table)
    elif user.startswith("/goal done "):
        try: goals[int(user[11:])-1]["done"]=True; save_data(); console.print("[green]✓ Done![/green]")
        except: console.print("[red]Invalid.[/red]")

    # Council
    elif user == "/councilsetup" or (
        (user.startswith("/council ") or user.startswith("/debate ")) and not council_chairman_id
    ):
        if provider_name != "OpenRouter":
            console.print(Panel(f"[yellow]⚠ On {provider_name}. OpenRouter gives access to ALL models.\nSwitch with /provider for full model list.[/yellow]", border_style="yellow"))
        council_chairman_id, council_sub_ids, council_sub_names, council_chairman_name = \
            select_model_council(client, provider_name)
        start_automation_runner(client, model)
        if user == "/councilsetup":
            console.print("[green]✓ Council ready.[/green]"); continue
        if user.startswith("/council "):
            reply = llm_council(client,user[9:].strip(),council_chairman_id,council_sub_ids,council_sub_names)
            if reply: last_reply=reply
        elif user.startswith("/debate "):
            reply = llm_debate(client,user[8:].strip(),council_chairman_id,council_sub_ids,council_sub_names)
            if reply: last_reply=reply
    elif user.startswith("/council "):
        query = user[9:].strip()
        if query:
            reply = llm_council(client,query,council_chairman_id,council_sub_ids,council_sub_names)
            if reply: last_reply=reply
    elif user.startswith("/debate "):
        motion = user[8:].strip()
        if motion:
            reply = llm_debate(client,motion,council_chairman_id,council_sub_ids,council_sub_names)
            if reply: last_reply=reply

    # Multi-Agent
    elif user.startswith("/agent "):
        reply = spawn_agents(client, model, user[7:].strip())
        if reply: last_reply=reply

    # GitHub
    elif user == "/ghconnect":            github_connect()
    elif user == "/myrepos":              github_list_repos()
    elif user.startswith("/repoload "): github_load_repo(user[10:].strip())
    elif user.startswith("/repofile "): github_read_file(user[10:].strip())
    elif user.startswith("/repoask "):  github_ask(client,model,user[9:].strip())
    elif user == "/reporeview":
        if council_chairman_id: github_council_review(client,council_chairman_id,council_sub_ids,council_sub_names)
        else: console.print("[yellow]Run /councilsetup first[/yellow]")
    elif user.startswith("/commit "):   github_commit(user[8:].strip())

    # Telegram
    elif user == "/telegramsetup":        telegram_setup()
    elif user.startswith("/telegram "): telegram_send(user[10:].strip())
    elif user == "/telegramread":         telegram_read()

    # Email
    elif user == "/emailsetup": email_setup()
    elif user.startswith("/email "):
        parts = user[7:].split("|",2)
        if len(parts)==3: email_send(parts[0].strip(),parts[1].strip(),parts[2].strip())
        else: console.print("[red]Usage: /email <to> | <subject> | <body>[/red]")

    # Automation
    elif user.startswith("/automate "):
        parts = user[10:].split("|",2)
        if len(parts)>=2:
            automation_add(parts[0].strip(),parts[1].strip(),parts[2].strip() if len(parts)==3 else "")
            start_automation_runner(client, model)
        else: console.print("[red]Usage: /automate <trigger> | <action> | <desc>[/red]\n[dim]E.g. /automate daily:09:00 | /marketnews | Morning news[/dim]")
    elif user == "/automations":         automation_list()
    elif user.startswith("/autodelete "): automation_remove(user[12:].strip())

    # Stocks
    elif user.startswith("/stock "):       get_stock(user[7:].strip().upper())
    elif user.startswith("/stocks "):      search_stocks(user[8:].strip())
    elif user.startswith("/recommend "):  stock_recommend(client,model,user[11:])
    elif user.startswith("/impact "):     war_impact(client,model,user[8:])
    elif user == "/marketnews":           market_news()
    elif user.startswith("/marketnews "): market_news(user[12:])
    elif user.startswith("/portfolio "):
        parts = user[11:].split()
        if parts[0]=="add" and len(parts)==4: portfolio_add(parts[1],parts[2],parts[3])
        elif parts[0]=="view": portfolio_view()
        elif parts[0]=="remove" and len(parts)==2:
            sym=parts[1].upper()
            if sym in portfolio: del portfolio[sym]; save_data(); console.print(f"[green]✓ Removed {sym}[/green]")

    # Code
    elif user.startswith("/code "):
        parts=user[6:].split(" ",1)
        if len(parts)==2: generate_code(client,model,parts[1],parts[0])
    elif user.startswith("/html "):
        parts=user[6:].split(" ",1)
        if len(parts)==2: generate_html(client,model,parts[1],parts[0])
    elif user.startswith("/doc "):
        parts=user[5:].split(" ",1)
        if len(parts)==2: generate_doc(client,model,parts[1],parts[0])
    elif user.startswith("/runfile "): run_file(user[9:])
    elif user.startswith("/debug "):   debug_file(client,model,user[7:])
    elif user.startswith("/git "):     git_cmd(user[5:])

    # Tools
    elif user.startswith("/search "):
        console.print("[yellow]Searching...[/yellow]"); console.print(Markdown(search(user[8:])))
    elif user.startswith("/scrape "):
        console.print(Markdown(f"```\n{scrape(user[8:])}\n```"))
    elif user.startswith("/browse "):
        try: console.print(Markdown(browse(user[8:])))
        except Exception as e: console.print(f"[red]{e}[/red]")
    elif user.startswith("/wiki "):
        console.print(Markdown(wiki(user[6:])))
    elif user.startswith("/weather "):
        err=weather(user[9:])
        if err: console.print(f"[red]{err}[/red]")
    elif user.startswith("/artifact "):
        if last_reply: console.print(f"[green]{make_artifact(user[10:],last_reply)}[/green]")
        else: console.print("[red]No reply yet.[/red]")
    elif user.startswith("/ocr "):
        console.print(Markdown(f"```\n{ocr(user[5:])}\n```"))
    elif user.startswith("/run "):
        try: exec(user[5:])
        except Exception as e: console.print(f"[red]{e}[/red]")

    # Main chat
    else:
        console.print("[yellow]Thinking...[/yellow]")
        reply = chat(client, model, user)
        last_reply = reply
        if not streaming_mode:
            console.print(Panel(Markdown(reply), border_style="blue"))
        else:
            # streaming already printed via Live — just add a newline for spacing
            console.print("")
        if mic_mode: speak(reply[:300])
        auto_memory(client, model, user, reply)
