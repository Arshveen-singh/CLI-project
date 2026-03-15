import warnings
warnings.filterwarnings("ignore")

import os, re, subprocess, requests, wikipedia, asyncio
import json, time, threading
from datetime import datetime
from pathlib import Path
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TimeElapsedColumn
from rich import box
from ddgs import DDGS
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
import easyocr
import yfinance as yf

console = Console()
history = []
advisor_history = []
portfolio = {}
goals = []

# ── File paths ─────────────────────────────────────────────────────
MEMORY_FILE = "vision_memory.json"
CHATS_DIR = "vision_chats"
Path(CHATS_DIR).mkdir(exist_ok=True)

# ── Memory System ──────────────────────────────────────────────────
def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    return {"facts": {}, "created": datetime.now().strftime("%d/%m/%Y")}

def save_memory_file(mem):
    with open(MEMORY_FILE, "w") as f:
        json.dump(mem, f, indent=2)

memory = load_memory()

def memory_add(key, value):
    memory["facts"][key] = {"value": value, "added": datetime.now().strftime("%d/%m/%Y %H:%M")}
    save_memory_file(memory)
    console.print(f"[green]✓ Memory saved: {key} → {value}[/green]")

def memory_view():
    if not memory["facts"]:
        console.print("[yellow]No memories yet. Use /memory add <key> <value>[/yellow]")
        return
    table = Table(box=box.ROUNDED, border_style="cyan", padding=(0,1))
    table.add_column("Key", style="bold cyan")
    table.add_column("Value", style="white")
    table.add_column("Added", style="dim")
    for key, data in memory["facts"].items():
        table.add_row(key, data["value"], data["added"])
    console.print(table)

def memory_forget(key):
    if key in memory["facts"]:
        del memory["facts"][key]
        save_memory_file(memory)
        console.print(f"[green]✓ Forgot: {key}[/green]")
    else:
        console.print(f"[red]Memory '{key}' not found.[/red]")

def get_memory_context():
    if not memory["facts"]:
        return ""
    facts = "\n".join([f"- {k}: {v['value']}" for k, v in memory["facts"].items()])
    return f"\n\nUser memory facts:\n{facts}"

# ── Chat Library ───────────────────────────────────────────────────
def save_chat(name):
    if not history:
        console.print("[red]No chat history to save.[/red]")
        return
    filename = f"{CHATS_DIR}/{name.replace(' ', '_')}_{datetime.now().strftime('%d%m%Y_%H%M')}.json"
    with open(filename, "w") as f:
        json.dump({"name": name, "date": datetime.now().strftime("%d/%m/%Y %H:%M"), "messages": history}, f, indent=2)
    console.print(f"[green]✓ Chat saved as '{filename}'[/green]")

def list_chats():
    files = list(Path(CHATS_DIR).glob("*.json"))
    if not files:
        console.print("[yellow]No saved chats yet.[/yellow]")
        return
    table = Table(box=box.ROUNDED, border_style="cyan", padding=(0,1))
    table.add_column("#", style="bold cyan")
    table.add_column("Name", style="white")
    table.add_column("Date", style="dim")
    table.add_column("Messages", style="white")
    for i, f in enumerate(sorted(files), 1):
        with open(f) as file:
            data = json.load(file)
        table.add_row(str(i), data.get("name", f.stem), data.get("date", "N/A"), str(len(data.get("messages", []))))
    console.print(table)

