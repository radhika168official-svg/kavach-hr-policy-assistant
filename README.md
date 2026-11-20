# Kavach HR Policy Assistant (prototype)

A chat assistant that answers Kavach Insurtech employees' HR policy questions **only from the supplied policy pack**,
personalised to the employee's band, role type, probation status and city. It asks a follow-up when an input is
missing, says "I don't know" (with the employee's HRBP) when the pack is silent, routes POSH / distress / exit
messages to a human, and logs every message and alert to CSV. All data is fictional.

**Design in one line:** policy numbers and eligibility live in plain Python functions (`hr_bot/policy.py`) checked
against the source Markdown at startup. An LLM is optional and only picks an intent label when the keyword matcher
can't. It never writes an answer.

## Run it locally (Windows / macOS / Linux)

Needs Python 3.11 or newer (tested on 3.12.7). On Windows, if `python --version` shows an older version, use the
launcher: `py -3.12 -m venv .venv`.

```bash
python -m venv .venv
```

Activate the venv. Windows PowerShell: `.venv\Scripts\Activate.ps1`. macOS/Linux: `source .venv/bin/activate`.

```bash
pip install -r requirements.txt
```

```bash
streamlit run app.py
```

Open **http://localhost:8501**. Enter an Employee ID from `data/Kavach_Employee_Roster.csv` (for example `KV1001`)
in the sidebar, or click *Continue without an ID*. Switch to **HRBP flag review** in the sidebar to see alerts.

### Tests and sample questions

```bash
python -m pytest -v
```

```bash
python scripts/run_samples.py
```

`run_samples.py` runs the six supplied questions plus the demo scenarios through the real bot. It writes
`results/sample_results.md` and appends to `logs/messages.csv` and `logs/alerts.csv`. Tests write to a temporary
folder, so they never touch `logs/`.

### Optional LLM intent fallback

The app works fully without an LLM. To let Claude classify messages the keyword matcher misses, set these in your
shell before `streamlit run` (see `.env.example`; the app reads the environment, not a `.env` file):

```powershell
$env:HR_BOT_USE_LLM = "1"; $env:ANTHROPIC_API_KEY = "<your key>"
```

Optional: `HRBP_VIEW_PASSCODE` puts a passcode on the HRBP page.

## Project layout

```
app.py                 Streamlit UI: employee chat + HRBP flag review
hr_bot/policy.py       Policy values (transcribed from the pack) + one deterministic answer function per topic
hr_bot/nlu.py          Regex detection: sensitive messages, injection, privacy, intents, slots (city, km, hours)
hr_bot/bot.py          Conversation: identity, guardrails, follow-ups/memory, reply + citation, logging, alerts
hr_bot/llm.py          Optional Claude intent fallback (structured JSON, validated, fails closed)
hr_bot/store.py        Roster loader, policy-pack integrity check, CSV logs
tests/test_bot.py      73 pytest tests (samples, bands, probation, interns, WFH, tiers, follow-ups, sensitive, guardrails, logs)
scripts/run_samples.py Six sample questions with a pass/fail score, plus the demo scenarios
data/                  Extracted assignment attachments (unchanged)
logs/                  messages.csv, alerts.csv written by real runs
results/               sample_results.md (actual bot answers), test_results.txt (actual pytest output)
docs/                  DESIGN_NOTE.md / DESIGN_NOTE.pdf (one page), DEMO_SCRIPT.md, SUBMISSION_CHECKLIST.md
demo/                  Kavach_HR_Assistant_Demo.mp4 (3:10 screen recording; logs/ was written by this run)
```

## Logs

`logs/messages.csv` holds one row per user message and per bot reply: `timestamp, session_id, employee_id, role,
message, topic, flag_type, policy_refs, hrbp_name, hrbp_email`.
`logs/alerts.csv` holds one row per flag: `alert_id, timestamp, session_id, employee_id, flag_type, priority, topic,
routed_to, hrbp_name, hrbp_email, summary, status`.
The text of a POSH disclosure is withheld from both files, and the alert records only that a concern was raised.

## Assumptions

See `docs/DESIGN_NOTE.md` for the full list, including where the policy pack is ambiguous.
