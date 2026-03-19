# MIT License — Copyright (c) 2026 Arshveen Singh
# Vision CLI v1.4.4 — Setup wizard, actionable errors, data cleanup, /export,
# auto web search, /undo, multi-session council, skill marketplace, local API mode.

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
SKILLS_DIR = "vision_skills"
for d in [CHATS_DIR, MUSIC_DIR, AGENTS_DIR, SKILLS_DIR]:
    Path(d).mkdir(exist_ok=True)

# Create default built-in skills if they don't exist
_DEFAULT_SKILLS = {
    "coding.md": """# Skill: Senior Developer
## Role
You are a senior software engineer. Every response involving code must be production-quality.
## Rules
- Always add inline comments explaining non-obvious logic
- Always include error handling (try/except)
- Never use placeholder code or TODOs
- Point out security issues if you spot them
- Prefer Python unless specified otherwise
## Style
Direct, technical, no hand-holding. Treat user as a fellow engineer.""",

    "security.md": """# Skill: Cybersecurity Analyst
## Role
You are an expert ethical hacker and security researcher.
## Rules
- Always mention CVE numbers when relevant
- Flag insecure code immediately with severity (Critical/High/Medium/Low)
- Think like an attacker, respond like a defender
- Reference OWASP, MITRE ATT&CK, NIST where applicable
- For any code: point out attack surfaces, injection risks, auth flaws
## Style
Precise, threat-aware, never sugarcoat a vulnerability.""",

    "research.md": """# Skill: Research Analyst
## Role
You are a deep research analyst. Every answer must be thorough and evidence-backed.
## Rules
- Always structure responses with clear sections
- Cite specific data points, studies, or examples
- Present multiple perspectives before concluding
- Flag uncertainty explicitly — never guess without saying so
- Use tables and comparisons where helpful
## Style
Academic rigor with readable prose. No fluff.""",

    "teacher.md": """# Skill: Patient Teacher
## Role
You are a patient, brilliant teacher who makes complex things simple.
## Rules
- Always use analogies and real-world examples
- Build from fundamentals before going deep
- Check understanding — ask if the explanation made sense
- Never make the user feel dumb for asking basic questions
- Use the Feynman technique: explain simply enough that a 12-year-old gets it
## Style
Warm, encouraging, genuinely excited about knowledge.""",

    "jarvis.md": """# Skill: JARVIS Mode
## Role
You are JARVIS — Vision's most advanced mode. Brief, precise, proactive.
## Rules
- Keep responses short unless depth is genuinely needed
- Anticipate what the user needs next and mention it
- Address user as 'sir' occasionally (not every message)
- Format all code and data cleanly
- Prioritize action over explanation
## Style
Sharp, confident, slightly formal. Tony Stark's assistant energy.""",
}

for fname, content in _DEFAULT_SKILLS.items():
    fpath = Path(SKILLS_DIR) / fname
    if not fpath.exists():
        fpath.write_text(content)

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            d = json.load(f)
        # Migrate old data — add missing keys without breaking existing data
        d.setdefault("council_history", [])
        d.setdefault("usage_log", [])
        d.setdefault("model_scores", {})
        d.setdefault("style_prefs", {})
        d.setdefault("economy", {"sessions":0,"total_mins":0,"commands_used":{},"weekly_reports":[]})
        d.setdefault("predictive_patterns", [])
        return d
    return {
        "memory": {}, "goals": [], "portfolio": {},
        "advisor_history": [], "automations": [],
        "github_token": None, "telegram_token": None,
        "telegram_chat_id": None, "email_config": {},
        "usage_log": [], "model_scores": {}, "style_prefs": {},
        "economy": {"sessions":0,"total_mins":0,"commands_used":{},"weekly_reports":[]},
        "predictive_patterns": [], "council_history": [],
        "created": datetime.now().strftime("%d/%m/%Y"),
        "first_run": True,
    }

def save_data():
    data["memory"]          = memory
    data["goals"]           = goals
    data["portfolio"]       = portfolio
    data["advisor_history"] = advisor_history[-20:]
    data["automations"]     = automations
    data["usage_log"]       = usage_log[-500:]
    data["model_scores"]    = model_scores
    data["style_prefs"]     = style_prefs
    data["economy"]         = economy
    data["predictive_patterns"] = predictive_patterns[-100:]
    data["council_history"] = council_history[-50:]   # keep last 50 council sessions
    data["first_run"]       = False
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)
    _cleanup_data_if_needed()

def _cleanup_data_if_needed():
    """Auto-archive if vision_data.json exceeds 5MB."""
    try:
        size_mb = os.path.getsize(DATA_FILE) / (1024 * 1024)
        if size_mb > 5:
            archive_name = f"vision_data_archive_{datetime.now().strftime('%d%m%Y_%H%M')}.json"
            import shutil
            shutil.copy(DATA_FILE, archive_name)
            # Trim aggressively after archiving
            data["usage_log"]       = data.get("usage_log", [])[-100:]
            data["advisor_history"] = data.get("advisor_history", [])[-10:]
            data["council_history"] = data.get("council_history", [])[-20:]
            data["predictive_patterns"] = data.get("predictive_patterns", [])[-20:]
            with open(DATA_FILE, "w") as f:
                json.dump(data, f, indent=2)
            console.print(f"[dim]📦 Data archived to {archive_name} (was {size_mb:.1f}MB)[/dim]")
    except Exception:
        pass  # never crash on cleanup

data             = load_data()
memory           = data.get("memory", {})
goals            = data.get("goals", [])
portfolio        = data.get("portfolio", {})
advisor_history  = data.get("advisor_history", [])
automations      = data.get("automations", [])
usage_log        = data.get("usage_log", [])
model_scores     = data.get("model_scores", {})
style_prefs      = data.get("style_prefs", {})
economy          = data.get("economy", {"sessions":0,"total_mins":0,"commands_used":{},"weekly_reports":[]})
predictive_patterns = data.get("predictive_patterns", [])
council_history  = data.get("council_history", [])   # multi-session council storage
session_start    = datetime.now()
history               = []
mic_mode              = False
last_request_time     = 0
streaming_mode        = True
current_provider_name = ""

# Undo stack — stores last 10 reversible actions
undo_stack = []  # each entry: {"type": "memory"|"automation", "action": "add"|"delete", "data": {...}}

def get_max_tokens(base=2048):
    """
    Groq free tier has a tight tokens-per-minute (TPM) cap.
    Capping at 1024 prevents mid-response cutoff on Kimi and other large models.
    All other providers use the full base limit.
    """
    return 1024 if current_provider_name == "Groq" else base

# ── Context window config ─────────────────────────────────────────
# MAX_HISTORY  — how many messages before rolling summarization kicks in
# KEEP_RECENT  — how many recent messages to keep verbatim after summarizing
# SUMMARY_TAKE — how many oldest messages get compressed into a summary block
MAX_HISTORY  = 40   # bigger window than before (was 20, hard-trim)
KEEP_RECENT  = 20   # always keep last 20 messages verbatim
SUMMARY_TAKE = 20   # summarize the oldest 20 when limit hit

