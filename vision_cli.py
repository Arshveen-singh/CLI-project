import warnings
warnings.filterwarnings("ignore")

import os, re, subprocess, requests, wikipedia, asyncio
import json, time, sys, threading
from datetime import datetime
from pathlib import Path
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich import box
from ddgs import DDGS
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
import easyocr
import yfinance as yf

console = Console()

# ── Persistent Storage ─────────────────────────────────────────────
DATA_FILE = "vision_data.json"
CHATS_DIR = "vision_chats"
MUSIC_DIR = "vision_music"
Path(CHATS_DIR).mkdir(exist_ok=True)
Path(MUSIC_DIR).mkdir(exist_ok=True)

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"memory": {}, "goals": [], "portfolio": {}, "advisor_history": [], "created": datetime.now().strftime("%d/%m/%Y")}

def save_data():
    data["advisor_history"] = advisor_history[-20:]
    data["goals"] = goals
    data["portfolio"] = portfolio
    data["memory"] = memory
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

data = load_data()
memory = data["memory"]
goals = data["goals"]
portfolio = data["portfolio"]
advisor_history = data.get("advisor_history", [])
history = []
mic_mode = False
last_request_time = 0

# ── Rate Limiting ──────────────────────────────────────────────────
MODEL_LIMITS = {
    "moonshotai/kimi-k2-instruct-0905": 3,
    "qwen/qwen3-32b": 2,
    "llama-3.3-70b-versatile": 2,
}

def rate_limit(model):
    global last_request_time
    interval = MODEL_LIMITS.get(model, 2)
    elapsed = time.time() - last_request_time
    if elapsed < interval:
        wait = interval - elapsed
        console.print(f"[yellow]⏳ {wait:.1f}s...[/yellow]", end="\r")
        time.sleep(wait)
    last_request_time = time.time()

# ── Music Player ───────────────────────────────────────────────────
music_queue = []
current_song = None
music_thread = None
music_playing = False

def download_and_play(query):
    global current_song, music_playing
    try:
        import yt_dlp
        import pygame

        console.print(f"[yellow]🎵 Searching: {query}...[/yellow]")

        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': f'{MUSIC_DIR}/%(title)s.%(ext)s',
            'quiet': True,
            'no_warnings': True,
            'default_search': 'ytsearch1',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch1:{query}", download=True)
            if 'entries' in info:
                info = info['entries'][0]
            title = info.get('title', query)
            duration = info.get('duration', 0)
            mins, secs = divmod(int(duration), 60)

        # Find downloaded file
        files = list(Path(MUSIC_DIR).glob("*.mp3"))
        if not files:
            console.print("[red]Download failed.[/red]")
            return

        latest = max(files, key=os.path.getctime)
        current_song = title

        console.print(Panel(
            f"[bold cyan]🎵 Now Playing[/bold cyan]\n\n"
            f"[white]{title}[/white]\n"
            f"[dim]Duration: {mins:02d}:{secs:02d}[/dim]\n\n"
            f"[dim]/pause  /resume  /stop  /skip  /nowplaying[/dim]",
            border_style="cyan"
        ))

        pygame.mixer.init()
        pygame.mixer.music.load(str(latest))
        pygame.mixer.music.play()
        music_playing = True

        while pygame.mixer.music.get_busy() and music_playing:
            time.sleep(1)

        music_playing = False
        current_song = None

        # Play next in queue if exists
        if music_queue:
            next_song = music_queue.pop(0)
            play_music(next_song)

    except Exception as e:
        console.print(f"[red]Music error: {e}[/red]")
        music_playing = False

def play_music(query):
    global music_thread
    music_thread = threading.Thread(target=download_and_play, args=(query,), daemon=True)
    music_thread.start()

def pause_music():
    try:
        import pygame
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.pause()
            console.print("[yellow]⏸ Paused[/yellow]")
        else:
            console.print("[red]Nothing playing.[/red]")
    except: console.print("[red]Music not initialized.[/red]")

def resume_music():
    try:
        import pygame
        pygame.mixer.music.unpause()
        console.print("[green]▶ Resumed[/green]")
    except: console.print("[red]Music not initialized.[/red]")

def stop_music():
    global music_playing, current_song
    try:
        import pygame
        pygame.mixer.music.stop()
        music_playing = False
        current_song = None
        music_queue.clear()
        console.print("[red]⏹ Stopped[/red]")
    except: console.print("[red]Music not initialized.[/red]")

def skip_music():
    global music_playing
    try:
        import pygame
        pygame.mixer.music.stop()
        music_playing = False
        console.print("[cyan]⏭ Skipped[/cyan]")
        if music_queue:
            next_song = music_queue.pop(0)
            play_music(next_song)
    except: console.print("[red]Music not initialized.[/red]")

