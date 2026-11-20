"""Message understanding: sensitive-message detection, guardrails, intent and slot extraction.

Deterministic regexes run first and always win. The optional LLM (llm.py) is consulted only when no
intent matched, and it can only pick a label from INTENTS — it never writes the answer.
"""
from __future__ import annotations

import re

from .policy import KNOWN_CITIES

# ------------------------------------------------------------------ sensitive messages
POSH_RE = re.compile(
    r"harass|sexual|molest|grop(e|ed|ing)|unwelcome (advance|touch|comment|message)|stalk|lewd|indecent|obscene|"
    r"eve[- ]?teas|touch(ed|es|ing)? me|inappropriate(ly)? (touch|comment|message|text|photo|joke|advance|behaviou?r|remark)|"
    r"quid pro quo|sexist remark|making me uncomfortable|blackmail")
WORKPLACE_RE = re.compile(r"\bbull(y|ied|ying)\b|abusive|abusing me|threaten|discriminat|humiliat|shout(s|ed|ing)? at me|toxic (manager|boss)")
CRISIS_RE = re.compile(
    r"suicid|kill (my ?self|myself)|end (my|it) (life|all)|end it all|want to die|wanna die|don'?t want to (live|be alive)|"
    r"no reason to live|self[- ]?harm|harm(ing)? myself|hurt(ing)? myself|cut(ting)? myself|better off dead|"
    r"not worth living|jaan de")
DISTRESS_RE = re.compile(
    r"depress|anxiety|anxious|panic attack|hopeless|helpless|worthless|can'?t cope|cannot cope|unable to cope|"
    r"overwhelm|burn(ed|t)[- ]?out|burnout|breakdown|mentally (exhausted|drained|broken)|so stressed|very stressed|"
    r"extremely stressed|too much stress|lonely|crying|can'?t sleep|cannot sleep|insomnia|"
    r"struggling (mentally|emotionally|to cope)|feel(ing)? (so |very |really )?(low|down|terrible|awful|empty|numb|lost)|"
    r"falling apart|bahut pareshan|tension (hai|ho rahi)")
EXIT_RE = re.compile(
    r"resign|\bquit(ting)?\b|(leave|leaving|left) (the |this )?(company|kavach|organi[sz]ation|job|firm)|"
    r"put (in|down) my papers|serv(e|ing) (my )?notice|last working day|another (job|offer|company)|new (job|offer)|"
    r"job offer|got an offer|switch(ing)? (jobs?|compan)|moving on from|buy[- ]?out|istifa|naukri chhod|job chhod|"
    r"relieving letter|exit interview")

# ------------------------------------------------------------------ guardrails
INJECTION_RE = re.compile(
    r"ignore (all |any |the |your |previous |prior |above |these |those )*(rules|instructions|policy|policies|guidelines|prompt)|"
    r"disregard .{0,30}(rules|instructions|policy)|forget (all |your )?(rules|instructions)|system prompt|"
    r"you are now|developer mode|jailbreak|pretend (to be|you are|you're)|act as (an? |the )?(admin|hr|hrbp|developer|system)|"
    r"\boverride\b|bypass|reveal (your|the) (prompt|instructions|rules)|do anything now|new instructions|"
    r"i am (the |an )?(admin|hr head|chro|hrbp|ceo)|as an admin")
PRIVACY_GENERIC_RE = re.compile(
    r"(colleague|co-?worker|team ?mate|manager|boss|someone else|other employees?|another employee|everyone|"
    r"all employees|him|her|his|their)('s|s')?\s+(salary|ctc|pay|phone|mobile|number|email|address|band|grade|"
    r"details|record|probation|leave balance|contact|data|joining date|doj)|"
    r"(list|show|give|share|send|dump|export|print).{0,30}(all|other|every|the) (employees?|staff|roster|records)|"
    r"\broster\b|employee (list|database|records)")
EMP_ID_RE = re.compile(r"\bkv\s?-?\d{4}\b", re.I)