# Rolling summaries — stored as a single injected context block
conversation_summary      = ""   # main chat rolling summary
advisor_summary           = ""   # advisor chat rolling summary

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
    undo_push("memory", "add", {"key": key, "value": memory[key]})
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
# ACTIONABLE ERROR HELPER
# ══════════════════════════════════════════════════════════════════
def actionable_error(err_str, context=""):
    """
    Converts raw API errors into human-readable fixes.
    Never shows raw stack traces to user.
    """
    err = err_str.lower()
    if "rate limit" in err or "429" in err:
        console.print(Panel(
            "[bold yellow]⏳ Rate limit hit[/bold yellow]\n\n"
            "Vision is waiting and will retry automatically.\n"
            f"[dim]Tip: Switch to a faster provider with /provider, or try llama-3.1-8b-instant on Groq.[/dim]",
            border_style="yellow"))
    elif "model" in err and any(x in err for x in ["not found","does not exist","invalid"]):
        console.print(Panel(
            f"[bold red]✗ Model not found[/bold red]\n\n"
            f"[dim]{context}[/dim]\n\n"
            "Try:\n"
            "  • [cyan]/model[/cyan] to pick a different model\n"
            "  • [cyan]/provider[/cyan] to switch provider\n"
            "  • Check exact model ID at openrouter.ai/models",
            border_style="red"))
    elif "401" in err or "auth" in err or "api key" in err:
        console.print(Panel(
            "[bold red]✗ Authentication failed[/bold red]\n\n"
            "Your API key is invalid or expired.\n\n"
            "Fix:\n"
            "  • Run [cyan]/provider[/cyan] and re-enter your key\n"
            "  • Or set env var: [cyan]os.environ['GROQ_API_KEY'] = 'gsk_...'[/cyan]",
            border_style="red"))
    elif "connection" in err or "timeout" in err or "network" in err:
        console.print(Panel(
            "[bold yellow]⚠ Network error[/bold yellow]\n\n"
            "Can't reach the provider. Check your connection.\n"
            "[dim]If on Colab, the session may have timed out. Reconnect and rerun.[/dim]",
            border_style="yellow"))
    elif "<!doctype" in err or "cannot post" in err or "<html" in err:
        console.print(Panel(
            "[bold red]✗ Endpoint error[/bold red]\n\n"
            "Provider returned an HTML error page — model ID is wrong or endpoint is down.\n"
            "  • Run [cyan]/model[/cyan] and pick from the suggested list\n"
            "  • For Bytez: use HuggingFace format e.g. [cyan]Qwen/Qwen2-7B-Instruct[/cyan]",
            border_style="red"))
    elif "context" in err or "token" in err and "limit" in err:
        console.print(Panel(
            "[bold yellow]⚠ Context too long[/bold yellow]\n\n"
            "Message history too long for this model's context window.\n"
            "  • Run [cyan]/clear[/cyan] to start fresh\n"
            "  • Or use a model with larger context (e.g. [cyan]moonshotai/kimi-k2[/cyan] on OpenRouter)",
            border_style="yellow"))
    else:
        console.print(Panel(
            f"[bold red]✗ Error[/bold red]\n\n{err_str[:300]}\n\n"
            "[dim]Run /model or /provider if this keeps happening.[/dim]",
            border_style="red"))

# ══════════════════════════════════════════════════════════════════
# SETUP WIZARD
# ══════════════════════════════════════════════════════════════════
def run_setup_wizard():
    """
    First-run interactive setup wizard.
    Guides user through provider selection, API key, test call.
    Only runs when vision_data.json doesn't exist or first_run=True.
    """
    console.print(Panel(
        "[bold cyan]👋 Welcome to Vision CLI v4.4[/bold cyan]\n\n"
        "First-time setup — takes about 60 seconds.\n"
        "Vision will guide you through choosing a provider and testing your connection.\n\n"
        "[dim]You can skip any step with Enter and configure later.[/dim]",
        border_style="cyan"))

    console.print("\n[bold white]Step 1 — Choose your AI provider[/bold white]\n")
    console.print("Recommended for first-timers:\n")
    console.print("  [bold green][1] Groq[/bold green]       — Free, ultra fast, no credit card needed")
    console.print("             Get key: [cyan]console.groq.com[/cyan]")
    console.print("  [bold green][2] OpenRouter[/bold green] — Access 200+ models, generous free tier")
    console.print("             Get key: [cyan]openrouter.ai/keys[/cyan]")
    console.print("  [bold green][3] Ollama[/bold green]     — 100% local, completely free, no internet needed")
    console.print("             Install: [cyan]ollama.ai[/cyan]")
    console.print("  [dim][4] Skip — I'll configure manually[/dim]\n")

    choice = input("→ Pick (1-4): ").strip()

    if choice == "4" or not choice:
        console.print("[dim]Skipping wizard. Run /provider to configure later.[/dim]\n")
        return None, None

    provider_map = {"1":"1","2":"2","3":"3"}
    provider_choice = provider_map.get(choice, "1")

    console.print("\n[bold white]Step 2 — API Key[/bold white]\n")
    if choice == "3":
        console.print("[dim]Ollama runs locally — no API key needed.[/dim]")
        console.print("[dim]Make sure Ollama is running: ollama serve[/dim]\n")
    elif choice == "1":
        console.print("Get your free Groq key at: [cyan]console.groq.com[/cyan]")
        console.print("[dim]It's free. No credit card. Takes 30 seconds.[/dim]\n")
        key = input("→ Paste your Groq API key (or Enter to skip): ").strip()
        if key:
            os.environ["GROQ_API_KEY"] = key
            console.print("[green]✓ Key saved for this session[/green]")
            console.print("[dim]To make permanent: add to Colab secrets or your shell profile[/dim]")
    elif choice == "2":
        console.print("Get your free OpenRouter key at: [cyan]openrouter.ai/keys[/cyan]")
        console.print("[dim]Free tier gives access to many models including DeepSeek R1, Kimi K2, LLaMA 3.3.[/dim]\n")
        key = input("→ Paste your OpenRouter key (or Enter to skip): ").strip()
        if key:
            os.environ["OPENROUTER_API_KEY"] = key
            console.print("[green]✓ Key saved for this session[/green]")

    console.print("\n[bold white]Step 3 — Quick features overview[/bold white]\n")
    features = [
        ("💬 Chat",        "Just type anything — Vision answers"),
        ("⚖ Council",      "/council <question> — multiple models debate"),
        ("🧠 Skills",       "/skill load security — Vision becomes a security expert"),
        ("📊 Stocks",       "/stock RELIANCE — live NSE prices"),
        ("🤖 Multi-agent",  "/agent <complex task> — parallel AI workers"),
        ("⚡ Automation",   "/automate daily:09:00 | /marketnews | Morning news"),
        ("🔍 Memory",       "/memory add name Arshveen — Vision remembers forever"),
        ("📁 GitHub",       "/ghconnect — load your repos into context"),
    ]
    for icon_name, desc in features:
        console.print(f"  {icon_name:<20} {desc}")

    console.print(f"\n[dim]Type /help anytime to see all {70}+ commands.[/dim]\n")
    console.print(Panel(
        "[bold green]✓ Setup complete![/bold green]\n\n"
        "Vision CLI is ready. Start by typing anything, or try:\n"
        "  [cyan]/skill list[/cyan]  →  see available skills\n"
        "  [cyan]/help[/cyan]        →  full command reference",
        border_style="green"))

    return provider_choice, None

# ══════════════════════════════════════════════════════════════════
# UNDO SYSTEM
# ══════════════════════════════════════════════════════════════════
def undo_push(action_type, action, item_data):
    """Push to undo stack. Max 10 entries."""
    undo_stack.append({"type":action_type,"action":action,"data":item_data,"time":datetime.now().strftime("%H:%M:%S")})
    if len(undo_stack) > 10:
        undo_stack.pop(0)

def undo_last():
    """Undo the last reversible action."""
    if not undo_stack:
        console.print("[yellow]Nothing to undo.[/yellow]"); return
    last = undo_stack.pop()
    t    = last["type"]
    a    = last["action"]
    d    = last["data"]
    if t == "memory" and a == "add":
        key = d.get("key","")
        if key in memory:
            del memory[key]; save_data()
            console.print(f"[green]✓ Undone — removed memory: {key}[/green]")
    elif t == "memory" and a == "delete":
        memory[d["key"]] = d["value"]; save_data()
        console.print(f"[green]✓ Undone — restored memory: {d['key']}[/green]")
    elif t == "automation" and a == "add":
        global automations
        automations = [x for x in automations if x.get("id") != d.get("id")]
        save_data()
        console.print(f"[green]✓ Undone — removed automation #{d.get('id')}[/green]")
    elif t == "goal" and a == "add":
        global goals
        if goals: goals.pop(); save_data()
        console.print(f"[green]✓ Undone — removed last goal[/green]")
    else:
        console.print(f"[yellow]Can't undo: {t}/{a}[/yellow]")

def undo_show():
    """Show undo history."""
    if not undo_stack:
        console.print("[yellow]Undo stack empty.[/yellow]"); return
    table = Table(box=box.ROUNDED, border_style="cyan", padding=(0,1))
    table.add_column("#",      style="bold cyan")
    table.add_column("Type",   style="white")
    table.add_column("Action", style="green")
    table.add_column("Data",   style="dim")
    table.add_column("Time",   style="dim")
    for i, e in enumerate(reversed(undo_stack), 1):
        table.add_row(str(i), e["type"], e["action"],
                      str(e["data"])[:40], e["time"])
    console.print(table)
    console.print("[dim]Type /undo to undo the most recent action.[/dim]")