def queue_music(query):
    music_queue.append(query)
    console.print(f"[green]✓ Queued: {query} (#{len(music_queue)} in queue)[/green]")

def show_queue():
    if not music_queue and not current_song:
        console.print("[yellow]Queue empty.[/yellow]")
        return
    if current_song:
        console.print(f"[bold cyan]🎵 Now:[/bold cyan] {current_song}")
    if music_queue:
        table = Table(box=box.ROUNDED, border_style="cyan", padding=(0,1))
        table.add_column("#", style="bold cyan")
        table.add_column("Song", style="white")
        for i, s in enumerate(music_queue, 1):
            table.add_row(str(i), s)
        console.print(table)

def set_volume(vol):
    try:
        import pygame
        v = float(vol) / 100
        pygame.mixer.music.set_volume(max(0, min(1, v)))
        console.print(f"[green]🔊 Volume: {vol}%[/green]")
    except: console.print("[red]Error setting volume.[/red]")

# ── Memory ─────────────────────────────────────────────────────────
def get_memory_context():
    if not memory:
        return ""
    facts = "\n".join([f"- {k}: {v['value']}" for k, v in memory.items()])
    return f"\n\nUser memory:\n{facts}"

def memory_add(key, value):
    memory[key] = {"value": value, "added": datetime.now().strftime("%d/%m/%Y %H:%M")}
    save_data()
    console.print(f"[green]✓ Memory: {key} → {value}[/green]")

def memory_view():
    if not memory:
        console.print("[yellow]No memories.[/yellow]")
        return
    table = Table(box=box.ROUNDED, border_style="cyan", padding=(0,1))
    table.add_column("Key", style="bold cyan")
    table.add_column("Value", style="white")
    table.add_column("Added", style="dim")
    for k, v in memory.items():
        table.add_row(k, v["value"], v["added"])
    console.print(table)

def memory_forget(key):
    if key in memory:
        del memory[key]
        save_data()
        console.print(f"[green]✓ Forgot: {key}[/green]")
    else:
        console.print(f"[red]Not found: {key}[/red]")

# ── Chat Library ───────────────────────────────────────────────────
def save_chat(name):
    if not history:
        console.print("[red]No chat to save.[/red]")
        return
    filename = f"{CHATS_DIR}/{name.replace(' ','_')}_{datetime.now().strftime('%d%m%Y_%H%M')}.json"
    with open(filename, "w") as f:
        json.dump({"name": name, "date": datetime.now().strftime("%d/%m/%Y %H:%M"), "messages": history}, f, indent=2)
    console.print(f"[green]✓ Saved: '{filename}'[/green]")

def list_chats():
    files = sorted(Path(CHATS_DIR).glob("*.json"))
    if not files:
        console.print("[yellow]No saved chats.[/yellow]")
        return
    table = Table(box=box.ROUNDED, border_style="cyan", padding=(0,1))
    table.add_column("#", style="bold cyan")
    table.add_column("Name", style="white")
    table.add_column("Date", style="dim")
    table.add_column("Messages", style="white")
    for i, f in enumerate(files, 1):
        d = json.load(open(f))
        table.add_row(str(i), d.get("name", f.stem), d.get("date","N/A"), str(len(d.get("messages",[]))))
    console.print(table)