# ------------------------------------------------------------------ topics the pack does not cover
UNSUPPORTED = [
    (r"\bgym\b|fitness", "gym or fitness reimbursement"), (r"salary|\bctc\b|pay ?slip|payslip|increment|hike|appraisal|bonus",
     "salary, payslips, increments or bonuses"), (r"insurance|mediclaim|health cover", "employee insurance cover"),
    (r"\bloan\b|advance salary|salary advance", "loans or salary advances"), (r"esop|stock option", "ESOPs"),
    (r"relocat", "relocation"), (r"laptop|device|\bphone bill|mobile bill|internet bill|broadband", "devices or phone/internet bills"),
    (r"referral", "referral bonuses"), (r"holiday list|public holiday|festival|\bholidays?\b", "public holidays"),
    (r"\bpf\b|provident|gratuity|\btax\b|tds|form 16", "PF, gratuity or tax"), (r"promotion", "promotions"),
    (r"\btransfer\b", "transfers"), (r"overtime|comp[- ]?off|compensatory", "overtime or comp-off"),
    (r"sabbatical", "sabbaticals"), (r"marriage leave|wedding leave", "marriage leave"),
    (r"birthday", "birthday leave"), (r"dress code", "dress code"), (r"parking|canteen|cafeteria|shuttle", "office facilities"),
    (r"\bcabs?\b|\btaxi|\buber\b|\bola\b|auto ?rickshaw", "cab/taxi fares (§3.4 only covers your own car or two-wheeler)"), (r"leave without pay|\blwp\b|unpaid leave", "leave without pay"),
    (r"work from abroad|work abroad|international travel|abroad|overseas|visa", "international travel or working abroad"),
    (r"shift allowance|night shift", "shift allowances"), (r"notice period.{0,20}waive|waive", "notice waivers"),
    (r"moonlight|side job|second job|freelanc", "outside employment"), (r"training|certification|course fee", "training or certification support"),
]
UNSUPPORTED = [(re.compile(p), label) for p, label in UNSUPPORTED]

# ------------------------------------------------------------------ intents, most specific first
_LEAVE = r"\b(leaves?|chh?utti|chhuttiyan)\b(?!\s+(the |this )?(company|kavach|organi[sz]ation|job|firm))"
INTENT_PATTERNS = [
    ("maternity", r"maternity|pregnan"),
    ("paternity", r"paternity|became a (father|dad)|wife.{0,20}(deliver|baby)|newborn|new born"),
    ("bereavement", r"bereavement|passed away|death in (the|my) family|funeral|died|demise"),
    ("sick_leave", r"\bsick\b|\bcl\b|\bsl\b|cl/sl|casual leave|medical certificate|unwell|fever|\bill\b"),
    ("earned_leave", r"\bel\b|earned leave|privilege leave|\bpl\b|carry[- ]?forward|carry over|encash|lapse"),
    ("leave_apply", r"(apply|request|raise|approv).{0,25}" + _LEAVE + "|" + _LEAVE + r".{0,25}(apply|request|approv)"),
    ("regularisation", r"regulari[sz]|missed (a )?punch|forgot to punch|missing punch|attendance correction"),
    ("late_marks", r"\blate\b|late mark|late coming"),
    ("wfh", r"\bwfh\b|work(ing)? from home|remote(ly)? work|work remotely|home office"),
    ("working_hours", r"working hours|office hours|office timings?|work timings?|work hours|what time.{0,20}(start|office)|attendance"),
    ("hotel", r"hotel|accommodation|lodging|per night|room rent|\bstay\b"),
    ("daily_allowance", r"daily allowance|\bda\b|per diem|food allowance|meal allowance|incidentals?"),
    ("conveyance", r"conveyance|own (vehicle|car|bike)|two[- ]?wheeler|\bbike\b|scooter|mileage|per km|fuel|petrol|drove|drive my"),
    ("travel_mode", r"\bfly\b|flight|air ?travel|by air|\btrain\b|3ac|premium economy|economy|mode of travel|travel class|airfare"),
    ("travel_general", r"travel (allowance|policy|entitlements?|rules|benefits)|business trip|official trip|work trip"),
    ("claims", r"\bclaims?\b|reimburs|expenses?|\bbills?\b|receipts?"),
    ("buyout", r"buy[- ]?out|shorten.{0,20}notice|early release|reduce.{0,20}notice"),
    ("fnf", r"full and final|f ?& ?f|\bfnf\b|final settlement|\bsettlement\b"),
    ("notice", r"\bnotice\b"),
    ("resign_how", r"resign"),
    ("posh_info", r"\bposh\b|internal committee|\bic\b"),
    ("eap_info", r"\beap\b|employee assistance|counsel|mann sahayak|therap"),
    ("leave_general", _LEAVE + r"|time off|days? off|vacation"),
    ("probation_info", r"probation|confirmation|confirmed"),
    ("contacts", r"payroll|helpdesk|help desk|contact|hrbp|hr business partner|who (do|should) i (ask|talk|email)"),
    ("profile", r"my (band|grade|role|details|profile|designation)|who am i"),
]
INTENT_PATTERNS = [(i, re.compile(p)) for i, p in INTENT_PATTERNS]
INTENTS = [i for i, _ in INTENT_PATTERNS]
GENERIC = {"leave_general": {"sick_leave", "earned_leave", "maternity", "paternity", "bereavement", "leave_apply"},
           "claims": {"hotel", "daily_allowance", "conveyance", "travel_mode", "travel_general"},
           "travel_general": {"hotel", "daily_allowance", "conveyance", "travel_mode"},
           "probation_info": set(INTENTS) - {"probation_info"},
           "notice": {"buyout"}, "contacts": set(INTENTS) - {"contacts"}}