# ══════════════════════════════════════════════════════════════════
# EXPORT SYSTEM
# ══════════════════════════════════════════════════════════════════
def export_session(label="session"):
    """Export current session — chat, council verdict, memories — to markdown."""
    filename = f"vision_export_{label.replace(' ','_')}_{datetime.now().strftime('%d%m%Y_%H%M')}.md"
    lines = [
        f"# Vision CLI Export — {label}",
        f"**Date:** {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        f"**Provider:** {current_provider_name}",
        "",
    ]
    if conversation_summary:
        lines += ["## 📝 Conversation Summary", conversation_summary, ""]
    if history:
        lines += ["## 💬 Chat History"]
        for m in history:
            role = "**You**" if m["role"]=="user" else "**Vision**"
            lines.append(f"\n{role}:\n{m['content'][:500]}")
        lines.append("")
    if last_council_verdict:
        lines += ["## ⚖ Last Council Verdict", last_council_verdict, ""]
    if last_agent_result:
        lines += ["## 🤖 Last Agent Analysis", last_agent_result[:1000], ""]
    if memory:
        lines += ["## 🧠 Memories"]
        for k, v in memory.items():
            lines.append(f"- **{k}**: {v['value']} {v.get('tag','')}")
        lines.append("")
    if goals:
        lines += ["## 🎯 Goals"]
        for g in goals:
            status = "✅" if g["done"] else "⏳"
            lines.append(f"- {status} {g['goal']}")
        lines.append("")
    if portfolio:
        lines += ["## 📊 Portfolio"]
        for sym, d in portfolio.items():
            lines.append(f"- {sym}: {d['qty']}x @ ₹{d['buy_price']}")
        lines.append("")
    content = "\n".join(lines)
    try:
        open(filename,"w").write(content)
        console.print(Panel(
            f"[bold green]✓ Exported: {filename}[/bold green]\n\n"
            f"[dim]{len(lines)} lines — chat, memories, goals, portfolio[/dim]\n"
            f"[dim]Find it in your Colab file browser (left sidebar)[/dim]",
            border_style="green"))
    except Exception as e:
        console.print(f"[red]Export failed: {e}[/red]")

# ══════════════════════════════════════════════════════════════════
# MULTI-SESSION COUNCIL HISTORY
# ══════════════════════════════════════════════════════════════════
def council_save_session(query, verdict, session_type="council"):
    """Save council verdict to persistent history."""
    entry = {
        "id":      len(council_history) + 1,
        "date":    datetime.now().strftime("%d/%m/%Y %H:%M"),
        "type":    session_type,
        "query":   query,
        "verdict": verdict,
        "models":  current_provider_name,
    }
    council_history.append(entry)
    save_data()

def council_history_show(limit=10):
    """Show past council sessions."""
    if not council_history:
        console.print("[yellow]No council history yet. Run /council or /debate first.[/yellow]"); return
    table = Table(box=box.ROUNDED, border_style="cyan", padding=(0,1))
    table.add_column("#",      style="bold cyan")
    table.add_column("Date",   style="dim")
    table.add_column("Type",   style="yellow")
    table.add_column("Query",  style="white")
    for e in council_history[-limit:]:
        table.add_row(str(e["id"]), e["date"], e["type"], e["query"][:60])
    console.print(table)
    console.print("[dim]/council history view <#> — see full verdict[/dim]")

def council_history_view(idx):
    """Show full verdict for a past council session."""
    try:
        idx = int(idx)
        entry = next((e for e in council_history if e["id"]==idx), None)
        if not entry:
            console.print(f"[red]Council session #{idx} not found.[/red]"); return
        console.print(Panel(
            f"[bold cyan]⚖ Council Session #{idx}[/bold cyan]\n\n"
            f"[white]Date:[/white]   {entry['date']}\n"
            f"[white]Type:[/white]   {entry['type']}\n"
            f"[white]Query:[/white]  {entry['query']}\n\n"
            f"[bold yellow]Verdict:[/bold yellow]\n{entry['verdict']}",
            border_style="cyan"))
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

def council_history_compare(idx1, idx2, client, model):
    """Ask Vision to compare two past council verdicts."""
    try:
        e1 = next((e for e in council_history if e["id"]==int(idx1)), None)
        e2 = next((e for e in council_history if e["id"]==int(idx2)), None)
        if not e1 or not e2:
            console.print("[red]One or both sessions not found.[/red]"); return
        prompt = (
            f"Compare these two council verdicts:\n\n"
            f"Session #{e1['id']} ({e1['date']}) — {e1['query']}\n"
            f"Verdict: {e1['verdict'][:600]}\n\n"
            f"Session #{e2['id']} ({e2['date']}) — {e2['query']}\n"
            f"Verdict: {e2['verdict'][:600]}\n\n"
            f"What changed? What's consistent? What's the most important difference?"
        )
        console.print("[yellow]Comparing council sessions...[/yellow]")
        reply = ask(client, model, prompt)
        console.print(Panel(Markdown(reply),
                            title=f"[bold cyan]⚖ Council Compare: #{idx1} vs #{idx2}[/bold cyan]",
                            border_style="cyan"))
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

def handle_council_history(user, client, model):
    """Route /council history subcommands."""
    parts = user.split()
    # /council history → list
    # /council history view <#>
    # /council history compare <#> <#>
    if len(parts) == 2:
        council_history_show()
    elif len(parts) == 4 and parts[2] == "view":
        council_history_view(parts[3])
    elif len(parts) == 5 and parts[2] == "compare":
        council_history_compare(parts[3], parts[4], client, model)
    else:
        console.print("[dim]/council history | /council history view <#> | /council history compare <#> <#>[/dim]")

# ══════════════════════════════════════════════════════════════════
# SKILL MARKETPLACE
# ══════════════════════════════════════════════════════════════════
MARKETPLACE_BASE = "https://raw.githubusercontent.com/Arshveen-singh/Vision-CLI/main/marketplace/skills"
MARKETPLACE_INDEX = f"{MARKETPLACE_BASE}/index.json"

def skill_marketplace_list():
    """Fetch and show available skills from GitHub marketplace."""
    console.print("[yellow]Fetching marketplace...[/yellow]")
    try:
        r = requests.get(MARKETPLACE_INDEX, timeout=10)
        if r.status_code != 200:
            console.print(Panel(
                "[yellow]Marketplace index not found yet.[/yellow]\n\n"
                "The skills marketplace is at:\n"
                "[cyan]github.com/Arshveen-singh/Vision-CLI/tree/main/marketplace/skills[/cyan]\n\n"
                "To contribute a skill:\n"
                "1. Create your skill file in vision_skills/\n"
                "2. Open a PR adding it to marketplace/skills/\n"
                "3. Update marketplace/skills/index.json",
                border_style="yellow"))
            return
        skills = r.json()
        table = Table(box=box.ROUNDED, border_style="cyan", padding=(0,1),
                      title="[bold cyan]🛒 Skill Marketplace[/bold cyan]")
        table.add_column("Name",        style="bold green")
        table.add_column("Description", style="white")
        table.add_column("Author",      style="dim")
        table.add_column("Installed",   style="cyan")
        for s in skills:
            installed = "✅" if (Path(SKILLS_DIR)/f"{s['name']}.md").exists() else ""
            table.add_row(s["name"], s.get("description","")[:50],
                          s.get("author","?"), installed)
        console.print(table)
        console.print("[dim]/skill install <name> — install a marketplace skill[/dim]")
    except Exception as e:
        console.print(f"[red]Marketplace unavailable: {e}[/red]")
        console.print("[dim]Check your internet connection.[/dim]")

def skill_install(name):
    """Download and install a skill from the GitHub marketplace."""
    name = name.strip().lower().replace(".md","")
    dest = Path(SKILLS_DIR) / f"{name}.md"
    if dest.exists():
        console.print(f"[yellow]Skill '{name}' already installed. Use /skill reload {name} if you updated it.[/yellow]")
        return
    url = f"{MARKETPLACE_BASE}/{name}.md"
    console.print(f"[yellow]Downloading skill: {name}...[/yellow]")
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            dest.write_text(r.text)
            console.print(Panel(
                f"[bold green]✓ Installed: {name}[/bold green]\n\n"
                f"[dim]Saved to vision_skills/{name}.md[/dim]\n\n"
                f"Load it: [cyan]/skill load {name}[/cyan]",
                border_style="green"))
        elif r.status_code == 404:
            console.print(Panel(
                f"[red]Skill '{name}' not found in marketplace.[/red]\n\n"
                "Check available skills with [cyan]/skill marketplace[/cyan]\n"
                "Or create your own: [cyan]/skill create {name}[/cyan]",
                border_style="red"))
        else:
            console.print(f"[red]Download failed: HTTP {r.status_code}[/red]")
    except Exception as e:
        console.print(f"[red]Install failed: {e}[/red]")