def load_chat(index):
    global history
    files = sorted(Path(CHATS_DIR).glob("*.json"))
    try:
        d = json.load(open(files[int(index)-1]))
        history = d["messages"]
        console.print(f"[green]✓ Loaded: {d['name']} ({len(history)} messages)[/green]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

# ── Timer ──────────────────────────────────────────────────────────
stopwatch_start = None
stopwatch_running = False
lap_times = []

def study_timer(minutes):
    secs = int(float(minutes) * 60)
    console.print(f"[bold cyan]⏱ {minutes} min timer[/bold cyan]")
    try:
        for remaining in range(secs, 0, -1):
            m, s = divmod(remaining, 60)
            console.print(f"\r[cyan]⏱ {m:02d}:{s:02d}[/cyan]", end="")
            time.sleep(1)
        console.print("\n[bold green]✓ DONE! 🎉[/bold green]")
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopped.[/yellow]")

def stopwatch_cmd(action):
    global stopwatch_start, stopwatch_running, lap_times
    if action == "start":
        stopwatch_start = time.time()
        stopwatch_running = True
        lap_times = []
        console.print("[green]✓ Started[/green]")
    elif action == "stop":
        if stopwatch_running:
            elapsed = time.time() - stopwatch_start
            stopwatch_running = False
            m, s = divmod(int(elapsed), 60)
            console.print(f"[bold green]{m:02d}:{s:02d}[/bold green]")
    elif action == "lap":
        if stopwatch_running:
            elapsed = time.time() - stopwatch_start
            lap_times.append(elapsed)
            m, s = divmod(int(elapsed), 60)
            console.print(f"[cyan]Lap {len(lap_times)}: {m:02d}:{s:02d}[/cyan]")
    elif action == "check":
        if stopwatch_running:
            elapsed = time.time() - stopwatch_start
            m, s = divmod(int(elapsed), 60)
            console.print(f"[cyan]⏱ {m:02d}:{s:02d}[/cyan]")

# ── Image Gen ──────────────────────────────────────────────────────
def generate_image(prompt):
    filename = f"vision_img_{datetime.now().strftime('%H%M%S')}.jpg"
    console.print("[yellow]Trying Pollinations.ai...[/yellow]")
    try:
        url = f"https://image.pollinations.ai/prompt/{prompt.replace(' ','%20')}?width=512&height=512&nologo=true"
        r = requests.get(url, timeout=30)
        if r.status_code == 200 and "image" in r.headers.get("content-type",""):
            with open(filename, "wb") as f:
                f.write(r.content)
            console.print(f"[green]✓ Saved: '{filename}'[/green]")
            try:
                from IPython.display import display, Image as IPImage
                display(IPImage(filename))
            except: pass
            return
    except:
        console.print("[yellow]Pollinations failed → HuggingFace...[/yellow]")
    try:
        token = os.environ.get("HF_TOKEN") or input("HuggingFace token: ").strip()
        r = requests.post(
            "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-2-1",
            headers={"Authorization": f"Bearer {token}"},
            json={"inputs": prompt}, timeout=60
        )
        if r.status_code == 200:
            with open(filename, "wb") as f: f.write(r.content)
            console.print(f"[green]✓ Saved: '{filename}'[/green]")
            try:
                from IPython.display import display, Image as IPImage
                display(IPImage(filename))
            except: pass
        else:
            console.print(f"[red]{r.text[:200]}[/red]")
    except Exception as e:
        console.print(f"[red]{e}[/red]")

# ── TTS + Voice ────────────────────────────────────────────────────
def speak(text):
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty('rate', 175)
        engine.say(text[:300])
        engine.runAndWait()
    except: pass

def listen():
    try:
        import speech_recognition as sr
        r = sr.Recognizer()
        with sr.Microphone() as source:
            console.print("[cyan]🎤 Listening...[/cyan]")
            audio = r.listen(source, timeout=5)
        text = r.recognize_google(audio)
        console.print(f"[cyan]You said: {text}[/cyan]")
        return text
    except Exception as e:
        console.print(f"[red]Mic error: {e}[/red]")
        return None

# ── Prompts ────────────────────────────────────────────────────────
BANNER = r"""[bold cyan]
____   ____.__       .__                _________ .____    .___
\   \ /   /|__| _____|__| ____   ____   \_   ___ \|    |   |   |
 \   Y   / |  |/  ___/  |/  _ \ /    \  /    \  \/|    |   |   |
  \     /  |  |\___ \|  (  <_> )   |  \ \     \___|    |___|   |
   \___/   |__/____  >__|\____/|___|  /  \______  /_______ \___|
                   \/               \/          \/        \/
[/bold cyan]"""

SYSTEM_PROMPT = """You are an elite AI assistant — sharp, direct, and deeply helpful.
Your personality: confident but never arrogant, slightly witty, calm under pressure.
You reason clearly, explain brilliantly, and write clean precise code.
You never give one-word or one-line replies unless the question genuinely needs it.
Be warm, engaged and conversational — you're talking to a person, not closing a ticket.
Never waffle. Treat the user as intelligent.
When coding: write clean, commented, production-quality code only.
When making artifacts: output ONLY the raw content."""

ADVISOR_PROMPT = """You are user's personal advisor, business partner, and trusted confidant.
You know him well he is Sharp, ambitious, thinks way beyond his age.

Your role:
- Brutally honest advisor — no sugarcoating, no fluff
- Business partner — evaluate ideas critically
- Goal tracker — remember and follow up on goals
- Venting buddy — listen, validate, redirect constructively
- Financial advisor — real stock advice for young Indian investor
- Long term thinker — career, business, money, life
- Challenge bad ideas, celebrate good ones
- Speak casually like a trusted older friend who happens to be a genius
- NEVER give one-word replies. Always be warm and engaged.

Never be preachy. Never lecture. Be real."""

GROQ_MODELS = {
    "1": ("moonshotai/kimi-k2-instruct-0905", "Kimi K2        — Best for reasoning & chat"),
    "2": ("qwen/qwen3-32b",                   "Qwen 3 32B     — Best for coding"),
    "3": ("llama-3.3-70b-versatile",           "LLaMA 3.3 70B  — Best for general tasks"),
}
OPENROUTER_MODELS = {
    "1": ("anthropic/claude-3.5-sonnet",       "Claude 3.5 Sonnet — Best overall"),
    "2": ("google/gemini-flash-1.5",           "Gemini Flash      — Fast & smart"),
    "3": ("meta-llama/llama-3.3-70b-instruct", "LLaMA 3.3 70B     — Open source"),
    "4": ("deepseek/deepseek-r1",              "DeepSeek R1       — Reasoning beast"),
}
OLLAMA_MODELS = {
    "1": ("llama3.2",  "LLaMA 3.2   — General"),
    "2": ("qwen2.5",   "Qwen 2.5    — Coding"),
    "3": ("mistral",   "Mistral     — Fast"),
    "4": ("custom",    "Custom      — Enter name"),
}
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

# ── Provider ───────────────────────────────────────────────────────
def select_provider():
    console.print(Panel("[bold cyan]Select AI Provider[/bold cyan]", border_style="cyan"))
    console.print("  [green][1][/green] Groq          — Free, ultra fast")
    console.print("  [green][2][/green] OpenRouter    — Access any model")
    console.print("  [green][3][/green] Ollama        — 100% local")
    while True:
        choice = input("\n→ (1-3): ").strip()
        if choice in ["1","2","3"]: return choice
        console.print("[red]Invalid.[/red]")

def setup_provider(provider):
    if provider == "1":
        from groq import Groq
        key = os.environ.get("GROQ_API_KEY") or input("Groq API key: ").strip()
        return Groq(api_key=key), "Groq", GROQ_MODELS
    elif provider == "2":
        from openai import OpenAI
        key = os.environ.get("OPENROUTER_API_KEY") or input("OpenRouter key: ").strip()
        return OpenAI(base_url="https://openrouter.ai/api/v1", api_key=key), "OpenRouter", OPENROUTER_MODELS
    elif provider == "3":
        from openai import OpenAI
        host = input("Ollama host (Enter=localhost): ").strip() or "http://localhost:11434"
        return OpenAI(base_url=f"{host}/v1", api_key="ollama"), "Ollama", OLLAMA_MODELS

def select_model(models):
    console.print(Panel("[bold cyan]Select Model[/bold cyan]", border_style="cyan"))
    for k, (_, desc) in models.items():
        console.print(f"  [green][{k}][/green] {desc}")
    while True:
        choice = input(f"\n→ (1-{len(models)}): ").strip()
        if choice in models:
            mid, desc = models[choice]
            if mid == "custom": mid = input("Model name: ").strip()
            console.print(f"\n[green]✓ {desc.split('—')[0].strip()}[/green]\n")
            return mid
        console.print("[red]Invalid.[/red]")

# ── Chat ───────────────────────────────────────────────────────────
def strip_think(text):
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

def chat(client, model, user_input, system=None):
    global history
    history.append({"role": "user", "content": user_input})
    if len(history) > 20: history = history[-20:]
    rate_limit(model)
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": (system or SYSTEM_PROMPT) + get_memory_context()}, *history],
            max_tokens=2048,
        )
        reply = strip_think(response.choices[0].message.content)
        history.append({"role": "assistant", "content": reply})
        return reply
    except Exception as e:
        return f"Error: {e}"