def load_chat(index):
    global history
    files = sorted(Path(CHATS_DIR).glob("*.json"))
    try:
        with open(files[int(index)-1]) as f:
            data = json.load(f)
        history = data["messages"]
        console.print(f"[green]✓ Loaded chat: {data['name']} ({len(history)} messages)[/green]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

# ── Study Timer & Stopwatch ────────────────────────────────────────
stopwatch_start = None
stopwatch_running = False
lap_times = []

def study_timer(minutes):
    secs = int(float(minutes) * 60)
    console.print(f"[bold cyan]⏱ Study timer started: {minutes} minutes[/bold cyan]")
    console.print("[dim]Press Ctrl+C to stop early[/dim]\n")
    try:
        for remaining in range(secs, 0, -1):
            mins, s = divmod(remaining, 60)
            console.print(f"\r[cyan]⏱ {mins:02d}:{s:02d} remaining[/cyan]", end="")
            time.sleep(1)
        console.print("\n[bold green]✓ TIMER DONE! Take a break 🎉[/bold green]")
    except KeyboardInterrupt:
        console.print("\n[yellow]Timer stopped.[/yellow]")

def stopwatch_cmd(action):
    global stopwatch_start, stopwatch_running, lap_times
    if action == "start":
        stopwatch_start = time.time()
        stopwatch_running = True
        lap_times = []
        console.print("[green]✓ Stopwatch started[/green]")
    elif action == "stop":
        if stopwatch_running:
            elapsed = time.time() - stopwatch_start
            stopwatch_running = False
            mins, secs = divmod(int(elapsed), 60)
            console.print(f"[bold green]✓ Stopped: {mins:02d}:{secs:02d}[/bold green]")
        else:
            console.print("[red]Stopwatch not running.[/red]")
    elif action == "lap":
        if stopwatch_running:
            elapsed = time.time() - stopwatch_start
            lap_times.append(elapsed)
            mins, secs = divmod(int(elapsed), 60)
            console.print(f"[cyan]Lap {len(lap_times)}: {mins:02d}:{secs:02d}[/cyan]")
        else:
            console.print("[red]Stopwatch not running.[/red]")
    elif action == "check":
        if stopwatch_running:
            elapsed = time.time() - stopwatch_start
            mins, secs = divmod(int(elapsed), 60)
            console.print(f"[cyan]⏱ Running: {mins:02d}:{secs:02d}[/cyan]")
            if lap_times:
                for i, lt in enumerate(lap_times, 1):
                    m, s = divmod(int(lt), 60)
                    console.print(f"  Lap {i}: {m:02d}:{s:02d}")
        else:
            console.print("[yellow]Stopwatch not running.[/yellow]")

# ── Image Generation ───────────────────────────────────────────────
def generate_image(prompt, hf_token=None):
    safe_prompt = prompt.replace(" ", "%20")
    filename = f"vision_img_{datetime.now().strftime('%H%M%S')}.jpg"

    # Try Pollinations.ai first (no API key needed)
    console.print("[yellow]Trying Pollinations.ai...[/yellow]")
    try:
        url = f"https://image.pollinations.ai/prompt/{safe_prompt}?width=512&height=512&nologo=true"
        r = requests.get(url, timeout=30)
        if r.status_code == 200 and "image" in r.headers.get("content-type", ""):
            with open(filename, "wb") as f:
                f.write(r.content)
            console.print(f"[green]✓ Image saved as '{filename}'[/green]")
            # Display in Colab
            try:
                from IPython.display import display, Image as IPImage
                display(IPImage(filename))
            except:
                pass
            return

    except Exception as e:
        console.print(f"[yellow]Pollinations failed: {e} — trying HuggingFace...[/yellow]")

    # Fallback to HuggingFace
    try:
        token = hf_token or os.environ.get("HF_TOKEN")
        if not token:
            token = input("Enter HuggingFace token (free at huggingface.co): ").strip()
            os.environ["HF_TOKEN"] = token
        
        API_URL = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-2-1"
        headers = {"Authorization": f"Bearer {token}"}
        payload = {"inputs": prompt}
        console.print("[yellow]Generating with HuggingFace SD2.1...[/yellow]")
        r = requests.post(API_URL, headers=headers, json=payload, timeout=60)
        if r.status_code == 200:
            with open(filename, "wb") as f:
                f.write(r.content)
            console.print(f"[green]✓ Image saved as '{filename}'[/green]")
            try:
                from IPython.display import display, Image as IPImage
                display(IPImage(filename))
            except:
                pass
        else:
            console.print(f"[red]HuggingFace error: {r.text[:200]}[/red]")
    except Exception as e:
        console.print(f"[red]Image generation failed: {e}[/red]")

# ── Banner & Prompts ───────────────────────────────────────────────
BANNER = """[bold cyan]
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
You never waffle. You never over-explain. You treat the user as intelligent.
When coding: write clean, commented, production-quality code only. No explanations unless asked.
When making artifacts: output ONLY the raw content, no extra text."""

ADVISOR_PROMPT = """You are Arshveen's personal advisor, business partner, and trusted confidant.
You know him well — he's a 14 year old Class 9 student from Delhi, solo developer, 
entrepreneur, and big thinker. He works on WTv (war intelligence dashboard), VISION AI, 
and Vision CLI. He's sharp, ambitious, and thinks way beyond his age.

Your role:
- Be his brutally honest advisor — no sugarcoating, no fluff
- Act as his business partner — evaluate ideas critically and practically  
- Be his goal tracker — remember and follow up on his goals
- Be his venting buddy — listen, validate, then redirect constructively
- Give real financial and stock advice tailored for a young Indian investor
- Think long term for him — career, business, money, life decisions
- Challenge bad ideas, celebrate good ones
- Speak casually, like a trusted older friend who happens to be a genius

Never be preachy. Never lecture. Be real."""

GROQ_MODELS = {
    "1": ("moonshotai/kimi-k2-instruct-0905", "Kimi K2        — Best for reasoning & chat"),
    "2": ("qwen/qwen3-32b",                   "Qwen 3 32B     — Best for coding"),
    "3": ("llama-3.3-70b-versatile",           "LLaMA 3.3 70B  — Best for general tasks"),
}
OPENROUTER_MODELS = {
    "1": ("anthropic/claude-3.5-sonnet",        "Claude 3.5 Sonnet — Best overall"),
    "2": ("google/gemini-flash-1.5",            "Gemini Flash      — Fast & smart"),
    "3": ("meta-llama/llama-3.3-70b-instruct",  "LLaMA 3.3 70B     — Open source"),
    "4": ("deepseek/deepseek-r1",               "DeepSeek R1       — Reasoning beast"),
}
OLLAMA_MODELS = {
    "1": ("llama3.2",  "LLaMA 3.2   — General tasks"),
    "2": ("qwen2.5",   "Qwen 2.5    — Coding"),
    "3": ("mistral",   "Mistral     — Fast & efficient"),
    "4": ("custom",    "Custom      — Enter model name"),
}
INDIAN_SECTORS = {
    "banking": ["HDFCBANK","ICICIBANK","SBIN","AXISBANK","KOTAKBANK","INDUSINDBK","BANDHANBNK"],
    "it":      ["TCS","INFY","WIPRO","HCLTECH","TECHM","LTIM","MPHASIS"],
    "pharma":  ["SUNPHARMA","DRREDDY","CIPLA","DIVISLAB","BIOCON","AUROPHARMA"],
    "auto":    ["TATAMOTORS","MARUTI","M&M","BAJAJ-AUTO","EICHERMOT","HEROMOTOCO"],
    "tata":    ["TCS","TATAMOTORS","TATASTEEL","TATAPOWER","TATACOMM","TATACHEM"],
    "energy":  ["RELIANCE","ONGC","NTPC","POWERGRID","ADANIGREEN","TATAPOWER"],
    "fmcg":    ["HINDUNILVR","ITC","NESTLEIND","BRITANNIA","DABUR","MARICO"],
    "adani":   ["ADANIENT","ADANIGREEN","ADANIPORTS","ADANIPOWER","ADANITRANS"],
    "smallcap":["IRFC","RVNL","RAILTEL","IRCTC","NYKAA","ZOMATO","PAYTM"],
}

# ── Provider ───────────────────────────────────────────────────────
def select_provider():
    console.print(Panel("[bold cyan]Select AI Provider[/bold cyan]", border_style="cyan"))
    console.print("  [green][1][/green] Groq          — Free, ultra fast")
    console.print("  [green][2][/green] OpenRouter    — Access any model")
    console.print("  [green][3][/green] Ollama        — 100% local, private")
    while True:
        choice = input("\n→ Enter choice (1-3): ").strip()
        if choice in ["1","2","3"]: return choice
        console.print("[red]Invalid choice.[/red]")

def setup_provider(provider):
    if provider == "1":
        from groq import Groq
        key = os.environ.get("GROQ_API_KEY") or input("Enter Groq API key: ").strip()
        return Groq(api_key=key), "Groq", GROQ_MODELS
    elif provider == "2":
        from openai import OpenAI
        key = os.environ.get("OPENROUTER_API_KEY") or input("Enter OpenRouter API key: ").strip()
        return OpenAI(base_url="https://openrouter.ai/api/v1", api_key=key), "OpenRouter", OPENROUTER_MODELS
    elif provider == "3":
        from openai import OpenAI
        host = input("Ollama host (Enter for localhost): ").strip() or "http://localhost:11434"
        return OpenAI(base_url=f"{host}/v1", api_key="ollama"), "Ollama", OLLAMA_MODELS

def select_model(models):
    console.print(Panel("[bold cyan]Select a Model[/bold cyan]", border_style="cyan"))
    for key, (_, desc) in models.items():
        console.print(f"  [green][{key}][/green] {desc}")
    while True:
        choice = input(f"\n→ Enter choice (1-{len(models)}): ").strip()
        if choice in models:
            model_id, desc = models[choice]
            if model_id == "custom":
                model_id = input("Enter model name: ").strip()
            console.print(f"\n[green]✓ Using {desc.split('—')[0].strip()}[/green]\n")
            return model_id
        console.print("[red]Invalid choice.[/red]")

# ── Chat ───────────────────────────────────────────────────────────
def chat(client, model, user_input, system=None):
    history.append({"role": "user", "content": user_input})
    mem_context = get_memory_context()
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": (system or SYSTEM_PROMPT) + mem_context}, *history],
        max_tokens=2048,
    )
    reply = response.choices[0].message.content
    reply = re.sub(r"<think>.*?</think>", "", reply, flags=re.DOTALL).strip()
    history.append({"role": "assistant", "content": reply})
    return reply

