# Submission checklist

## Brief must-haves
- [x] Know who is asking: roster lookup by Employee ID; guest flow for unknown IDs (`hr_bot/bot.py` `login`)
- [x] Answer from the policy pack only, citing sections in every answer (startup anchor check in `store.load_policy`)
- [x] Personalised by band, role type, probation, city and intern status (`hr_bot/policy.py`)
- [x] Asks one follow-up when an input is missing: city, km, band, probation status, role (sample S4 and tests)
- [x] "I don't know" plus HRBP name and email (sample S5); partial coverage handled
- [x] POSH → IC route plus alert; exit → answer plus HRBP flag; distress → EAP plus urgent alert
- [x] Logs every message, reply and flag with timestamp, employee ID, topic and flag type (`logs/*.csv`)
- [x] Conversation memory ("and for Pune?")

## Nice-to-haves done
- [x] HRBP view (sidebar → HRBP flag review), with filter by HRBP and status and a resolve button
- [x] Automated sample run with a pass/fail score (`scripts/run_samples.py`, 6/6)
- [x] Cost estimate (design note)
- [x] Prompt-injection and other-employee privacy guards
- [ ] Hindi/Hinglish replies (only a few Hinglish keywords are understood)

## To send
- [x] Demo video, 4:58, my own voiceover: `demo/Kavach_HR_Assistant_Demo.mp4` (script in `docs/DEMO_VOICEOVER.md`)
- [x] GitHub repo with README (`.env`, `.venv/`, `.claude/` excluded)
- [x] Log sample: `logs/messages.csv` and `logs/alerts.csv`, written fresh by the demo recording
- [x] Design note: `docs/DESIGN_NOTE.pdf` (one page)
- [x] Six-question results: `results/sample_results.md`
- [ ] Reply to the assignment email with the links

## Before pushing
- [x] A fresh clone of the GitHub repo installs from `requirements.txt`, passes 73 tests, scores 6/6 and starts the app
- [x] `python -m pytest` passes (73 tests)
- [x] `python scripts/run_samples.py` prints 6/6 (note: running it appends to `logs/`)
- [x] No API keys in code, logs or video
- [x] The original brief PDF and ZIP are unchanged; they are kept out of the repo, and `data/` holds the extracted attachments