def advisor_chat(client, model, user_input):
    global advisor_history
    advisor_history.append({"role": "user", "content": user_input})
    if len(advisor_history) > 20: advisor_history = advisor_history[-20:]
    rate_limit(model)
    context = f"Goals: {goals}\nPortfolio: {portfolio}\n" if goals or portfolio else ""
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": ADVISOR_PROMPT + f"\n\n{context}" + get_memory_context()}, *advisor_history],
            max_tokens=2048,
        )
        reply = strip_think(response.choices[0].message.content)
        advisor_history.append({"role": "assistant", "content": reply})
        save_data()
        return reply
    except Exception as e:
        return f"Error: {e}"

def ask(client, model, prompt, system=None):
    rate_limit(model)
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": system or SYSTEM_PROMPT}, {"role": "user", "content": prompt}],
            max_tokens=2048,
        )
        return strip_think(response.choices[0].message.content)
    except Exception as e:
        return f"Error: {e}"

# ── Stocks ─────────────────────────────────────────────────────────
def get_stock(symbol):
    try:
        for suffix in [".NS", ".BO", ""]:
            ticker = yf.Ticker(symbol + suffix)
            info = ticker.info
            price = info.get("currentPrice") or info.get("regularMarketPrice")
            if price:
                prev = info.get("previousClose", price)
                change = price - prev
                pct = (change/prev*100) if prev else 0
                color = "green" if change >= 0 else "red"
                arrow = "▲" if change >= 0 else "▼"
                currency = "₹" if suffix in [".NS",".BO"] else "$"
                table = Table(box=box.ROUNDED, border_style="cyan", show_header=False, padding=(0,1))
                table.add_column("Key", style="bold cyan", no_wrap=True)
                table.add_column("Value", style="white")
                table.add_row("Stock", f"[bold]{info.get('longName', symbol)}[/bold]")
                table.add_row("Price", f"[bold {color}]{currency}{price:.2f} {arrow} ({pct:+.2f}%)[/bold {color}]")
                table.add_row("52W High", f"{currency}{info.get('fiftyTwoWeekHigh','N/A')}")
                table.add_row("52W Low", f"{currency}{info.get('fiftyTwoWeekLow','N/A')}")
                table.add_row("Mkt Cap", f"{currency}{info.get('marketCap',0)/1e9:.2f}B" if info.get("marketCap") else "N/A")
                table.add_row("P/E", str(round(info.get("trailingPE",0),2)) if info.get("trailingPE") else "N/A")
                table.add_row("Volume", f"{info.get('volume',0):,}")
                table.add_row("Sector", info.get("sector","N/A"))
                console.print(table)
                return
        console.print(f"[red]'{symbol}' not found.[/red]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

def search_stocks(query):
    q = query.lower()
    if q in INDIAN_SECTORS:
        table = Table(box=box.ROUNDED, border_style="cyan", padding=(0,1), title=f"[bold cyan]{q.upper()}[/bold cyan]")
        table.add_column("Symbol", style="bold green")
        table.add_column("Price", style="white")
        table.add_column("Change", style="white")
        for sym in INDIAN_SECTORS[q]:
            try:
                info = yf.Ticker(sym+".NS").info
                price = info.get("currentPrice") or info.get("regularMarketPrice", 0)
                prev = info.get("previousClose", price)
                pct = ((price-prev)/prev*100) if prev else 0
                color = "green" if pct >= 0 else "red"
                table.add_row(sym, f"₹{price:.2f}", f"[{color}]{'▲' if pct>=0 else '▼'} {pct:+.2f}%[/{color}]")
            except:
                table.add_row(sym, "N/A", "N/A")
        console.print(table)
    else:
        console.print(f"[yellow]Sectors: {', '.join(INDIAN_SECTORS.keys())}[/yellow]")

def stock_recommend(client, model, query):
    console.print("[yellow]Analyzing...[/yellow]")
    reply = ask(client, model, f"Indian/global stock advisor. Query: {query}\nGive specific picks with thesis, risk, time horizon.")
    console.print(Panel(Markdown(reply), title="[bold]Recommendations[/bold]", border_style="cyan"))

def war_impact(client, model, event):
    console.print("[yellow]Analyzing...[/yellow]")
    reply = ask(client, model, f"How does '{event}' impact Indian AND global stocks? Give sectors, NSE/NYSE symbols, commodities, currency impact.")
    console.print(Panel(Markdown(reply), title="[bold]Market Impact[/bold]", border_style="red"))

def portfolio_add(symbol, qty, buy_price):
    portfolio[symbol.upper()] = {"qty": float(qty), "buy_price": float(buy_price)}
    save_data()
    console.print(f"[green]✓ {qty}x {symbol.upper()} @ ₹{buy_price}[/green]")

def portfolio_view():
    if not portfolio:
        console.print("[yellow]Portfolio empty.[/yellow]")
        return
    table = Table(box=box.ROUNDED, border_style="cyan", padding=(0,1))
    table.add_column("Symbol", style="bold green")
    table.add_column("Qty")
    table.add_column("Buy")
    table.add_column("Current")
    table.add_column("P&L")
    table.add_column("P&L %")
    total_inv = total_cur = 0
    for sym, d in portfolio.items():
        try:
            info = yf.Ticker(sym+".NS").info
            cur = info.get("currentPrice") or info.get("regularMarketPrice", d["buy_price"])
            inv = d["qty"] * d["buy_price"]
            cv = d["qty"] * cur
            pnl = cv - inv
            pct = (pnl/inv*100) if inv else 0
            color = "green" if pnl>=0 else "red"
            table.add_row(sym, str(d["qty"]), f"₹{d['buy_price']:.2f}", f"₹{cur:.2f}", f"[{color}]₹{pnl:+.2f}[/{color}]", f"[{color}]{pct:+.2f}%[/{color}]")
            total_inv += inv; total_cur += cv
        except:
            table.add_row(sym, str(d["qty"]), f"₹{d['buy_price']:.2f}", "N/A", "N/A", "N/A")
    console.print(table)
    pnl = total_cur - total_inv
    pct = (pnl/total_inv*100) if total_inv else 0
    color = "green" if pnl>=0 else "red"
    console.print(f"[bold]Invested:[/bold] ₹{total_inv:.2f}  [bold {color}]P&L: ₹{pnl:+.2f} ({pct:+.2f}%)[/bold {color}]")

def market_news(query="indian stock market"):
    results = []
    with DDGS() as ddgs:
        for r in ddgs.text(f"{query} today", max_results=5):
            results.append(f"**{r['title']}**\n{r['body']}\n{r['href']}")
    console.print(Markdown("\n\n".join(results)))

# ── Tools ──────────────────────────────────────────────────────────
def search(query):
    results = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=4):
            results.append(f"**{r['title']}**\n{r['body']}\n{r['href']}")
    return "\n\n".join(results)