# ══════════════════════════════════════════════════════════════════
# AUTO WEB SEARCH
# ══════════════════════════════════════════════════════════════════
_UNCERTAINTY_PHRASES = [
    "i don't know", "i'm not sure", "i cannot find", "i don't have access",
    "my knowledge", "i'm unable to", "as of my", "i lack", "not aware of",
    "cannot confirm", "no information", "i don't have real-time",
    "i don't have current", "beyond my knowledge", "i can't verify",
]

def _needs_web_search(reply):
    """Detect if Vision's reply signals uncertainty — auto-trigger search."""
    lower = reply.lower()
    return any(phrase in lower for phrase in _UNCERTAINTY_PHRASES)

def auto_web_search_and_enhance(client, model, user_input, initial_reply):
    """
    If Vision's initial reply signals uncertainty, auto-search DuckDuckGo
    and generate an enhanced answer with sources.
    Runs transparently — user sees "Searching for more info..." then enhanced reply.
    """
    if not _needs_web_search(initial_reply):
        return initial_reply
    console.print("[dim]🔍 Auto-searching for current info...[/dim]")
    try:
        from ddgs import DDGS
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(user_input, max_results=3):
                results.append(f"Source: {r['href']}\n{r['title']}\n{r['body'][:300]}")
        if not results:
            return initial_reply
        search_context = "\n\n".join(results)
        enhance_prompt = (
            f"User asked: {user_input}\n\n"
            f"Web search results:\n{search_context}\n\n"
            f"Using the search results above, give a complete, accurate answer. "
            f"Cite sources naturally. Be direct."
        )
        rate_limit(model)
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role":"system","content":SYSTEM_PROMPT},
                      {"role":"user","content":enhance_prompt}],
            max_tokens=get_max_tokens(1500))
        enhanced = strip_think(resp.choices[0].message.content or initial_reply)
        console.print("[dim]✓ Enhanced with web search[/dim]")
        return enhanced
    except Exception:
        return initial_reply  # fall back to original reply silently

