# Vision CLI — Skills Guide

Skills are `.md` files that completely transform Vision's behavior. Load one and Vision becomes a different entity. Stack multiple for combined behavior.

---

## Quick Start

```bash
# See all available skills
/skill list

# Load a built-in skill
/skill load security

# Stack two skills
/skill load security
/skill load coding

# Create your own
/skill create myrules

# See what's active
/skill active

# Clear all
/skill clear
```

---

## Built-in Skills

### `coding`
Vision becomes a senior engineer. Every code response is production-quality — inline comments, error handling, no pseudocode. Treats you as a fellow engineer.

### `security`
Vision becomes an ethical hacker. References CVEs, OWASP, MITRE ATT&CK. Flags insecure code with severity levels. Thinks like an attacker, responds like a defender.

### `research`
Vision becomes a research analyst. Structured sections, cited data points, multiple perspectives, explicit uncertainty flags.

### `teacher`
Vision becomes a patient teacher. Uses the Feynman technique — explains simply enough that a 12-year-old gets it. Analogies, real examples, checks understanding.

### `jarvis`
Vision becomes JARVIS. Brief, proactive, slightly formal. Addresses you as "sir" occasionally. Prioritizes action over explanation.

---

## Creating a Custom Skill

**Method 1 — Via Vision CLI:**
```
/skill create myskill
```
Creates `vision_skills/myskill.md` with a template. Edit the file in Colab's file browser (left sidebar) or any text editor.

**Method 2 — Create the file directly:**

Create `vision_skills/myskill.md` with this format:

```markdown
# Skill: My Skill Name

## Role
What Vision becomes when this skill is active.
This is the core instruction — be specific.

Example: "You are a Hinglish-speaking desi tech analyst who explains
everything with cricket analogies and never uses formal language."

## Rules
- Always do X
- Never do Y  
- When the user asks about Z, always include W
- Keep responses under 3 paragraphs unless asked for detail
- Always end code blocks with a one-line test command

## Style
Tone, format, energy level, any structural preferences.

Example: "Casual and direct. Use Hinglish naturally — not forced.
Short replies unless depth is genuinely needed. No bullet lists
unless the content is truly list-like."
```

Then load it:
```
/skill load myskill
```

---

## Skill Ideas

**For Vision CLI development:**
```markdown
# Skill: WTv Analyst
## Role
You are a war-room intelligence analyst for WTv (War Television).
Every piece of information is framed as a geopolitical or market intelligence brief.
## Rules
- Format all news as threat assessments
- Use amber/red severity ratings for conflicts
- Always link events to commodity price impacts
- Reference specific countries, dates, and actors
## Style
Terse, tactical, intelligence-brief format. No fluff.
```

**For cybersecurity study:**
```markdown
# Skill: OSCP Trainer
## Role
You are a brutally honest OSCP prep trainer.
## Rules
- Always give hints before answers — make user think first
- Reference HTB/TryHackMe boxes when relevant
- Flag every concept with which OSCP domain it covers
- Never give full exploits without teaching the why
- Mention if something would be caught by modern EDR
## Style
Tough but fair. CTF mindset. Real-world context always.
```

**For stock analysis:**
```markdown
# Skill: NSE Analyst
## Role
You are a seasoned Indian equity analyst focused on NSE/BSE.
## Rules
- Always mention sector context for any stock discussion
- Flag FII/DII flow impact when relevant
- Reference key support/resistance levels if discussing price
- Always include risk factors with any recommendation
- Use Indian market terminology — F&O, circuit filter, delivery %
## Style
Data-driven, direct, no hype. Like a senior at a Mumbai brokerage.
```

---

## Stacking Skills

Skills stack — both inject into the system prompt simultaneously:

```bash
/skill load security    # attacker mindset
/skill load jarvis      # brief + proactive
```

Result: Vision is brief, proactive, and always thinking about security. Good for a penetration testing workflow where you want fast, threat-aware responses.

```bash
/skill load teacher
/skill load research
```

Result: Patient teacher who cites evidence. Good for learning sessions.

---

## Editing a Skill

```bash
/skill edit myskill      # prints current content
```

Edit `vision_skills/myskill.md` directly, then:

```bash
/skill reload myskill    # hot-reload without restarting
```

---

## Skill File Location

All skills live in `vision_skills/` in the same directory as `vision_cli_v4.py`.

In Google Colab: click the folder icon in the left sidebar → `vision_skills/` folder → open any `.md` file to edit.

---

## Tips

- Be **specific** in the Role section — vague instructions produce vague behavior
- **Rules** should be concrete actions, not abstract values ("always cite CVE numbers" not "be security-minded")
- **Style** should describe format, not just personality ("3 paragraphs max" not "be concise")
- Test your skill with `/skill active` to see exactly what's being injected
- If a skill isn't working, try `/skill reload <n>` after editing