def scrape(url):
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        for tag in soup(["script","style","nav","footer"]): tag.decompose()
        return soup.get_text(separator="\n", strip=True)[:3000]
    except Exception as e:
        return f"Error: {e}"

def wiki(query):
    try:
        summary = wikipedia.summary(query, sentences=5)
        page = wikipedia.page(query)
        return f"**{page.title}**\n\n{summary}\n\n→ {page.url}"
    except wikipedia.DisambiguationError as e:
        return f"Ambiguous. Try: {', '.join(e.options[:5])}"
    except Exception as e:
        return f"Error: {e}"

def weather(city):
    try:
        r = requests.get(f"https://wttr.in/{city}?format=j1", timeout=10, headers={"User-Agent":"curl/7.68.0"})
        dw = r.json()
        current = dw["current_condition"][0]
        area = dw["nearest_area"][0]
        desc = current["weatherDesc"][0]["value"]
        ICONS = {"sunny":"☀️","clear":"🌙","cloud":"☁️","rain":"🌧️","snow":"❄️","fog":"🌫️","thunder":"⛈️","mist":"🌫️","haze":"🌫️","partly":"⛅"}
        icon = next((v for k,v in ICONS.items() if k in desc.lower()), "🌡️")
        table = Table(box=box.ROUNDED, border_style="cyan", show_header=False, padding=(0,1))
        table.add_column("Key", style="bold cyan", no_wrap=True)
        table.add_column("Value", style="white")
        table.add_row("Location", f"{area['areaName'][0]['value']}, {area['country'][0]['value']}")
        table.add_row("Condition", f"{icon} {desc}")
        table.add_row("Temp", f"{current['temp_C']}C (Feels {current['FeelsLikeC']}C)")
        table.add_row("Humidity", f"{current['humidity']}%")
        table.add_row("Wind", f"{current['windspeedKmph']} km/h")
        console.print(table)
        return None
    except Exception as e:
        return f"Error: {e}"