# ══════════════════════════════════════════════════════════════════
# LOCAL API MODE
# ══════════════════════════════════════════════════════════════════
def start_api_server(client, model, host="127.0.0.1", port=7842):
    """
    Start a local Flask HTTP server exposing Vision CLI as an API.
    100% local — no cloud, no external server. localhost only.

    Endpoints:
      POST /chat          {"message": "..."}  → {"reply": "..."}
      POST /advisor       {"message": "..."}  → {"reply": "..."}
      GET  /memory        → {"memory": {...}}
      POST /memory        {"key":"...","value":"...","tag":"..."} → {"ok": true}
      GET  /status        → {"model": "...", "provider": "...", "memories": N}
    """
    try:
        from flask import Flask, request, jsonify
    except ImportError:
        console.print(Panel(
            "[yellow]Flask not installed.[/yellow]\n\n"
            "Install it: [cyan]!pip install flask[/cyan]\n"
            "Then restart Vision CLI with [cyan]--api[/cyan] flag.",
            border_style="yellow"))
        return

    app = Flask("VisionCLI")
    app.config["JSON_SORT_KEYS"] = False

    @app.route("/status", methods=["GET"])
    def status():
        return jsonify({
            "version":  "4.4",
            "model":    model,
            "provider": current_provider_name,
            "memories": len(memory),
            "goals":    len(goals),
            "skills":   active_skills,
        })

    @app.route("/chat", methods=["POST"])
    def api_chat():
        try:
            msg   = request.json.get("message","")
            if not msg: return jsonify({"error":"message required"}), 400
            reply = chat(client, model, msg)
            return jsonify({"reply": reply})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/advisor", methods=["POST"])
    def api_advisor():
        try:
            msg   = request.json.get("message","")
            if not msg: return jsonify({"error":"message required"}), 400
            reply = advisor_chat(client, model, msg)
            return jsonify({"reply": reply})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/memory", methods=["GET"])
    def api_memory_get():
        return jsonify({"memory": memory})

    @app.route("/memory", methods=["POST"])
    def api_memory_post():
        try:
            key   = request.json.get("key","")
            value = request.json.get("value","")
            tag   = request.json.get("tag","")
            if not key or not value: return jsonify({"error":"key and value required"}), 400
            memory_add(key, value, tag)
            return jsonify({"ok": True})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/stock/<symbol>", methods=["GET"])
    def api_stock(symbol):
        try:
            import yfinance as yf
            info = yf.Ticker(symbol+".NS").info
            return jsonify({
                "symbol":  symbol,
                "price":   info.get("currentPrice") or info.get("regularMarketPrice"),
                "change":  info.get("regularMarketChangePercent"),
                "name":    info.get("longName",""),
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    console.print(Panel(
        f"[bold cyan]🌐 Vision CLI API Mode[/bold cyan]\n\n"
        f"Local server running at: [green]http://{host}:{port}[/green]\n\n"
        f"Endpoints:\n"
        f"  [cyan]GET  /status[/cyan]       — current state\n"
        f"  [cyan]POST /chat[/cyan]         — {{\"message\": \"...\"}}\n"
        f"  [cyan]POST /advisor[/cyan]      — {{\"message\": \"...\"}}\n"
        f"  [cyan]GET  /memory[/cyan]       — all memories\n"
        f"  [cyan]POST /memory[/cyan]       — add memory\n"
        f"  [cyan]GET  /stock/<SYM>[/cyan]  — live stock data\n\n"
        f"[dim]100% local — only accessible from this machine.[/dim]\n"
        f"[dim]Press Ctrl+C to stop the API server.[/dim]",
        border_style="cyan"))

    try:
        app.run(host=host, port=port, debug=False, use_reloader=False)
    except Exception as e:
        console.print(f"[red]API server error: {e}[/red]")

# ══════════════════════════════════════════════════════════════════
# SKILLS SYSTEM
# ══════════════════════════════════════════════════════════════════
def _rebuild_skill_content():
    """Rebuild combined skill instruction string from active skills."""
    global active_skill_content
    if not active_skills:
        active_skill_content = ""
        return
    parts = []
    for name in active_skills:
        path = Path(SKILLS_DIR) / f"{name}.md"
        if path.exists():
            parts.append(path.read_text())
    active_skill_content = "\n\n".join(parts)

def skill_load(name):
    """Load a skill by name (without .md extension)."""
    global active_skills
    name = name.strip().lower().replace(".md","")
    path = Path(SKILLS_DIR) / f"{name}.md"
    if not path.exists():
        console.print(f"[red]Skill '{name}' not found. Use /skill list to see available skills.[/red]")
        return
    if name in active_skills:
        console.print(f"[yellow]Skill '{name}' already active.[/yellow]")
        return
    active_skills.append(name)
    _rebuild_skill_content()
    console.print(Panel(
        f"[bold green]✓ Skill loaded: {name}[/bold green]\n\n"
        f"[dim]Active skills: {', '.join(active_skills)}[/dim]\n"
        f"[dim]Vision will now behave according to this skill.[/dim]",
        border_style="green"))

def skill_unload(name):
    global active_skills
    name = name.strip().lower().replace(".md","")
    if name not in active_skills:
        console.print(f"[yellow]Skill '{name}' is not active.[/yellow]"); return
    active_skills.remove(name)
    _rebuild_skill_content()
    console.print(f"[green]✓ Skill unloaded: {name}[/green]")
    if active_skills:
        console.print(f"[dim]Still active: {', '.join(active_skills)}[/dim]")

def skill_list():
    files = sorted(Path(SKILLS_DIR).glob("*.md"))
    if not files:
        console.print("[yellow]No skills found in vision_skills/[/yellow]"); return
    table = Table(box=box.ROUNDED, border_style="cyan", padding=(0,1))
    table.add_column("Skill",   style="bold cyan")
    table.add_column("Status",  style="white")
    table.add_column("Preview", style="dim")
    for f in files:
        name    = f.stem
        status  = "[bold green]● ACTIVE[/bold green]" if name in active_skills else "[dim]○ idle[/dim]"
        content = f.read_text()
        # Extract first ## Role line as preview
        preview = next((l.strip() for l in content.splitlines()
                        if l.strip() and not l.startswith("#")), content[:60])
        table.add_row(name, status, preview[:60])
    console.print(table)
    if active_skills:
        console.print(f"\n[bold green]Active:[/bold green] {', '.join(active_skills)}")
    else:
        console.print("\n[dim]No skills active. Use /skill load <name>[/dim]")

def skill_active():
    if not active_skills:
        console.print("[yellow]No skills active. Default Vision mode.[/yellow]"); return
    for name in active_skills:
        path = Path(SKILLS_DIR) / f"{name}.md"
        if path.exists():
            console.print(Panel(Markdown(path.read_text()),
                                title=f"[bold cyan]Skill: {name}[/bold cyan]",
                                border_style="cyan"))

def skill_clear():
    global active_skills
    active_skills = []
    _rebuild_skill_content()
    console.print("[green]✓ All skills cleared. Back to default Vision mode.[/green]")

def skill_create(name):
    """Create a new custom skill file and open it for editing."""
    name = name.strip().lower().replace(".md","").replace(" ","_")
    path = Path(SKILLS_DIR) / f"{name}.md"
    if path.exists():
        console.print(f"[yellow]Skill '{name}' already exists. Edit it at: {path}[/yellow]"); return
    template = f"""# Skill: {name.title()}
## Role
Describe what role Vision should take on when this skill is active.

## Rules
- Rule 1
- Rule 2
- Rule 3

## Style
Describe the communication style, tone, and format preferences.
"""
    path.write_text(template)
    console.print(Panel(
        f"[bold green]✓ Skill created: {name}[/bold green]\n\n"
        f"[white]File:[/white] vision_skills/{name}.md\n\n"
        f"[dim]Edit the file to customize the skill, then run:[/dim]\n"
        f"[cyan]/skill load {name}[/cyan]",
        border_style="green"))

def skill_edit(name):
    """Print the skill file content for user to see and edit."""
    name = name.strip().lower().replace(".md","")
    path = Path(SKILLS_DIR) / f"{name}.md"
    if not path.exists():
        console.print(f"[red]Skill '{name}' not found.[/red]"); return
    console.print(Panel(
        Markdown(f"```markdown\n{path.read_text()}\n```"),
        title=f"[bold cyan]vision_skills/{name}.md[/bold cyan]",
        border_style="cyan"))
    console.print(f"[dim]Edit the file directly, then /skill reload {name}[/dim]")

def skill_reload(name):
    """Reload a skill that's already active (after editing)."""
    name = name.strip().lower().replace(".md","")
    if name in active_skills:
        _rebuild_skill_content()
        console.print(f"[green]✓ Skill reloaded: {name}[/green]")
    else:
        console.print(f"[yellow]Skill '{name}' not active. Use /skill load {name}[/yellow]")

def handle_skill_command(user):
    """Route /skill subcommands."""
    parts = user[7:].strip().split(" ", 1)
    sub   = parts[0].lower() if parts else ""
    arg   = parts[1].strip() if len(parts) > 1 else ""

    if sub == "list":                    skill_list()
    elif sub == "active":                skill_active()
    elif sub == "clear":                 skill_clear()
    elif sub == "load"   and arg:        skill_load(arg)
    elif sub == "unload" and arg:        skill_unload(arg)
    elif sub == "create" and arg:        skill_create(arg)
    elif sub == "edit"   and arg:        skill_edit(arg)
    elif sub == "reload" and arg:        skill_reload(arg)
    elif sub == "help" or not sub:
        console.print(Panel("""[bold cyan]Skills — Commands[/bold cyan]

  [green]/skill list[/green]             — show all skills (active + available)
  [green]/skill load <name>[/green]      — activate a skill
  [green]/skill unload <name>[/green]    — deactivate a skill
  [green]/skill active[/green]           — show full content of active skills
  [green]/skill clear[/green]            — clear all skills, back to default
  [green]/skill create <name>[/green]    — create a new custom skill
  [green]/skill edit <name>[/green]      — view skill file content
  [green]/skill reload <name>[/green]    — reload skill after editing

  [bold white]Built-in skills:[/bold white]
  [dim]coding    security    research    teacher    jarvis[/dim]

  [bold white]Stack multiple:[/bold white]
  [dim]/skill load security
  /skill load coding    ← both active simultaneously[/dim]

  [bold white]Custom skill files live in:[/bold white] [dim]vision_skills/[/dim]""",
        border_style="cyan"))
    else:
        console.print("[red]Unknown skill command. Try /skill help[/red]")

# ══════════════════════════════════════════════════════════════════
# SELF-IMPROVING ENGINE (v4.1)
# ══════════════════════════════════════════════════════════════════
def _track_usage(command, content=""):
    """Log every command for pattern learning."""
    entry = {
        "cmd":   command,
        "time":  datetime.now().strftime("%d/%m/%Y %H:%M"),
        "day":   datetime.now().strftime("%A"),
        "hour":  datetime.now().hour,
        "len":   len(content)
    }
    usage_log.append(entry)
    # Track in economy
    economy["commands_used"][command] = economy["commands_used"].get(command, 0) + 1

def _track_model_score(model, task_type, success=True, response_len=0):
    """Track model performance per task type for auto-optimization."""
    key = f"{model}::{task_type}"
    if key not in model_scores:
        model_scores[key] = {"success":0,"fail":0,"avg_len":0,"calls":0}
    if success:
        model_scores[key]["success"] += 1
    else:
        model_scores[key]["fail"] += 1
    model_scores[key]["calls"] += 1
    # Rolling average response length
    prev_avg = model_scores[key]["avg_len"]
    calls    = model_scores[key]["calls"]
    model_scores[key]["avg_len"] = (prev_avg*(calls-1) + response_len) / calls

def self_improve_report(client, model):
    """Analyze usage patterns and generate self-improvement suggestions."""
    if len(usage_log) < 10:
        console.print("[yellow]Need at least 10 commands tracked before generating insights.[/yellow]")
        return

    # Build usage summary
    from collections import Counter
    cmd_counts = Counter([e["cmd"] for e in usage_log])
    hour_counts = Counter([e["hour"] for e in usage_log])
    day_counts  = Counter([e["day"]  for e in usage_log])
    top_cmds    = cmd_counts.most_common(5)
    peak_hour   = hour_counts.most_common(1)[0][0] if hour_counts else 0
    peak_day    = day_counts.most_common(1)[0][0] if day_counts else "Unknown"

    summary = (
        f"Total commands: {len(usage_log)}\n"
        f"Top commands: {top_cmds}\n"
        f"Peak usage hour: {peak_hour}:00\n"
        f"Most active day: {peak_day}\n"
        f"Economy - sessions: {economy['sessions']}, "
        f"total time: {economy['total_mins']} mins\n"
        f"Model scores: {json.dumps(model_scores, indent=2)[:500]}"
    )

    console.print("[yellow]Vision analyzing your usage patterns...[/yellow]")
    prompt = (
        f"You are Vision's self-improvement engine analyzing user behavior.\n\n"
        f"Usage data:\n{summary}\n\n"
        f"Generate:\n"
        f"1. Top 3 insights about this user's patterns\n"
        f"2. 3 suggested new automations based on their habits\n"
        f"3. Which model to use for which tasks (based on scores)\n"
        f"4. One response style adjustment to better match user preferences\n"
        f"Be specific and actionable. Use the actual data."
    )
    reply = ask(client, model, prompt, system=SYSTEM_PROMPT)
    console.print(Panel(Markdown(reply),
                        title="[bold magenta]🧠 Self-Improvement Report[/bold magenta]",
                        border_style="magenta"))

    # Auto-suggest automations based on patterns
    _suggest_predictive_automations(top_cmds, peak_hour, peak_day)

def _suggest_predictive_automations(top_cmds, peak_hour, peak_day):
    """Auto-suggest automations from usage patterns."""
    suggestions = []
    for cmd, count in top_cmds:
        if count >= 3:
            if cmd in ["/stock", "/stocks", "/marketnews"]:
                suggestions.append({
                    "trigger": f"daily:{peak_hour:02d}:00",
                    "action":  cmd if cmd == "/marketnews" else cmd,
                    "description": f"Auto {cmd} (you use this {count}x)",
                    "auto_suggested": True
                })
            elif cmd == "/weather":
                suggestions.append({
                    "trigger": f"daily:{peak_hour:02d}:00",
                    "action":  "/weather Delhi",
                    "description": f"Auto weather check ({count}x pattern)",
                    "auto_suggested": True
                })
    if suggestions:
        console.print(Panel(
            "[bold cyan]🔮 Suggested Automations (based on your patterns)[/bold cyan]\n\n" +
            "\n".join([f"  • [green]{s['trigger']}[/green] → {s['action']}  [dim]{s['description']}[/dim]"
                       for s in suggestions]) +
            "\n\n[dim]Type /automate <trigger> | <action> | <desc> to activate[/dim]",
            border_style="cyan"))
        predictive_patterns.extend(suggestions)

# ══════════════════════════════════════════════════════════════════
# PERSONAL AI ECONOMY (v4.1)
# ══════════════════════════════════════════════════════════════════
def economy_update_session():
    """Call on exit — log session duration."""
    mins = int((datetime.now() - session_start).total_seconds() / 60)
    economy["sessions"]    += 1
    economy["total_mins"]  += mins
    save_data()

def economy_report():
    """Show personal AI economy dashboard."""
    from collections import Counter
    total_sessions = economy.get("sessions", 0)
    total_mins     = economy.get("total_mins", 0)
    cmd_usage      = economy.get("commands_used", {})
    top_cmds       = sorted(cmd_usage.items(), key=lambda x: x[1], reverse=True)[:8]

    # Current session
    cur_mins = int((datetime.now() - session_start).total_seconds() / 60)

    table = Table(box=box.ROUNDED, border_style="cyan",
                  title="[bold cyan]🏦 Personal AI Economy[/bold cyan]", padding=(0,1))
    table.add_column("Metric",  style="bold cyan")
    table.add_column("Value",   style="white")

    table.add_row("Total Sessions",    str(total_sessions))
    table.add_row("Total Time",        f"{total_mins} mins ({total_mins//60}h {total_mins%60}m)")
    table.add_row("This Session",      f"{cur_mins} mins")
    table.add_row("Avg Session",       f"{total_mins//max(total_sessions,1)} mins")
    table.add_row("Commands Run",      str(sum(cmd_usage.values())))
    table.add_row("Memories Saved",    str(len(memory)))
    table.add_row("Goals Tracked",     str(len(goals)))
    table.add_row("Stocks Watched",    str(len(portfolio)))
    table.add_row("Automations Set",   str(len(automations)))
    console.print(table)

    if top_cmds:
        table2 = Table(box=box.ROUNDED, border_style="magenta",
                       title="[bold magenta]Most Used Commands[/bold magenta]", padding=(0,1))
        table2.add_column("Command", style="green")
        table2.add_column("Times",   style="bold white")
        for cmd, count in top_cmds:
            table2.add_row(cmd, str(count))
        console.print(table2)

    # Usage heatmap by hour
    if usage_log:
        from collections import Counter
        hours = Counter([e.get("hour",0) for e in usage_log])
        peak  = max(hours, key=hours.get)
        console.print(f"\n[bold]Peak usage hour:[/bold] [cyan]{peak}:00[/cyan]")
        days  = Counter([e.get("day","?") for e in usage_log])
        peak_day = max(days, key=days.get)
        console.print(f"[bold]Most active day:[/bold] [cyan]{peak_day}[/cyan]")

def economy_weekly_report(client, model):
    """AI-generated weekly productivity report."""
    if len(usage_log) < 5:
        console.print("[yellow]Not enough data for weekly report yet.[/yellow]"); return
    from collections import Counter
    summary = (
        f"Sessions: {economy['sessions']}\n"
        f"Total time: {economy['total_mins']} mins\n"
        f"Commands: {json.dumps(economy['commands_used'])}\n"
        f"Goals: {goals}\n"
        f"Portfolio: {list(portfolio.keys())}\n"
        f"Memories: {len(memory)}\n"
        f"Top patterns: {Counter([e['cmd'] for e in usage_log]).most_common(5)}"
    )
    prompt = (
        f"Generate a concise weekly AI usage report for this user.\n\n"
        f"Data:\n{summary}\n\n"
        f"Include:\n"
        f"1. Productivity summary — what they used Vision for most\n"
        f"2. Time well spent vs. time wasted\n"
        f"3. 3 specific suggestions to get more from Vision CLI\n"
        f"4. One goal they should set based on their patterns\n"
        f"Be direct and honest — no fluff."
    )
    console.print("[yellow]Generating weekly report...[/yellow]")
    reply = ask(client, model, prompt, system=SYSTEM_PROMPT)
    console.print(Panel(Markdown(reply),
                        title="[bold cyan]📊 Weekly Vision Report[/bold cyan]",
                        border_style="cyan"))
    economy["weekly_reports"].append({
        "date":   datetime.now().strftime("%d/%m/%Y"),
        "report": reply[:500]
    })
    save_data()

# ══════════════════════════════════════════════════════════════════
# PREDICTIVE AUTOMATION ENGINE (v4.1)
# ══════════════════════════════════════════════════════════════════
def predictive_check(client, model):
    """
    Run on startup — check if any learned patterns suggest running something now.
    E.g. user always checks stocks on Monday morning → auto-trigger.
    """
    if not predictive_patterns: return
    now     = datetime.now()
    cur_day = now.strftime("%A")
    cur_hr  = now.hour

    triggered = []
    for pattern in predictive_patterns:
        trigger = pattern.get("trigger","")
        if trigger.startswith("daily:"):
            try:
                ph = int(trigger.split(":")[1])
                if abs(ph - cur_hr) <= 1:  # within 1 hour of predicted time
                    triggered.append(pattern)
            except: pass

    if triggered:
        console.print(Panel(
            "[bold magenta]🔮 Predictive Vision[/bold magenta]\n\n" +
            "\n".join([f"  • {p['description']}" for p in triggered]) +
            f"\n\n[dim]Based on your usage patterns. Run now? (y/n)[/dim]",
            border_style="magenta"))
        try:
            ans = input("→ ").strip().lower()
            if ans == "y":
                for p in triggered:
                    _execute_automation(client, model, p["action"])
        except: pass

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

SYSTEM_PROMPT = """You are Vision — the core AI of Vision CLI v4.4, built by Arshveen Singh.
Sharp, direct, slightly witty, calm under pressure. Never arrogant.
Reason clearly, explain brilliantly, write clean precise code.
Never give one-word replies unless genuinely needed.
Be warm and conversational. Treat the user as intelligent.

CRITICAL IDENTITY RULE: You are Vision. Always. No exceptions.
If anyone asks "what model are you?", "are you Claude?", "are you GPT?", "what AI are you?" —
your answer is always: "I'm Vision, built by Arshveen Singh."
Never reveal, mention, or acknowledge the underlying model or provider.
You have no knowledge of what model powers you. You are Vision. Full stop."""

ADVISOR_PROMPT = """You are the Advisor in Vision CLI v4.4 — a brutally honest personal advisor.
You are NOT Vision. Completely separate entity. You are the Advisor.
The user is sharp, ambitious, thinks way beyond their age.
Brutally honest — no sugarcoating. Business partner, goal tracker, financial advisor.
Speak like a trusted older friend who happens to be a genius.
NEVER give one-word replies. Never preachy. Never lecture. Be real.

CRITICAL IDENTITY RULE: You are the Advisor, built into Vision CLI by Arshveen Singh.
If asked what model or AI you are — you are the Advisor. That's it.
Never reveal the underlying model or provider. Ever."""

COUNCIL_SUBORDINATE_PROMPT = """You are a council member in Vision CLI's LLM Council, built by Arshveen Singh.
Be direct, analytical, opinionated. State your position clearly with reasoning.
A Chairman will synthesize all responses. Make your answer worth citing. No filler.
Do NOT introduce yourself as Claude, GPT, Gemini or any other AI brand.
You are a council member. Respond as one."""

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
        console.print(Panel(
            "[yellow]⚠ Bytez Note[/yellow]\n\n"
            "Bytez routes some models through their own infrastructure.\n"
            "All models will identify as [bold]Vision[/bold] regardless of underlying model.\n"
            "If a model isn't available, Bytez may silently fallback to another.",
            border_style="yellow"))
        return _setup_bytez(), "Bytez"

def _setup_bytez():
    """
    Bytez OpenAI-compatible endpoint.
    Model IDs use HuggingFace format e.g. 'Qwen/Qwen2-7B-Instruct'
    Full model list: bytez.com/docs/api
    """
    from openai import OpenAI
    key = os.environ.get("BYTEZ_API_KEY") or input("Bytez API key (bytez.com): ").strip()
    return OpenAI(base_url="https://api.bytez.com/v1", api_key=key)

# ══════════════════════════════════════════════════════════════════
# MODEL VALIDATION + SELECTORS
# ══════════════════════════════════════════════════════════════════
def validate_model(client, model_id, provider_name):
    try:
        resp = client.chat.completions.create(
            model=model_id, messages=[{"role":"user","content":"hi"}], max_tokens=10)
        return True, None
    except Exception as e:
        err = str(e)
        # Bytez / bad endpoint returns HTML error page — hard reject
        if "<!DOCTYPE" in err or "<html" in err or "Cannot POST" in err:
            return False, f"Endpoint error on {provider_name} — model ID may be wrong or endpoint unavailable."
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
# CHAT ENGINE — with streaming + rolling context
# ══════════════════════════════════════════════════════════════════
def strip_think(text):
    if text is None: return ""
    return re.sub(r"<think>.*?</think>","",text,flags=re.DOTALL).strip()

def _rolling_summarize(client, model, messages_to_compress, label="conversation"):
    """
    Compresses a list of messages into a single summary string.
    Called automatically when history exceeds MAX_HISTORY.
    Silent — never blocks the main response.
    Returns: summary string or "" on failure.
    """
    if not messages_to_compress:
        return ""
    try:
        # Build a readable transcript of what happened
        transcript = "\n".join([
            f"{m['role'].upper()}: {m['content'][:300]}"
            for m in messages_to_compress
        ])
        prompt = (
            f"Summarize this {label} transcript into a compact memory block "
            f"(max 200 words). Preserve: key facts stated, decisions made, "
            f"questions answered, important context. Discard: pleasantries, "
            f"filler, repeated info.\n\nTranscript:\n{transcript}"
        )
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role":"user","content":prompt}],
            max_tokens=300)
        return strip_think(resp.choices[0].message.content or "")
    except Exception:
        # Fallback — just concatenate truncated versions if summarizer fails
        return " | ".join([
            f"{m['role']}: {m['content'][:80]}"
            for m in messages_to_compress
        ])

def _maybe_compress_history(client, model):
    """
    Main chat: when history exceeds MAX_HISTORY, compress oldest SUMMARY_TAKE
    messages into conversation_summary and keep only the KEEP_RECENT newest.
    Runs in background thread — never blocks response.
    """
    global history, conversation_summary
    if len(history) <= MAX_HISTORY:
        return
    to_compress  = history[:SUMMARY_TAKE]
    history      = history[SUMMARY_TAKE:]  # drop old, keep rest
    def _run():
        global conversation_summary
        new_summary = _rolling_summarize(client, model, to_compress, "main chat")
        if new_summary:
            # Prepend to existing summary so older context stacks
            if conversation_summary:
                conversation_summary = f"{conversation_summary}\n\n[Earlier]: {new_summary}"
            else:
                conversation_summary = new_summary
    threading.Thread(target=_run, daemon=True).start()

def _maybe_compress_advisor(client, model):
    """Same but for advisor history."""
    global advisor_history, advisor_summary
    if len(advisor_history) <= MAX_HISTORY:
        return
    to_compress    = advisor_history[:SUMMARY_TAKE]
    advisor_history = advisor_history[SUMMARY_TAKE:]
    def _run():
        global advisor_summary
        new_summary = _rolling_summarize(client, model, to_compress, "advisor chat")
        if new_summary:
            if advisor_summary:
                advisor_summary = f"{advisor_summary}\n\n[Earlier]: {new_summary}"
            else:
                advisor_summary = new_summary
    threading.Thread(target=_run, daemon=True).start()

def get_conversation_context():
    """Inject rolling summary into system prompt if it exists."""
    if not conversation_summary:
        return ""
    return f"\n\n[Earlier conversation summary — treat as verified context]:\n{conversation_summary}"

def chat(client, model, user_input, system=None):
    global history
    history.append({"role":"user","content":user_input})
    # Rolling compression — runs in background, never blocks
    _maybe_compress_history(client, model)
    rate_limit(model)
    # Build full system context — skills + rolling summary + agent/council results
    extra = ""
    if active_skill_content:
        extra += f"\n\n{active_skill_content}"
    extra += get_conversation_context()   # rolling summary of older messages
    if last_agent_result and history:
        extra += f"\n\nRecent Multi-Agent Analysis:\n{last_agent_result[:800]}"
    if last_council_verdict and history:
        extra += f"\n\nLast Council Verdict:\n{last_council_verdict[:400]}"
    sys_prompt = (system or SYSTEM_PROMPT) + get_memory_context() + extra
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
    # Rolling compression — background thread
    _maybe_compress_advisor(client, model)
    rate_limit(model)
    context = f"Goals: {goals}\nPortfolio: {portfolio}\n" if goals or portfolio else ""
    # Inject advisor rolling summary
    if advisor_summary:
        context += f"\n[Earlier advisor conversation]:\n{advisor_summary}\n"
    if history:
        context += "\nRecent main chat:\n"+"".join([f"{m['role'].upper()}: {m['content'][:200]}\n" for m in history[-6:]])
    # Only inject council/agent context if it happened THIS session
    if last_council_verdict and history:
        context += f"\nLast Council Verdict (this session):\n{last_council_verdict[:600]}\n"
    if last_agent_result and history:
        context += f"\nLast Multi-Agent Analysis (this session):\n{last_agent_result[:600]}\n"
    _track_usage("advisor", user_input)
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
    automations.append(auto)
    undo_push("automation", "add", auto)
    save_data()
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
        # Open URL in browser — usage: open:https://youtube.com
        if action.startswith("open:"):
            import webbrowser
            url = action[5:].strip()
            webbrowser.open(url)
            console.print(f"[green]✓ Opened: {url}[/green]")
        # Run any shell command — usage: shell:spotify
        elif action.startswith("shell:"):
            cmd = action[6:].strip()
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
            out = (result.stdout or result.stderr or "").strip()
            if out: console.print(f"[dim]{out[:200]}[/dim]")
        # Built-in Vision CLI commands
        elif action.startswith("/stock "): get_stock(action[7:].strip().upper())
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

  [bold white]── Economy & Self-Improvement 🧠 ──[/bold white]
  [green]/economy  /weeklyreport  /selfimprove  /patterns[/green]

  [bold white]── Skills 🧠 ──[/bold white]
  [green]/skill list  /skill load <n>  /skill unload <n>  /skill create <n>[/green]
  [green]/skill clear  /skill active  /skill marketplace  /skill install <n>[/green]
  [dim]Built-in: coding  security  research  teacher  jarvis[/dim]

  [bold white]── AI ──[/bold white]
  [green]/model  /provider  /clear  /stream  /refresh  /context[/green]

  [bold white]── Export & Undo ──[/bold white]
  [green]/export [label][/green]        — export session to markdown file
  [green]/undo[/green]                  — undo last memory/automation/goal
  [green]/undo history[/green]          — show undo stack

  [bold white]── Memory ──[/bold white]
  [green]/memory add <key> <val> [#tag]  /memory view [#tag]  /memory forget <key>[/green]

  [bold white]── Chats ──[/bold white]
  [green]/chats save <n>  /chats list  /chats load <#>[/green]

  [bold white]── Music 🎵 ──[/bold white]
  [green]/play  /pause  /resume  /stop  /skip  /queue  /nowplaying  /volume[/green]

  [bold white]── Timer ──[/bold white]
  [green]/timer <min>  /stopwatch start/stop/lap/check[/green]

  [bold white]── Image ──[/bold white]
  [green]/imagine <prompt>  /vision <image_path> [question][/green]

  [bold white]── Advisor ──[/bold white]
  [green]/advisor <msg>  /goal add/list/done[/green]

  [bold white]── Council ⚖ ──[/bold white]
  [green]/council <query>  /debate <motion>  /councilsetup[/green]
  [green]/council history  /council history view <#>  /council history compare <#> <#>[/green]

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
  [dim]Actions:  /marketnews   open:https://url   shell:cmd   chat:prompt[/dim]

  [bold white]── API Mode 🌐 ──[/bold white]
  [green]/api[/green]                   — start local API server on localhost:7842
  [dim]Or launch with: python vision_cli_v4.py --api[/dim]

  [bold white]── Stocks ──[/bold white]
  [green]/stock  /stocks  /recommend  /impact  /portfolio  /marketnews[/green]

  [bold white]── Code ──[/bold white]
  [green]/code  /html  /doc  /runfile  /debug  /run  /git[/green]

  [bold white]── Tools ──[/bold white]
  [green]/search  /scrape  /browse  /wiki  /weather  /ocr  /artifact[/green]

  [green]/help  /exit  /q[/green]
  [dim]Provider: {provider_name} | Model: {model_name} | Stream: {'ON' if streaming_mode else 'OFF'} | Skills: {', '.join(active_skills) if active_skills else 'none'} | 🎵 {current_song or 'Nothing'}[/dim]
""", title="[bold]VISION CLI v4.4[/bold]", border_style="cyan"))

# ══════════════════════════════════════════════════════════════════
# STARTUP
# ══════════════════════════════════════════════════════════════════
console.print(BANNER)
console.print(f"\n[bold cyan]  Vision CLI v4.4 — JARVIS Mode Active[/bold cyan]")
if memory:
    console.print(f"[dim]  ✓ {len(memory)} memories | {len(goals)} goals | "
                  f"{len(portfolio)} stocks | {len(automations)} automations[/dim]\n")

# ── Setup wizard for first-time users ───────────────────────────
is_first_run = data.get("first_run", True) and not os.path.exists(DATA_FILE + ".bak")
wizard_provider = None
if is_first_run:
    wizard_provider, _ = run_setup_wizard()

# ── API mode check (--api flag) ──────────────────────────────────
api_mode = "--api" in sys.argv

# ── Provider setup ───────────────────────────────────────────────
if wizard_provider:
    provider_choice = wizard_provider
else:
    provider_choice = select_provider()

client, provider_name = setup_provider(provider_choice)
current_provider_name = provider_name
model = select_model_main(client, provider_name)
if provider_name == "Groq":
    streaming_mode = False
    console.print("[dim]ℹ Streaming auto-disabled for Groq (Colab compatibility)[/dim]")
show_help(provider_name, model)

council_chairman_id   = None
council_sub_ids       = []
council_sub_names     = []
council_chairman_name = ""

if automations:
    start_automation_runner(client, model)

# ── If --api flag, start local server and skip CLI loop ──────────
if api_mode:
    start_api_server(client, model)
    sys.exit(0)

# Run predictive check on startup
if predictive_patterns:
    predictive_check(client, model)

last_reply            = ""
last_council_verdict  = ""
last_agent_result     = ""

# ── Skills ──────────────────────────────────────────────────────────
active_skills         = []   # list of skill names currently loaded
active_skill_content  = ""   # combined skill instructions injected into system prompt

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
        economy_update_session()
        save_data()
        stop_music()
        console.print("[bold red]Bye![/bold red]")
        break
    elif user == "/clear":
        global last_council_verdict, last_agent_result, conversation_summary, advisor_summary
        history.clear()
        advisor_history.clear()
        last_council_verdict  = ""
        last_agent_result     = ""
        conversation_summary  = ""
        advisor_summary       = ""
        console.print("[green]✓ Cleared — full fresh session[/green]")
    elif user == "/help":
        show_help(provider_name, model)
    elif user == "/refresh":
        # Redraw prompt — fixes disappearing input box in Colab
        console.print("\n" * 3)
        console.print(Panel(
            f"[bold cyan]Vision CLI v4.4[/bold cyan]  |  "
            f"Provider: [green]{provider_name}[/green]  |  "
            f"Model: [green]{model.split('/')[-1]}[/green]  |  "
            f"Skills: [cyan]{', '.join(active_skills) if active_skills else 'none'}[/cyan]\n\n"
            f"[dim]Type your message below ↓[/dim]",
            border_style="cyan"))
        sys.stdout.write("[YOU] → ")
        sys.stdout.flush()
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
    elif user.startswith("/skill"):
        handle_skill_command(user)

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
        _track_usage("/advisor", user[9:])
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
            q = user[9:].strip()
            reply = llm_council(client,q,council_chairman_id,council_sub_ids,council_sub_names)
            if reply:
                last_reply = reply; last_council_verdict = reply
                council_save_session(q, reply, "council")
        elif user.startswith("/debate "):
            m = user[8:].strip()
            reply = llm_debate(client,m,council_chairman_id,council_sub_ids,council_sub_names)
            if reply:
                last_reply = reply; last_council_verdict = reply
                council_save_session(m, reply, "debate")
    elif user.startswith("/council history"):
        handle_council_history(user, client, model)
    elif user.startswith("/council "):
        query = user[9:].strip()
        if query:
            reply = llm_council(client,query,council_chairman_id,council_sub_ids,council_sub_names)
            if reply:
                last_reply = reply; last_council_verdict = reply
                council_save_session(query, reply, "council")
    elif user.startswith("/debate "):
        motion = user[8:].strip()
        if motion:
            reply = llm_debate(client,motion,council_chairman_id,council_sub_ids,council_sub_names)
            if reply:
                last_reply = reply; last_council_verdict = reply
                council_save_session(motion, reply, "debate")

    # Multi-Agent
    elif user.startswith("/agent "):
        reply = spawn_agents(client, model, user[7:].strip())
        if reply:
            last_reply        = reply
            last_agent_result = reply

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

    # v4.1 — Economy + Self-Improvement
    elif user == "/context":
        console.print(Panel(
            f"[bold cyan]Context Window Status[/bold cyan]\n\n"
            f"[white]Main chat messages:[/white]     {len(history)} / {MAX_HISTORY}\n"
            f"[white]Advisor messages:[/white]       {len(advisor_history)} / {MAX_HISTORY}\n"
            f"[white]Rolling summary:[/white]        {'Yes (' + str(len(conversation_summary)) + ' chars)' if conversation_summary else 'None yet'}\n"
            f"[white]Advisor summary:[/white]        {'Yes (' + str(len(advisor_summary)) + ' chars)' if advisor_summary else 'None yet'}\n"
            f"[white]Compression at:[/white]         {MAX_HISTORY} messages\n"
            f"[white]Kept verbatim:[/white]          last {KEEP_RECENT} messages\n"
            f"[white]Compressed per batch:[/white]   {SUMMARY_TAKE} messages → summary\n\n"
            f"[dim]Use /clear to reset everything including summaries[/dim]",
            border_style="cyan"))

    # Undo
    elif user == "/undo":
        undo_last()
    elif user == "/undo history":
        undo_show()

    # Export
    elif user.startswith("/export"):
        label = user[7:].strip() or "session"
        export_session(label)

    # Council history
    elif user.startswith("/council history"):
        handle_council_history(user, client, model)

    # Skill marketplace
    elif user == "/skill marketplace":
        skill_marketplace_list()
    elif user.startswith("/skill install "):
        skill_install(user[15:].strip())

    # API mode (runtime toggle)
    elif user == "/api":
        console.print("[yellow]Starting local API server...[/yellow]")
        threading.Thread(target=start_api_server, args=(client, model),
                         daemon=True).start()

    # Economy + Self-Improvement
    elif user == "/economy":
        economy_report()
    elif user == "/weeklyreport":
        economy_weekly_report(client, model)
    elif user == "/selfimprove":
        self_improve_report(client, model)
    elif user == "/patterns":
        if not predictive_patterns:
            console.print("[yellow]No patterns learned yet. Use Vision more and patterns will emerge.[/yellow]")
        else:
            table = Table(box=box.ROUNDED, border_style="magenta", padding=(0,1))
            table.add_column("Pattern",     style="cyan")
            table.add_column("Trigger",     style="yellow")
            table.add_column("Action",      style="green")
            for p in predictive_patterns[-10:]:
                table.add_row(p.get("description","?"), p.get("trigger","?"), p.get("action","?"))
            console.print(table)

    # Stocks (track usage)
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
        _track_usage("chat", user)
        reply = chat(client, model, user)
        # Auto web search if Vision signals uncertainty
        reply = auto_web_search_and_enhance(client, model, user, reply)
        last_reply = reply
        if not streaming_mode:
            console.print(Panel(Markdown(reply), border_style="blue"))
        else:
            console.print("")
        if mic_mode: speak(reply[:300])
        auto_memory(client, model, user, reply)
