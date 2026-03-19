# Contributing to Vision CLI

Thanks for being here. Vision CLI is solo-built and every contribution matters.

---

## Open Issues — Claim One

| Issue | Difficulty | What's needed |
|-------|-----------|---------------|
| Wake word detection | Hard | Background mic thread, hotword model |
| Flutter mobile app | Hard | Cross-device sync |
| Self-healing code runner | Medium | Auto-debug + retry on `/runfile` errors |
---

## How to Add a New Provider

Most AI providers use OpenAI-compatible API. Adding one = ~15 lines.

**Step 1 — Add to `select_provider()`:**
```python
("11", "NewProvider", "Description"),
```

**Step 2 — Add to `setup_provider()`:**
```python
elif provider == "11":
    key = os.environ.get("NEWPROVIDER_API_KEY") or input("NewProvider key: ").strip()
    return OpenAI(base_url="https://api.newprovider.com/v1", api_key=key), "NewProvider"
```

**Step 3 — Add suggested models list:**
```python
NEWPROVIDER_SUGGESTED = [
    ("model-id-1", "Model Name 1 — description"),
]
```

**Step 4 — Wire into `_get_suggested()`:**
```python
"NewProvider": (NEWPROVIDER_SUGGESTED, "docs.newprovider.com/models"),
```

Done. Model selector, validation, council, skills — all work automatically.

---

## How to Add a New Integration

```python
# Setup
def myservice_setup():
    token = os.environ.get("MYSERVICE_TOKEN") or input("Token: ").strip()
    data["myservice_token"] = token
    save_data()
    console.print("[green]✓ Configured[/green]")

# Send
def myservice_send(message):
    token = data.get("myservice_token")
    if not token:
        console.print("[yellow]Run /myservicesetup first[/yellow]"); return False
    try:
        r = requests.post("https://api.myservice.com/send",
                          json={"token": token, "message": message}, timeout=10)
        if r.status_code == 200:
            console.print("[green]✓ Sent[/green]"); return True
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]"); return False
```

**Wire into main loop:**
```python
elif user == "/myservicesetup":       myservice_setup()
elif user.startswith("/myservice "): myservice_send(user[13:].strip())
```

**Add to `show_help()`** and **`_execute_automation()`** for scheduler support.

See [INTEGRATIONS.md](INTEGRATIONS.md) for full working examples.

---

## How to Add a New Command

1. Write the function — Rich output, try/except, `save_data()` if it persists anything
2. Add `elif user.startswith("/yourcommand"):` in the main loop
3. Add to `show_help()` in the right section
4. Add to `_track_usage()` if worth tracking
5. Update CHANGELOG.md

---

## How to Add a Built-in Skill

Add to `_DEFAULT_SKILLS` dict in the storage section:

```python
"myskill.md": """# Skill: My Skill
## Role
What Vision becomes.
## Rules
- Rule 1
## Style
Tone description.""",
```

---

## Code Standards

- Rich for all output — `console.print()`, `Panel()`, `Table()`, `Markdown()`
- `try/except` around all external calls — never crash the main loop
- `save_data()` whenever modifying `memory`, `goals`, `portfolio`, `automations`
- `rate_limit(model)` before every `client.chat.completions.create()`
- `_track_usage("command", content)` for commands worth tracking
- No hardcoded API keys — `os.environ.get()` + `input()` fallback

---

## PR Checklist

- [ ] Works end-to-end (tested in Colab or local)
- [ ] No crashes on failure
- [ ] Added to `show_help()`
- [ ] Added to CHANGELOG.md
- [ ] No hardcoded secrets
- [ ] Follows `save_data()` / `load_data()` pattern if storing anything