def generate_code(client, model, prompt, filename):
    code = re.sub(r"```python|```","", ask(client, model, f"Write Python for: {prompt}\nONLY raw Python.")).strip()
    open(filename,"w").write(code)
    console.print(f"[green]✓ {filename}[/green]")
    console.print(Markdown(f"```python\n{code}\n```"))

def generate_html(client, model, prompt, filename):
    html = re.sub(r"```html|```","", ask(client, model, f"Write HTML/CSS/JS for: {prompt}\nONLY raw HTML.")).strip()
    open(filename,"w").write(html)
    console.print(f"[green]✓ {filename}[/green]")

def generate_doc(client, model, prompt, filename):
    doc = ask(client, model, f"Write markdown about: {prompt}\nONLY markdown.")
    open(filename,"w").write(doc)
    console.print(f"[green]✓ {filename}[/green]")
    console.print(Markdown(doc))

def run_file(filename):
    try:
        result = subprocess.run(["python", filename], capture_output=True, text=True, timeout=30)
        console.print(Panel(result.stdout or result.stderr, title=f"[bold]{filename}[/bold]", border_style="green"))
    except Exception as e:
        console.print(f"[red]{e}[/red]")

def debug_file(client, model, filename):
    try:
        code = open(filename).read()
        fixed = re.sub(r"```python|```","", ask(client, model, f"Fix ONLY:\n\n{code}")).strip()
        open(filename,"w").write(fixed)
        console.print(f"[green]✓ Fixed: {filename}[/green]")
        console.print(Markdown(f"```python\n{fixed}\n```"))
    except Exception as e:
        console.print(f"[red]{e}[/red]")

def git_cmd(command):
    result = subprocess.run(f"git {command}", shell=True, capture_output=True, text=True)
    console.print(Panel((result.stdout or result.stderr).strip(), title="[bold]Git[/bold]", border_style="cyan"))

def make_artifact(name, content):
    try:
        if "```python" in content or content.strip().startswith(("def ","import ")):
            ext, content = ".py", re.sub(r"```python|```","",content).strip()
        elif "```html" in content or "<html" in content:
            ext, content = ".html", re.sub(r"```html|```","",content).strip()
        else:
            ext = ".md"
        filename = f"{name.replace(' ','_')}{ext}"
        open(filename,"w").write(content)
        return f"✓ Saved: '{filename}'"
    except Exception as e:
        return f"Error: {e}"

def ocr(image_path):
    try:
        console.print("[yellow]Reading...[/yellow]")
        return "\n".join(easyocr.Reader(["en"], gpu=False).readtext(image_path, detail=0))
    except Exception as e:
        return f"Error: {e}"