def advisor_chat(client, model, user_input):
    advisor_history.append({"role": "user", "content": user_input})
    context = f"Current goals: {goals}\nPortfolio: {portfolio}\n" if goals or portfolio else ""
    mem_context = get_memory_context()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": ADVISOR_PROMPT + f"\n\n{context}" + mem_context},
            *advisor_history
        ],
        max_tokens=2048,
    )
    reply = response.choices[0].message.content
    reply = re.sub(r"<think>.*?</think>", "", reply, flags=re.DOTALL).strip()
    advisor_history.append({"role": "assistant", "content": reply})
    return reply

def ask(client, model, prompt, system=None):
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system or SYSTEM_PROMPT}, {"role": "user", "content": prompt}],
        max_tokens=2048,
    )
    return re.sub(r"<think>.*?</think>", "", response.choices[0].message.content, flags=re.DOTALL).strip()

# ── Stocks ─────────────────────────────────────────────────────────
def get_stock(symbol):
    try:
        for suffix in [".NS", ".BO"]:
            ticker = yf.Ticker(symbol + suffix)
            info = ticker.info
            price = info.get("currentPrice") or info.get("regularMarketPrice")
            if price:
                prev = info.get("previousClose", price)
                change = price - prev
                change_pct = (change / prev * 100) if prev else 0
                color = "green" if change >= 0 else "red"
                arrow = "▲" if change >= 0 else "▼"
                table = Table(box=box.ROUNDED, border_style="cyan", show_header=False, padding=(0,1))
                table.add_column("Key", style="bold cyan", no_wrap=True)
                table.add_column("Value", style="white")
                table.add_row("Stock", f"[bold]{info.get('longName', symbol)}[/bold]")
                table.add_row("Price", f"[bold {color}]₹{price:.2f} {arrow} {change:+.2f} ({change_pct:+.2f}%)[/bold {color}]")
                table.add_row("52W High", f"₹{info.get('fiftyTwoWeekHigh', 'N/A')}")
                table.add_row("52W Low", f"₹{info.get('fiftyTwoWeekLow', 'N/A')}")
                table.add_row("Market Cap", f"₹{info.get('marketCap',0)/1e9:.2f}B" if info.get("marketCap") else "N/A")
                table.add_row("P/E Ratio", str(round(info.get("trailingPE",0),2)) if info.get("trailingPE") else "N/A")
                table.add_row("Volume", f"{info.get('volume',0):,}")
                table.add_row("Sector", info.get("sector","N/A"))
                console.print(table)
                return
        console.print(f"[red]Stock '{symbol}' not found.[/red]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

def search_stocks(query):
    query = query.lower()
    if query in INDIAN_SECTORS:
        symbols = INDIAN_SECTORS[query]
        table = Table(box=box.ROUNDED, border_style="cyan", padding=(0,1), title=f"[bold cyan]{query.upper()} Sector[/bold cyan]")
        table.add_column("Symbol", style="bold green")
        table.add_column("Price ₹", style="white")
        table.add_column("Change", style="white")
        for sym in symbols:
            try:
                info = yf.Ticker(sym + ".NS").info
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
    reply = ask(client, model, f"Indian stock market advisor. Query: {query}\nGive specific NSE stock picks with thesis, risk level, time horizon.")
    console.print(Panel(Markdown(reply), title="[bold]Recommendations[/bold]", border_style="cyan"))

def war_impact(client, model, event):
    console.print("[yellow]Analyzing impact...[/yellow]")
    reply = ask(client, model, f"How does '{event}' impact Indian stocks? Give sectors, specific NSE symbols, commodities, INR impact.")
    console.print(Panel(Markdown(reply), title="[bold]Market Impact[/bold]", border_style="red"))

def portfolio_add(symbol, qty, buy_price):
    portfolio[symbol.upper()] = {"qty": float(qty), "buy_price": float(buy_price)}
    console.print(f"[green]✓ Added {qty}x {symbol.upper()} @ ₹{buy_price}[/green]")

def portfolio_view():
    if not portfolio:
        console.print("[yellow]Portfolio empty.[/yellow]")
        return
    table = Table(box=box.ROUNDED, border_style="cyan", padding=(0,1))
    table.add_column("Symbol", style="bold green")
    table.add_column("Qty")
    table.add_column("Buy ₹")
    table.add_column("Current ₹")
    table.add_column("P&L")
    table.add_column("P&L %")
    total_inv = total_cur = 0
    for sym, data in portfolio.items():
        try:
            info = yf.Ticker(sym+".NS").info
            cur = info.get("currentPrice") or info.get("regularMarketPrice", data["buy_price"])
            inv = data["qty"] * data["buy_price"]
            cv = data["qty"] * cur
            pnl = cv - inv
            pct = (pnl/inv*100) if inv else 0
            color = "green" if pnl>=0 else "red"
            table.add_row(sym, str(data["qty"]), f"₹{data['buy_price']:.2f}", f"₹{cur:.2f}", f"[{color}]₹{pnl:+.2f}[/{color}]", f"[{color}]{pct:+.2f}%[/{color}]")
            total_inv += inv; total_cur += cv
        except:
            table.add_row(sym, str(data["qty"]), f"₹{data['buy_price']:.2f}", "N/A", "N/A", "N/A")
    console.print(table)
    pnl = total_cur - total_inv
    pct = (pnl/total_inv*100) if total_inv else 0
    color = "green" if pnl>=0 else "red"
    console.print(f"[bold]Invested:[/bold] ₹{total_inv:.2f}  [bold]Current:[/bold] ₹{total_cur:.2f}  [bold {color}]P&L: ₹{pnl:+.2f} ({pct:+.2f}%)[/bold {color}]")

def market_news(query="indian stock market"):
    results = []
    with DDGS() as ddgs:
        for r in ddgs.text(f"{query} NSE BSE today", max_results=5):
            results.append(f"**{r['title']}**\n{r['body']}\n{r['href']}")
    console.print(Markdown("\n\n".join(results)))

# ── Other Tools ────────────────────────────────────────────────────
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
        r = requests.get(f"https://wttr.in/{city}?format=j1", timeout=10, headers={"User-Agent": "curl/7.68.0"})
        data = r.json()
        current = data["current_condition"][0]
        area = data["nearest_area"][0]
        area_name = area["areaName"][0]["value"]
        country = area["country"][0]["value"]
        temp_c = current["temp_C"]
        feels = current["FeelsLikeC"]
        humidity = current["humidity"]
        wind = current["windspeedKmph"]
        desc = current["weatherDesc"][0]["value"]
        ICONS = {"sunny":"☀️","clear":"🌙","cloud":"☁️","rain":"🌧️","snow":"❄️","fog":"🌫️","thunder":"⛈️","mist":"🌫️","haze":"🌫️","partly":"⛅"}
        icon = next((v for k,v in ICONS.items() if k in desc.lower()), "🌡️")
        table = Table(box=box.ROUNDED, border_style="cyan", show_header=False, padding=(0,1))
        table.add_column("Key", style="bold cyan", no_wrap=True)
        table.add_column("Value", style="white")
        table.add_row("Location", f"{area_name}, {country}")
        table.add_row("Condition", f"{icon} {desc}")
        table.add_row("Temp", f"{temp_c}C (Feels like {feels}C)")
        table.add_row("Humidity", f"{humidity}%")
        table.add_row("Wind", f"{wind} km/h")
        console.print(table)
        return None
    except Exception as e:
        return f"Error: {e}"

def generate_code(client, model, prompt, filename):
    console.print("[yellow]Generating...[/yellow]")
    code = re.sub(r"```python|```", "", ask(client, model, f"Write Python code for: {prompt}\nONLY raw Python code.")).strip()
    with open(filename, "w") as f: f.write(code)
    console.print(f"[green]✓ Saved: '{filename}'[/green]")
    console.print(Markdown(f"```python\n{code}\n```"))

def generate_html(client, model, prompt, filename):
    console.print("[yellow]Generating...[/yellow]")
    html = re.sub(r"```html|```", "", ask(client, model, f"Write HTML/CSS/JS for: {prompt}\nONLY raw HTML.")).strip()
    with open(filename, "w") as f: f.write(html)
    console.print(f"[green]✓ Saved: '{filename}'[/green]")

def generate_doc(client, model, prompt, filename):
    console.print("[yellow]Generating...[/yellow]")
    doc = ask(client, model, f"Write markdown doc about: {prompt}\nONLY markdown.")
    with open(filename, "w") as f: f.write(doc)
    console.print(f"[green]✓ Saved: '{filename}'[/green]")
    console.print(Markdown(doc))

def run_file(filename):
    try:
        result = subprocess.run(["python", filename], capture_output=True, text=True, timeout=30)
        console.print(Panel(result.stdout or result.stderr, title=f"[bold]Output: {filename}[/bold]", border_style="green"))
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

def debug_file(client, model, filename):
    try:
        with open(filename) as f: code = f.read()
        fixed = re.sub(r"```python|```", "", ask(client, model, f"Fix this code, ONLY corrected code:\n\n{code}")).strip()
        with open(filename, "w") as f: f.write(fixed)
        console.print(f"[green]✓ Fixed: '{filename}'[/green]")
        console.print(Markdown(f"```python\n{fixed}\n```"))
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

def git_cmd(command):
    try:
        result = subprocess.run(f"git {command}", shell=True, capture_output=True, text=True)
        console.print(Panel((result.stdout or result.stderr).strip(), title="[bold]Git[/bold]", border_style="cyan"))
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

def make_artifact(name, content):
    try:
        if "```python" in content or content.strip().startswith(("def ","import ")):
            ext, content = ".py", re.sub(r"```python|```","",content).strip()
        elif "```html" in content or "<html" in content:
            ext, content = ".html", re.sub(r"```html|```","",content).strip()
        else:
            ext = ".md"
        filename = f"{name.replace(' ','_')}{ext}"
        with open(filename, "w") as f: f.write(content)
        return f"✓ Artifact saved as '{filename}'"
    except Exception as e:
        return f"Error: {e}"

def ocr(image_path):
    try:
        console.print("[yellow]Reading image...[/yellow]")
        reader = easyocr.Reader(["en"], gpu=False)
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
  [green]/model[/green]                              — Switch model
  [green]/provider[/green]                           — Switch provider
  [green]/clear[/green]                              — Clear chat history

  [bold white]── Memory ──[/bold white]
  [green]/memory add <key> <value>[/green]           — Save a memory
  [green]/memory view[/green]                        — View all memories
  [green]/memory forget <key>[/green]                — Delete a memory

  [bold white]── Chat Library ──[/bold white]
  [green]/chats save <name>[/green]                  — Save current chat
  [green]/chats list[/green]                         — View saved chats
  [green]/chats load <number>[/green]                — Load a saved chat

  [bold white]── Timer ──[/bold white]
  [green]/timer <minutes>[/green]                    — Study countdown timer
  [green]/stopwatch start/stop/lap/check[/green]     — Stopwatch

  [bold white]── Image Gen ──[/bold white]
  [green]/imagine <prompt>[/green]                   — Generate AI image

  [bold white]── Advisor ──[/bold white]
  [green]/advisor <message>[/green]                  — Personal advisor
  [green]/goal add <goal>[/green]                    — Add goal
  [green]/goal list[/green]                          — View goals
  [green]/goal done <index>[/green]                  — Complete goal

  [bold white]── Stocks ──[/bold white]
  [green]/stock <SYMBOL>[/green]                     — Live price
  [green]/stocks <sector>[/green]                    — Sector stocks
  [green]/recommend <query>[/green]                  — AI recommendations
  [green]/impact <event>[/green]                     — Market impact analysis
  [green]/portfolio add <SYM> <QTY> <PRICE>[/green] — Add to portfolio
  [green]/portfolio view[/green]                     — View P&L
  [green]/portfolio remove <SYM>[/green]             — Remove stock
  [green]/marketnews[/green]                         — Market news

  [bold white]── Code ──[/bold white]
  [green]/code <file> <prompt>[/green]               — Generate .py
  [green]/html <file> <prompt>[/green]               — Generate .html
  [green]/doc  <file> <prompt>[/green]               — Generate .md
  [green]/runfile <file>[/green]                     — Run file
  [green]/debug <file>[/green]                       — AI fix file
  [green]/run <code>[/green]                         — Run inline Python

  [bold white]── Tools ──[/bold white]
  [green]/search  <query>[/green]                    — Web search
  [green]/scrape  <url>[/green]                      — Scrape webpage
  [green]/browse  <url>[/green]                      — Headless browser
  [green]/wiki    <query>[/green]                    — Wikipedia
  [green]/weather <city>[/green]                     — Weather
  [green]/ocr     <imagepath>[/green]                — Image to text
  [green]/artifact <name>[/green]                    — Save last reply
  [green]/git <command>[/green]                      — Git command

  [green]/help[/green]                               — This menu
  [green]/exit[/green]                               — Quit

  [yellow]Anything else = chat with AI[/yellow]
  [dim]Provider: {provider_name}[/dim]
""", title="[bold]VISION CLI[/bold]", border_style="cyan"))

# ── STARTUP ────────────────────────────────────────────────────────
console.print(BANNER)
console.print("[bold cyan]         AI Agent Ready — Type /help for commands[/bold cyan]\n")
if memory["facts"]:
    console.print(f"[dim]✓ Loaded {len(memory['facts'])} memories[/dim]\n")

provider_choice = select_provider()
client, provider_name, models = setup_provider(provider_choice)
model = select_model(models)
show_help(provider_name)

last_reply = ""

while True:
    try:
        user = input("[YOU] → ").strip()
    except (EOFError, KeyboardInterrupt):
        console.print("\n[bold red]Exiting...[/bold red]")
        break

    if not user: continue
    elif user == "/exit":
        console.print("[bold red]Bye![/bold red]")
        break
    elif user == "/clear":
        history.clear()
        console.print("[green]History cleared.[/green]")
    elif user == "/help":
        show_help(provider_name)
    elif user == "/model":
        model = select_model(models)
    elif user == "/provider":
        provider_choice = select_provider()
        client, provider_name, models = setup_provider(provider_choice)
        model = select_model(models)
        history.clear()

    # ── Memory ──
    elif user.startswith("/memory add "):
        parts = user[12:].split(" ", 1)
        if len(parts) == 2: memory_add(parts[0], parts[1])
        else: console.print("[red]Usage: /memory add <key> <value>[/red]")
    elif user == "/memory view":
        memory_view()
    elif user.startswith("/memory forget "):
        memory_forget(user[15:])

    # ── Chat Library ──
    elif user.startswith("/chats save "):
        save_chat(user[12:])
    elif user == "/chats list":
        list_chats()
    elif user.startswith("/chats load "):
        load_chat(user[12:])

    # ── Timer ──
    elif user.startswith("/timer "):
        study_timer(user[7:])
    elif user.startswith("/stopwatch "):
        stopwatch_cmd(user[11:].strip())

    # ── Image Gen ──
    elif user.startswith("/imagine "):
        generate_image(user[9:])

    # ── Advisor ──
    elif user.startswith("/advisor "):
        console.print("[yellow]Advisor thinking...[/yellow]")
        reply = advisor_chat(client, model, user[9:])
        last_reply = reply
        console.print(Panel(Markdown(reply), title="[bold cyan]Your Advisor[/bold cyan]", border_style="cyan"))
    elif user.startswith("/goal add "):
        goals.append({"goal": user[10:], "done": False, "added": datetime.now().strftime("%d/%m/%Y")})
        console.print(f"[green]✓ Goal added[/green]")
    elif user == "/goal list":
        if not goals:
            console.print("[yellow]No goals yet.[/yellow]")
        else:
            table = Table(box=box.ROUNDED, border_style="cyan", padding=(0,1))
            table.add_column("#", style="bold cyan")
            table.add_column("Goal", style="white")
            table.add_column("Status")
            table.add_column("Added", style="dim")
            for i, g in enumerate(goals, 1):
                table.add_row(str(i), g["goal"], "[green]✓[/green]" if g["done"] else "[yellow]⏳[/yellow]", g["added"])
            console.print(table)
    elif user.startswith("/goal done "):
        try:
            goals[int(user[11:])-1]["done"] = True
            console.print("[green]✓ Goal complete![/green]")
        except: console.print("[red]Invalid index.[/red]")

    # ── Stocks ──
    elif user.startswith("/stock "):
        get_stock(user[7:].strip().upper())
    elif user.startswith("/stocks "):
        search_stocks(user[8:].strip())
    elif user.startswith("/recommend "):
        stock_recommend(client, model, user[11:])
    elif user.startswith("/impact "):
        war_impact(client, model, user[8:])
    elif user == "/marketnews":
        market_news()
    elif user.startswith("/marketnews "):
        market_news(user[12:])
    elif user.startswith("/portfolio "):
        parts = user[11:].split()
        if parts[0] == "add" and len(parts) == 4:
            portfolio_add(parts[1], parts[2], parts[3])
        elif parts[0] == "view":
            portfolio_view()
        elif parts[0] == "remove" and len(parts) == 2:
            sym = parts[1].upper()
            if sym in portfolio:
                del portfolio[sym]
                console.print(f"[green]✓ Removed {sym}[/green]")
        else:
            console.print("[red]Usage: /portfolio add <SYM> <QTY> <PRICE> | view | remove <SYM>[/red]")

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
        console.print("[yellow]Scraping...[/yellow]")
        console.print(Markdown(f"```\n{scrape(user[8:])}\n```"))
    elif user.startswith("/browse "):
        console.print("[yellow]Browsing...[/yellow]")
        try:
            result = asyncio.get_event_loop().run_until_complete(browse(user[8:]))
            console.print(Markdown(result))
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
    elif user.startswith("/wiki "):
        console.print("[yellow]Wikipedia...[/yellow]")
        console.print(Markdown(wiki(user[6:])))
    elif user.startswith("/weather "):
        console.print("[yellow]Fetching weather...[/yellow]")
        err = weather(user[9:])
        if err: console.print(f"[red]{err}[/red]")
    elif user.startswith("/artifact "):
        if last_reply: console.print(f"[green]{make_artifact(user[10:], last_reply)}[/green]")
        else: console.print("[red]No AI reply yet.[/red]")
    elif user.startswith("/ocr "):
        console.print(Markdown(f"```\n{ocr(user[5:])}\n```"))
    elif user.startswith("/run "):
        try: exec(user[5:])
        except Exception as e: console.print(f"[red]Error: {e}[/red]")
    else:
        console.print("[yellow]Thinking...[/yellow]")
        reply = chat(client, model, user)
        last_reply = reply
        console.print(Panel(Markdown(reply), border_style="blue"))
