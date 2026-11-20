# Design note: Kavach HR Policy Assistant

**What it is.** A Streamlit chat backed by a deterministic Python policy engine. The 7-section pack is short and
mostly lookup tables, so I hand-coded each rule as a function (band × role × probation × city). I didn't build
retrieval or a vector DB. At startup the code checks 47 exact strings from the source Markdown, so a value can't
drift from the pack without the app refusing to start.

## How it decides: answer, ask, or "I don't know"
1. **Identity.** The Employee ID is looked up in the roster (band, role type, probation as of 15 Nov 2026, city,
   HRBP). If the ID isn't found, the user continues as a guest and is asked for whatever an answer needs (band,
   probation status or role type).
2. **Safety checks run first:** sensitive-message detection, then prompt-injection and other-employee privacy checks.
3. **Intent and slots.** Ordered regexes find the topic (about 26 topics) and slots (destination city, km, flight
   hours, late-mark count, days since a trip). Rules apply in order: intern exceptions first, then probation, then
   role type (e.g. Field Sales has no WFH), then band.
4. **Ask.** If a required input is missing (city for hotel, km for a Band A flight, band for a guest), the bot asks
   one short question and keeps it pending. The next message fills it. Short follow-ups such as "and for Pune?" or
   "what about 600 km?" reuse the last topic and slots.
5. **"I don't know".** It says this when no topic matches, a known uncovered topic is named (gym, salary, holidays,
   taxis…), or a rule doesn't cover the person (interns have no WFH or travel rows). The reply names the HRBP and
   their email. Partly covered questions get the covered part answered and the rest called out.
6. Every answer cites its sections. It never confuses entitlement with balance ("I can't see what's left; check
   PeopleHub").

## Sensitive messages: detection and what happens next
Keyword and regex patterns detect three things (no model needed, so it works offline):

- **POSH:** the bot shares the IC route (ic@kavach.example, 3 months plus up to 3 more, confidentiality, no
  retaliation, HRBP support). It gives no judgement or advice. A HIGH alert goes to the IC, with the HRBP named for
  support. The disclosure text is **withheld from the logs**, because the bot is not a complaint channel and
  shouldn't spread allegations.
- **Distress:** a caring reply with the EAP contact and an URGENT HRBP alert. Self-harm language also adds the §6.2
  emergency guidance.
- **Exit intent:** the bot answers the factual question and raises a MEDIUM HRBP flag. A plain notice-period
  question raises no flag.
- Bullying-type concerns get a HIGH HRBP flag (the pack has no process for them) and a pointer to the IC.

**What could go wrong:** keywords miss indirect phrasing ("I don't see the point any more") and over-trigger on
some words. The optional LLM can only add a sensitive route, never remove one. Regex can't read sarcasm or
third-person reports. There's no real authentication: the Employee ID is a stand-in, so anyone can type any ID.
Alerts sit in a CSV with no notifications, so an urgent flag is only as fast as someone reading it.

## Ambiguities in the pack (noted, not resolved by guessing)
- *Delhi NCR* lists only Delhi, Gurugram and Noida. Faridabad, Ghaziabad, Greater Noida, Thane, Navi Mumbai and
  Secunderabad get both limits and are referred to the HRBP.
- Interns have no WFH, hotel, DA or travel-mode rows, so the bot says "I don't know" and points to the HRBP. §1.3
  says "all bands", but §1.5 ("no other leave type applies to interns") wins.
- §2.2 deducts late marks from EL first, yet probationers can't use EL (§1.4). It's also unclear how the 9:45
  cut-off applies to Field Sales geo-punches. The bot flags the latter.
- Notice buy-out has no formula. Premium economy is defined only for Band S, so "business class" isn't covered.
- Probation status is taken from the roster as of 15 Nov 2026. It's consistent with the 6-month rule (KV1019 was
  confirmed 10 days before that date). Intern leave earned is calculated as of the same date.

## What I chose not to build
WhatsApp or Telegram (the channel doesn't matter for the brief). RAG or a vector DB (a short pack where exact
numbers matter). LLM-written answers (to avoid invented numbers). Google Sheets (CSV needs no credentials).
Hindi/Hinglish replies (there are only a few Hinglish keywords). Real SSO, multi-question splitting beyond 3
topics, and alert email or Slack notifications.

## What breaks first at 3,000 users on day one, and fixes
1. **CSV logging:** one process-wide lock, a whole-file rewrite on "resolve", no concurrent multi-instance writes.
   Fix: Postgres or Google Sheets API with append-only rows.
2. **Unanswered urgent alerts:** fix with email, Slack or pager notifications per priority, an SLA, and an
   on-call HRBP.
3. **Identity:** fix with SSO and an HRMS (PeopleHub) API instead of a static CSV, plus role-based access to the
   HRBP view.
4. **Phrasing coverage:** fix by reviewing `topic=unknown` rows weekly, adding patterns, and turning on the LLM
   fallback. Streamlit holds sessions in memory, so it needs a few replicas behind a load balancer.

## Rough running cost per 1,000 questions
The deterministic path costs **$0** in model fees, only hosting (a small VM, about $10–30/month). With the LLM
fallback on, assume about 30% of messages reach it, at about 700 input and about 300 output tokens each (low
effort, JSON only):

- **Claude Opus 5.5** ($4/$20 per MTok): about $0.009 per call, so about **$3 per 1,000 questions**.
- **Claude Haiku 5.5** ($0.10/$0.50): about **$0.07 per 1,000**.

The profile is never sent to the model, only the message text.

## AI-tool disclosure
I built this with Claude Code (Anthropic) as a coding assistant. It read the brief and the pack, proposed the
structure, wrote the code, tests and docs, and ran them. I reviewed every policy value against the pack, and the
startup anchor check enforces them. Both the tests and the six-sample run were executed, and their outputs are in
`results/`.