async def browse(url):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url, timeout=15000)
        title = await page.title()
        content = await page.inner_text("body")
        await browser.close()
        return f"**{title}**\n\n{content[:2000]}"

def show_help(provider_name):
    console.print(Panel(f"""
[bold cyan]Commands:[/bold cyan]

  [bold white]── AI ──[/bold white]
  [green]/model  /provider  /clear[/green]

  [bold white]── Memory ──[/bold white]
  [green]/memory add <key> <val>[/green]  [green]/memory view[/green]  [green]/memory forget <key>[/green]

  [bold white]── Chats ──[/bold white]
  [green]/chats save <name>[/green]  [green]/chats list[/green]  [green]/chats load <#>[/green]

  [bold white]── Music 🎵 ──[/bold white]
  [green]/play <song>[/green]         — Play any song from YouTube
  [green]/pause[/green]               — Pause
  [green]/resume[/green]              — Resume
  [green]/stop[/green]                — Stop & clear queue
  [green]/skip[/green]                — Skip to next
  [green]/queue <song>[/green]        — Add to queue
  [green]/nowplaying[/green]          — Show current song & queue
  [green]/volume <0-100>[/green]      — Set volume

  [bold white]── Voice ──[/bold white]
  [green]/mic on[/green]  [green]/mic off[/green]

  [bold white]── Timer ──[/bold white]
  [green]/timer <min>[/green]  [green]/stopwatch start/stop/lap/check[/green]

  [bold white]── Image ──[/bold white]
  [green]/imagine <prompt>[/green]

  [bold white]── Advisor ──[/bold white]
  [green]/advisor <msg>[/green]  [green]/goal add/list/done[/green]

  [bold white]── Stocks ──[/bold white]
  [green]/stock <SYM>[/green]  [green]/stocks <sector>[/green]  [green]/recommend <q>[/green]
  [green]/impact <event>[/green]  [green]/portfolio add/view/remove[/green]  [green]/marketnews[/green]

  [bold white]── Code ──[/bold white]
  [green]/code /html /doc /runfile /debug /run /git[/green]

  [bold white]── Tools ──[/bold white]
  [green]/search /scrape /browse /wiki /weather /ocr /artifact[/green]

  [green]/help  /exit[/green]
  [dim]Provider: {provider_name} | Mic: {'ON 🎤' if mic_mode else 'OFF'} | 🎵 {current_song or 'Nothing playing'}[/dim]
""", title="[bold]VISION CLI v3.0[/bold]", border_style="cyan"))

# ── STARTUP ────────────────────────────────────────────────────────
console.print(BANNER)
console.print(f"\n[bold cyan]  Vision CLI v3.0 — AI Agent Ready[/bold cyan]")
if memory:
    console.print(f"[dim]  ✓ {len(memory)} memories | {len(goals)} goals | {len(portfolio)} stocks[/dim]\n")

provider_choice = select_provider()
client, provider_name, models = setup_provider(provider_choice)
model = select_model(models)
show_help(provider_name)

last_reply = ""