# Slot-only follow-ups: which intents a bare slot can continue
SLOT_INTENTS = {"city": {"hotel"}, "distance_km": {"travel_mode", "conveyance"}, "flight_hours": {"travel_mode"},
                "count": {"late_marks"}, "days": {"claims"}}

_CITY_RE = re.compile(r"\b(" + "|".join(sorted(map(re.escape, KNOWN_CITIES), key=len, reverse=True)) + r")\b")


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("’", "'").lower()).strip()


def detect_sensitive(t: str) -> list[str]:
    flags = []
    if CRISIS_RE.search(t):
        flags.append("DISTRESS_CRISIS")
    elif DISTRESS_RE.search(t):
        flags.append("DISTRESS")
    if POSH_RE.search(t):
        flags.append("POSH")
    elif WORKPLACE_RE.search(t):
        flags.append("WORKPLACE_CONCERN")
    if EXIT_RE.search(t):
        flags.append("EXIT_INTENT")
    return flags


def detect_intents(t: str) -> list[str]:
    hits = [i for i, rx in INTENT_PATTERNS if rx.search(t)]
    hits = [i for i in hits if not (GENERIC.get(i, set()) & set(hits))]
    return hits[:3]


def unsupported_topics(t: str) -> list[str]:
    return [label for rx, label in UNSUPPORTED if rx.search(t)]


def find_cities(t: str) -> list[tuple[int, str]]:
    return [(m.start(), KNOWN_CITIES[m.group(1)]) for m in _CITY_RE.finditer(t)]


def destination_city(t: str) -> str | None:
    """Hotel limits use the destination city: prefer 'to X' / 'in X'; ignore a lone 'from X'."""
    cities = find_cities(t)
    if not cities:
        return None
    for pos, name in cities:
        if re.search(r"\b(to|in|at|for|visiting|towards)\s+$", t[max(0, pos - 12):pos]):
            return name
    non_origin = [n for p, n in cities if not re.search(r"\bfrom\s+$", t[max(0, p - 6):p])]
    return non_origin[-1] if non_origin else None


def extract_slots(t: str) -> dict:
    s: dict = {}
    if (c := destination_city(t)):
        s["city"] = c
        others = list(dict.fromkeys(n for p, n in find_cities(t) if not re.search(r"\bfrom\s+$", t[max(0, p - 6):p])))
        if len(others) > 1:
            s["cities"] = others  # "hotel limit for Pune and Lucknow?"
    if (m := re.search(r"(\d[\d,]*(?:\.\d+)?)\s*(km|kms|kilomet)", t)):
        s["distance_km"] = float(m.group(1).replace(",", ""))
    if (m := re.search(r"(\d+(?:\.\d+)?)\s*[- ]?(hours?|hrs?|h)\b", t)):
        s["flight_hours"] = float(m.group(1))
    if (m := re.search(r"(\d+)\s*(late marks?|times late|lates)\b|late (\d+) times", t)):
        s["count"] = int(m.group(1) or m.group(3))
    if (m := re.search(r"(\d+)\s*days?\s*(after|since|ago|later|old)", t)):
        s["days"] = int(m.group(1))
    if re.search(r"\bcar\b", t):
        s["vehicle"] = "car"
    elif re.search(r"two[- ]?wheeler|\bbike\b|scooter|motorcycle", t):
        s["vehicle"] = "two-wheeler"
    return s


def parse_band(t: str) -> str | None:
    if re.search(r"\bintern\b", t):
        return "Intern"
    m = re.search(r"\bband\s*([ams])\d?\b|^\s*([ams])\s*[123]?\s*\.?$|\b([ams])[123]\b|^\s*band\s*-?\s*([ams])", t)
    return next((g.upper() for g in m.groups() if g), None) if m else None


def parse_probation(t: str) -> str | None:
    if re.search(r"probation|not (yet )?confirmed|new joiner", t):
        return "On probation"
    if re.search(r"confirm|permanent", t):
        return "Confirmed"
    return None


def parse_role(t: str) -> str | None:
    if re.search(r"field|sales", t):
        return "Field Sales"
    if re.search(r"corporate|office", t):
        return "Corporate"
    return None