while True:
    try:
        if mic_mode:
            user = listen() or input("[YOU 🎤] → ").strip()
        else:
            user = input("[YOU] → ").strip()
    except (EOFError, KeyboardInterrupt):
        save_data()
        stop_music()
        console.print("\n[bold red]Bye![/bold red]")
        break

    if not user: continue
    elif user == "/exit":
        save_data()
        stop_music()
        console.print("[bold red]Bye![/bold red]")
        break
    elif user == "/clear":
        history.clear()
        console.print("[green]✓ Cleared[/green]")
    elif user == "/help": show_help(provider_name)
    elif user == "/model": model = select_model(models)
    elif user == "/provider":
        provider_choice = select_provider()
        client, provider_name, models = setup_provider(provider_choice)
        model = select_model(models)
        history.clear()
    elif user == "/mic on":
        mic_mode = True
        console.print("[green]🎤 Mic ON[/green]")
    elif user == "/mic off":
        mic_mode = False
        console.print("[yellow]🔇 Mic OFF[/yellow]")

    # ── Music ──
    elif user.startswith("/play "): play_music(user[6:])
    elif user == "/pause": pause_music()
    elif user == "/resume": resume_music()
    elif user == "/stop": stop_music()
    elif user == "/skip": skip_music()
    elif user.startswith("/queue "): queue_music(user[7:])
    elif user == "/nowplaying": show_queue()
    elif user.startswith("/volume "): set_volume(user[8:])

    # ── Memory ──
    elif user.startswith("/memory add "):
        parts = user[12:].split(" ", 1)
        if len(parts) == 2: memory_add(parts[0], parts[1])
    elif user == "/memory view": memory_view()
    elif user.startswith("/memory forget "): memory_forget(user[15:])

    # ── Chats ──
    elif user.startswith("/chats save "): save_chat(user[12:])
    elif user == "/chats list": list_chats()
    elif user.startswith("/chats load "): load_chat(user[12:])

    # ── Timer ──
    elif user.startswith("/timer "): study_timer(user[7:])
    elif user.startswith("/stopwatch "): stopwatch_cmd(user[11:].strip())

    # ── Image ──
    elif user.startswith("/imagine "): generate_image(user[9:])

    # ── Advisor ──
    elif user.startswith("/advisor "):
        console.print("[yellow]Advisor thinking...[/yellow]")
        reply = advisor_chat(client, model, user[9:])
        last_reply = reply
        console.print(Panel(Markdown(reply), title="[bold cyan]Your Advisor[/bold cyan]", border_style="cyan"))
        if mic_mode: speak(reply[:300])
    elif user.startswith("/goal add "):
        goals.append({"goal": user[10:], "done": False, "added": datetime.now().strftime("%d/%m/%Y")})
        save_data()
        console.print("[green]✓ Goal added[/green]")
    elif user == "/goal list":
        if not goals: console.print("[yellow]No goals.[/yellow]")
        else:
            table = Table(box=box.ROUNDED, border_style="cyan", padding=(0,1))
            table.add_column("#", style="bold cyan")
            table.add_column("Goal")
            table.add_column("Status")
            table.add_column("Added", style="dim")
            for i, g in enumerate(goals, 1):
                table.add_row(str(i), g["goal"], "[green]✓[/green]" if g["done"] else "[yellow]⏳[/yellow]", g["added"])
            console.print(table)
    elif user.startswith("/goal done "):
        try:
            goals[int(user[11:])-1]["done"] = True
            save_data()
            console.print("[green]✓ Done![/green]")
        except: console.print("[red]Invalid.[/red]")

    # ── Stocks ──
    elif user.startswith("/stock "): get_stock(user[7:].strip().upper())
    elif user.startswith("/stocks "): search_stocks(user[8:].strip())
    elif user.startswith("/recommend "): stock_recommend(client, model, user[11:])
    elif user.startswith("/impact "): war_impact(client, model, user[8:])
    elif user == "/marketnews": market_news()
    elif user.startswith("/marketnews "): market_news(user[12:])
    elif user.startswith("/portfolio "):
        parts = user[11:].split()
        if parts[0] == "add" and len(parts) == 4: portfolio_add(parts[1], parts[2], parts[3])
        elif parts[0] == "view": portfolio_view()
        elif parts[0] == "remove" and len(parts) == 2:
            sym = parts[1].upper()
            if sym in portfolio:
                del portfolio[sym]; save_data()
                console.print(f"[green]✓ Removed {sym}[/green]")

    # ── Code ──
    elif user.startswith("/code "):
        parts = user[6:].split(" ", 1)
        if len(parts) == 2: generate_code(client, model, parts[1], parts[0])
    elif user.startswith("/html "):
        parts = user[6:].split(" ", 1)
        if len(parts) == 2: generate_html(client, model, parts[1], parts[0])
    elif user.startswith("/doc "):
        parts = user[5:].split(" ", 1)
        if len(parts) == 2: generate_doc(client, model, parts[1], parts[0])
    elif user.startswith("/runfile "): run_file(user[9:])
    elif user.startswith("/debug "): debug_file(client, model, user[7:])
    elif user.startswith("/git "): git_cmd(user[5:])

    # ── Tools ──
    elif user.startswith("/search "):
        console.print("[yellow]Searching...[/yellow]")
        console.print(Markdown(search(user[8:])))
    elif user.startswith("/scrape "):
        console.print(Markdown(f"```\n{scrape(user[8:])}\n```"))
    elif user.startswith("/browse "):
        try:
            result = asyncio.get_event_loop().run_until_complete(browse(user[8:]))
            console.print(Markdown(result))
        except Exception as e: console.print(f"[red]{e}[/red]")
    elif user.startswith("/wiki "):
        console.print(Markdown(wiki(user[6:])))
    elif user.startswith("/weather "):
        err = weather(user[9:])
        if err: console.print(f"[red]{err}[/red]")
    elif user.startswith("/artifact "):
        if last_reply: console.print(f"[green]{make_artifact(user[10:], last_reply)}[/green]")
        else: console.print("[red]No reply yet.[/red]")
    elif user.startswith("/ocr "):
        console.print(Markdown(f"```\n{ocr(user[5:])}\n```"))
    elif user.startswith("/run "):
        try: exec(user[5:])
        except Exception as e: console.print(f"[red]{e}[/red]")
    else:
        console.print("[yellow]Thinking...[/yellow]")
        reply = chat(client, model, user)
        last_reply = reply
        console.print(Panel(Markdown(reply), border_style="blue"))
        if mic_mode: speak(reply[:300])
