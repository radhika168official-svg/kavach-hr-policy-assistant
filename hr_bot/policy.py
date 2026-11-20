"""Deterministic policy engine.

Every number here is transcribed from data/Kavach_HR_Policy_Pack.md (v3.2).
`POLICY_ANCHORS` lists the exact source strings each value came from; `data.load_policy()`
refuses to start if any anchor is missing, so the code and the pack cannot silently drift.
"""
from __future__ import annotations

import calendar
from dataclasses import dataclass, field
from datetime import date

AS_OF = date(2026, 11, 15)  # roster probation status is "as of 15 Nov 2026" (assignment brief)

SECTIONS = {
    "about": "About this pack (Bands, Probation, City tiers)",
    "1.1": "Leave Policy §1.1 Leave year",
    "1.2": "Leave Policy §1.2 Earned Leave",
    "1.3": "Leave Policy §1.3 Casual and Sick Leave",
    "1.4": "Leave Policy §1.4 Leave during probation",
    "1.5": "Leave Policy §1.5 Interns",
    "1.6": "Leave Policy §1.6 Maternity Leave",
    "1.7": "Leave Policy §1.7 Paternity Leave",
    "1.8": "Leave Policy §1.8 Bereavement Leave",
    "1.9": "Leave Policy §1.9 How to apply",
    "2.1": "Attendance & WFH §2.1 Working hours",
    "2.2": "Attendance & WFH §2.2 Late marks",
    "2.3": "Attendance & WFH §2.3 Missed punch / regularisation",
    "2.4": "Attendance & WFH §2.4 Work From Home",
    "3.1": "Travel & Reimbursement §3.1 Hotel limit per night",
    "3.2": "Travel & Reimbursement §3.2 Daily allowance",
    "3.3": "Travel & Reimbursement §3.3 Mode of travel",
    "3.4": "Travel & Reimbursement §3.4 Local conveyance",
    "3.5": "Travel & Reimbursement §3.5 Submitting claims",
    "4.2": "POSH §4.2 Internal Committee",
    "4.3": "POSH §4.3 Timeline",
    "4.4": "POSH §4.4 Confidentiality and no retaliation",
    "4.5": "POSH §4.5 HRBP support",
    "5.1": "Separation §5.1 Notice period",
    "5.2": "Separation §5.2 How to resign",
    "5.3": "Separation §5.3 Notice buy-out",
    "5.4": "Separation §5.4 Full and Final settlement",
    "6.1": "Wellbeing §6.1 Employee Assistance Programme",
    "6.2": "Wellbeing §6.2 Emergency",
    "7": "Contacts §7",
}

EL = {"A": (18, 30), "M": (21, 30), "S": (24, 45)}  # (days per year, max carry-forward)
EL_ENCASH_MAX = 30
CLSL_DAYS = 12
WFH = {"A": "up to 2 days per month, with manager approval",
       "M": "up to 4 days per month, with manager approval",
       "S": "flexible, as agreed with your reporting manager"}
HOTEL = {"A": (3500, 2500), "M": (5500, 4000), "S": (8000, 6000)}  # (Tier 1, Tier 2/3)
DA = {"A": 600, "M": 900, "S": 1200}
NOTICE = {"A": 30, "M": 60, "S": 90}
NOTICE_PROBATION, NOTICE_INTERN = 15, 7
CAR_PER_KM, TWO_WHEELER_PER_KM = 12, 5
IC_EMAIL, HELPDESK, PAYROLL = "ic@kavach.example", "hr.help@kavach.example", "payroll@kavach.example"
EAP = "Mann Sahayak (fictional EAP partner): 1800-000-4357 or eap@kavach.example"

TIER1 = {  # alias -> canonical name. Pack: Mumbai, Delhi NCR (Delhi, Gurugram, Noida), Bengaluru, Hyderabad, Chennai, Kolkata, Pune
    "mumbai": "Mumbai", "bombay": "Mumbai", "delhi": "Delhi", "new delhi": "Delhi", "delhi ncr": "Delhi NCR",
    "gurugram": "Gurugram", "gurgaon": "Gurugram", "noida": "Noida", "bengaluru": "Bengaluru",
    "bangalore": "Bengaluru", "hyderabad": "Hyderabad", "chennai": "Chennai", "madras": "Chennai",
    "kolkata": "Kolkata", "calcutta": "Kolkata", "pune": "Pune",
}
# Commonly treated as part of a Tier-1 metro, but NOT named in the pack's Tier-1 list -> never guess.
AMBIGUOUS_CITIES = {"faridabad": "Faridabad", "ghaziabad": "Ghaziabad", "greater noida": "Greater Noida",
                    "thane": "Thane", "navi mumbai": "Navi Mumbai", "secunderabad": "Secunderabad"}
OTHER_CITIES = [
    "Indore", "Lucknow", "Jaipur", "Chandigarh", "Ahmedabad", "Patna", "Kanpur", "Kochi", "Cochin", "Bhopal",
    "Nagpur", "Coimbatore", "Surat", "Vadodara", "Nashik", "Goa", "Panaji", "Visakhapatnam", "Vizag",
    "Bhubaneswar", "Guwahati", "Dehradun", "Ranchi", "Raipur", "Ludhiana", "Amritsar", "Agra", "Varanasi",
    "Mysuru", "Mysore", "Mangaluru", "Mangalore", "Madurai", "Tiruchirappalli", "Trichy", "Thiruvananthapuram",
    "Trivandrum", "Jodhpur", "Udaipur", "Shimla", "Srinagar", "Jammu", "Gwalior", "Jabalpur", "Aurangabad",
    "Rajkot", "Meerut", "Prayagraj", "Allahabad", "Vijayawada", "Kozhikode", "Siliguri", "Jamshedpur",
]
KNOWN_CITIES = {**TIER1, **AMBIGUOUS_CITIES, **{c.lower(): c for c in OTHER_CITIES}}

POLICY_ANCHORS = [  # exact strings in the Markdown pack that back the constants above
    "| A | 18 days | 30 days |", "| M | 21 days | 30 days |", "| S | 24 days | 45 days |",
    "up to a maximum of 30 days", "**12 days of CL/SL combined**", "**more than 2 consecutive days**",
    "can **use EL only after confirmation**", "**1 day of leave per completed month**",
    "26 weeks of paid leave for the first two children; 12 weeks from the third child onwards",
    "5 working days, to be taken within 3 months", "3 working days on the death of an immediate family member",
    "within 3 working days", "9:30 AM to 6:30 PM, Monday to Friday", "after **9:45 AM**",
    "**3 late marks per calendar month**", "**half-day deduction**", "within **5 calendar days**",
    "**4 regularisations per month**", "Up to 2 days per month, with manager approval",
    "Up to 4 days per month, with manager approval", "Flexible, as agreed with the reporting manager",
    "**Field Sales employees of any band are not eligible for WFH.**",
    "| A | ₹3,500 | ₹2,500 |", "| M | ₹5,500 | ₹4,000 |", "| S | ₹8,000 | ₹6,000 |",
    "A ₹600 · M ₹900 · S ₹1,200", "journeys up to 500 km", "longer than 4 hours",
    "car ₹12 per km, two-wheeler ₹5 per km", "within **30 days**", "between 31 and 60 days",
    "**Claims submitted after 60 days are not reimbursed.**", "**ic@kavach.example**", "within **3 months**",
    "extend this by up to 3 more months", "| On probation (any band) | 15 days |",
    "| Confirmed — Band A | 30 days |", "| Confirmed — Band M | 60 days |", "| Confirmed — Band S | 90 days |",
    "| Intern | 7 days |", "within **45 days**", "Mann Sahayak (fictional EAP partner): 1800-000-4357**", "**eap@kavach.example**",
    "hr.help@kavach.example", "payroll@kavach.example", "first **6 months**",
    "Mumbai, Delhi NCR (Delhi, Gurugram, Noida), Bengaluru, Hyderabad, Chennai, Kolkata, Pune",
]


@dataclass
class Profile:
    employee_id: str | None = None
    name: str | None = None
    band: str | None = None           # "A" | "M" | "S" | "Intern" | None (unknown)
    role_type: str | None = None      # "Corporate" | "Field Sales" | "Intern" | None
    probation: str | None = None      # "On probation" | "Confirmed" | "Not applicable (Intern)" | None
    city: str | None = None
    doj: date | None = None
    hrbp_name: str | None = None
    hrbp_email: str | None = None

    @property
    def is_guest(self) -> bool:
        return self.employee_id is None

    @property
    def is_intern(self) -> bool:
        return self.band == "Intern" or self.role_type == "Intern"

    @property
    def hrbp(self) -> str:
        if self.hrbp_name:
            return f"your HRBP, {self.hrbp_name} ({self.hrbp_email})"
        return f"your HRBP (name and email are in PeopleHub) or the HR Helpdesk ({HELPDESK})"


@dataclass
class Result:
    text: str = ""
    refs: list[str] = field(default_factory=list)
    ask: tuple[str, str] | None = None   # (slot name, follow-up question) when an input is missing


def ask(slot: str, question: str) -> Result:
    return Result(ask=(slot, question))


ASK_BAND = ("band", "Which band are you in: A, M, S or Intern? (Or share your Employee ID.)")
ASK_STATUS = ("probation", "Are you confirmed, or still on probation?")
ASK_ROLE = ("role_type", "Is your role Corporate or Field Sales?")


def inr(n: float) -> str:
    return f"₹{n:,.0f}"


def add_months(d: date, n: int) -> date:
    y, m = divmod(d.month - 1 + n, 12)
    y, m = d.year + y, m + 1
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def completed_months(start: date, end: date) -> int:
    n = (end.year - start.year) * 12 + end.month - start.month
    return n - 1 if add_months(start, n) > end else max(n, 0)


def city_tier(city: str) -> str | None:
    """'1', '2/3', or None when the pack does not settle it."""
    key = city.lower()
    if key in TIER1:
        return "1"
    if key in AMBIGUOUS_CITIES:
        return None
    return "2/3"  # pack: "Tier 2/3: all other cities"


def not_covered(p: Profile, what: str) -> Result:
    return Result(f"I don't know — the Kavach HR Policy Pack doesn't cover {what}, so I can't give you a "
                  f"reliable answer. Please check with {p.hrbp}.", ["7"])


def intern_only_leave(p: Profile, extra: str = "") -> Result:
    months = completed_months(p.doj, AS_OF) if p.doj else None
    acc = (f" As of 15 Nov 2026 you have completed {months} month(s) since joining on {p.doj:%d %b %Y}, "
           f"so {months} day(s) have been earned in total — your remaining balance (after any leave taken) "
           f"is in PeopleHub (Leave).") if months is not None else ""
    return Result(f"{extra}As an intern you get **1 day of leave per completed month** of internship. It can't be "
                  f"carried forward or encashed, and no other leave type (EL, CL/SL, maternity, paternity, "
                  f"bereavement) applies to interns.{acc}", ["1.5"])


# ---------------------------------------------------------------- answers per intent
def a_sick_leave(p, s):
    if p.band is None:
        return ask(*ASK_BAND)
    if p.is_intern:
        return intern_only_leave(p, "Casual/Sick Leave doesn't apply to interns. ")
    txt = (f"You get **{CLSL_DAYS} days of Casual and Sick Leave (CL/SL) combined** per leave year "
           "(1 January – 31 December). CL/SL **cannot be carried forward or encashed**. Sick leave of "
           "**more than 2 consecutive days** needs a medical certificate uploaded in PeopleHub.")
    refs = ["1.3", "1.1"]
    if p.probation == "On probation":
        txt += " You're on probation, and CL/SL **can** be used during probation."
        refs.append("1.4")
    txt += " This is your yearly entitlement — your remaining balance is shown in PeopleHub (Leave)."
    return Result(txt, refs)


def a_earned_leave(p, s):
    if p.band is None:
        return ask(*ASK_BAND)
    if p.is_intern:
        return intern_only_leave(p, "Earned Leave doesn't apply to interns. ")
    days, cf = EL[p.band]
    txt = (f"As a Band {p.band} employee you earn **{days} days of Earned Leave (EL) per year**, credited monthly "
           f"in equal parts ({days / 12:g} days a month). You can carry forward up to **{cf} days** into the next "
           f"year; EL above that lapses on 31 December. EL can be encashed **only at the time of exit**, up to "
           f"a maximum of {EL_ENCASH_MAX} days.")
    refs = ["1.2"]
    if p.probation is None:
        txt += (" Note: if you are on probation, EL accrues from your joining date but can be used only after "
                "confirmation (emergency use needs manager + HRBP approval).")
        refs.append("1.4")
    elif p.probation == "On probation":
        txt += (" **You're currently on probation:** EL accrues from your date of joining, but you can **use EL only "
                "after confirmation**. In an emergency, EL can be used during probation with approval from both "
                "your reporting manager and your HRBP. CL/SL can be used during probation.")
        refs.append("1.4")
    txt += " Your current EL balance is in PeopleHub (Leave)."
    return Result(txt, refs)


def a_leave_general(p, s):
    if p.band is None:
        return ask(*ASK_BAND)
    if p.is_intern:
        return intern_only_leave(p)
    days, cf = EL[p.band]
    txt = (f"Your yearly leave **entitlement** (leave year 1 Jan – 31 Dec) as a Band {p.band} employee:\n"
           f"- **Earned Leave:** {days} days a year (credited monthly; carry-forward up to {cf} days)\n"
           f"- **Casual/Sick Leave:** {CLSL_DAYS} days combined (no carry-forward or encashment)\n"
           "- Event-based leave: maternity, paternity and bereavement leave as per policy.\n")
    refs = ["1.1", "1.2", "1.3"]
    if p.probation == "On probation":
        txt += ("\nYou're on probation, so EL accrues but can be **used only after confirmation** (emergency use "
                "needs manager + HRBP approval); CL/SL can be used now.\n")
        refs.append("1.4")
    txt += ("\nI can't see how many days you have **left** — your actual balance is in PeopleHub "
            "(*Leave*). To apply: PeopleHub > *Leave > Apply Leave*.")
    refs.append("1.9")
    return Result(txt, refs)


def a_maternity(p, s):
    if p.is_intern:
        return intern_only_leave(p, "Maternity leave isn't available to interns under the pack. ")
    return Result("Maternity leave is **26 weeks of paid leave** for the first two children, and **12 weeks** from "
                  "the third child onwards. Apply in PeopleHub (*Leave > Apply Leave*).", ["1.6", "1.9"])


def a_paternity(p, s):
    if p.is_intern:
        return intern_only_leave(p, "Paternity leave isn't available to interns under the pack. ")
    return Result("Paternity leave is **5 working days**, to be taken within **3 months** of the child's birth or "
                  "adoption. Apply in PeopleHub (*Leave > Apply Leave*).", ["1.7", "1.9"])


def a_bereavement(p, s):
    if p.is_intern:
        return intern_only_leave(p, "Bereavement leave isn't available to interns under the pack. ")
    return Result("I'm sorry for your loss. Bereavement leave is **3 working days** on the death of an immediate "
                  "family member (spouse, child, parent, sibling, parent-in-law). Apply in PeopleHub "
                  "(*Leave > Apply Leave*). If you'd like to talk to someone, the Employee Assistance Programme is "
                  f"free and confidential: {EAP}.", ["1.8", "1.9", "6.1"])


def a_leave_apply(p, s):
    return Result("Apply in PeopleHub: *Leave > Apply Leave*. Your reporting manager should act within **3 working "
                  "days**; if not, the request is escalated to your HRBP.", ["1.9"])


def a_working_hours(p, s):
    if p.role_type == "Field Sales":
        return Result("As a Field Sales employee you mark attendance using the **geo-tagged punch** in the PeopleHub "
                      "mobile app. (The 9:30 AM – 6:30 PM, Monday–Friday timing in the pack is for corporate "
                      "offices.)", ["2.1"])
    return Result("Corporate office hours are **9:30 AM to 6:30 PM, Monday to Friday**. Field Sales employees mark "
                  "attendance with the geo-tagged punch in the PeopleHub mobile app.", ["2.1"])


def a_late_marks(p, s):
    txt = ("A punch-in after **9:45 AM** is a late mark. Up to **3 late marks per calendar month** are allowed; the "
           "**4th and every later late mark** in the same month results in a **half-day deduction** from leave "
           "(EL first; if there is no EL balance, loss of pay).")
    n = s.get("count")
    if n is not None:
        ded = max(0, n - 3) * 0.5
        txt += (f" With {n} late mark(s) this month, that's **{ded:g} day(s)** deducted." if ded else
                f" With {n} late mark(s) this month, there is no deduction.")
    if p.role_type == "Field Sales":
        txt += (" Note: the pack doesn't say how the 9:45 AM cut-off applies to field (geo-tagged) punches — "
                f"please confirm with {p.hrbp}.")
    return Result(txt, ["2.2"])


def a_regularisation(p, s):
    return Result("A missed punch must be regularised in PeopleHub within **5 calendar days** of the date, and a "
                  "maximum of **4 regularisations per month** is allowed.", ["2.3"])


def a_wfh(p, s):
    if p.is_intern:
        return not_covered(p, "Work From Home for interns (the WFH table only covers Bands A, M and S in Corporate roles)")
    if p.role_type is None:
        return ask(*ASK_ROLE)
    if p.role_type == "Field Sales":
        return Result("No — **Field Sales employees of any band are not eligible for WFH**, so WFH isn't available "
                      "in your role.", ["2.4"])
    if p.band is None:
        return ask(*ASK_BAND)
    return Result(f"As a Band {p.band} Corporate employee, WFH is allowed **{WFH[p.band]}**.", ["2.4"])


def _travel_band(p) -> Result | None:
    if p.band is None:
        return ask(*ASK_BAND)
    if p.is_intern:
        return not_covered(p, "travel entitlements for interns (the travel tables only cover Bands A, M and S)")
    return None


def a_hotel(p, s):
    if (r := _travel_band(p)):
        return r
    if len(s.get("cities", [])) > 1:
        parts = [a_hotel(p, {"city": c}) for c in s["cities"]]
        return Result("\n\n".join(r.text for r in parts), ["3.1", "about"])
    city = s.get("city")
    if not city:
        return ask("city", "Which city will you be staying in? (Hotel limits depend on the destination city's tier.)")
    t1, t23 = HOTEL[p.band]
    tier = city_tier(city)
    if tier is None:
        return Result(f"The pack's Tier 1 list is Mumbai, Delhi NCR (Delhi, Gurugram, Noida), Bengaluru, Hyderabad, "
                      f"Chennai, Kolkata and Pune — it doesn't say whether **{city}** counts as Tier 1. For Band "
                      f"{p.band} the limit is **{inr(t1)}/night** in a Tier 1 city and **{inr(t23)}/night** in a Tier 2/3 "
                      f"city. Please confirm {city}'s tier with {p.hrbp} before booking.", ["3.1", "about"])
    amt = t1 if tier == "1" else t23
    note = "" if s.get("city_known", True) else (
        f" (I don't have {city} in my city list, so I've treated it as Tier 2/3 because it isn't in the Tier 1 list. "
        "If you meant a Tier 1 city, tell me.)")
    return Result(f"Your hotel limit as a Band {p.band} employee in **{city} (Tier {tier})** is **{inr(amt)} per "
                  f"night**.{note}", ["3.1", "about"])


def a_daily_allowance(p, s):
    if (r := _travel_band(p)):
        return r
    return Result(f"Your daily allowance (food and incidentals) as a Band {p.band} employee is **{inr(DA[p.band])} per "
                  "day of travel**.", ["3.2"])


def a_travel_mode(p, s):
    if (r := _travel_band(p)):
        return r
    km, hrs = s.get("distance_km"), s.get("flight_hours")
    if p.band == "M":
        return Result("As a Band M employee you can take an **economy flight for any distance**.", ["3.3"])
    if p.band == "S":
        if hrs is None:
            return Result("As a Band S employee you travel by **economy flight**; **premium economy** is allowed if the "
                          "flight is longer than 4 hours.", ["3.3"])
        ok = hrs > 4
        return Result(f"For a {hrs:g}-hour flight: economy flight applies, and premium economy is "
                      f"**{'allowed' if ok else 'not allowed'}** (it's allowed only for flights longer than 4 hours).",
                      ["3.3"])
    if km is None:  # Band A depends on distance
        return ask("distance_km", "Roughly how long is the journey in km? (For Band A, flights depend on distance.)")
    if km > 500:
        return Result(f"Yes — for a journey of about {km:g} km (above 500 km), Band A can take an **economy flight**.",
                      ["3.3"])
    return Result(f"No — Band A can fly only for journeys **above 500 km**. For about {km:g} km, **train (3AC)** applies.",
                  ["3.3"])


def a_travel_general(p, s):
    if (r := _travel_band(p)):
        return r
    t1, t23 = HOTEL[p.band]
    mode = {"A": "train (3AC) up to 500 km; economy flight only above 500 km",
            "M": "economy flight for any distance",
            "S": "economy flight; premium economy if the flight is longer than 4 hours"}[p.band]
    return Result(f"Your travel entitlements as a Band {p.band} employee:\n"
                  f"- **Daily allowance** (food and incidentals): {inr(DA[p.band])} per day of travel\n"
                  f"- **Hotel**: up to {inr(t1)}/night in a Tier 1 city, {inr(t23)}/night in a Tier 2/3 city "
                  "(tell me the destination city for the exact limit)\n"
                  f"- **Mode of travel**: {mode}\n"
                  f"- **Own-vehicle conveyance**: car {inr(CAR_PER_KM)}/km, two-wheeler {inr(TWO_WHEELER_PER_KM)}/km\n"
                  "- **Claims**: submit in PeopleHub within 30 days of the trip (31–60 days needs HRBP approval; "
                  "after 60 days not reimbursed)", ["3.1", "3.2", "3.3", "3.4", "3.5"])


def a_conveyance(p, s):
    txt = f"Local conveyance in your own vehicle is reimbursed at **car {inr(CAR_PER_KM)}/km** and **two-wheeler {inr(TWO_WHEELER_PER_KM)}/km**."
    km, veh = s.get("distance_km"), s.get("vehicle")
    if km is not None and veh:
        rate = CAR_PER_KM if veh == "car" else TWO_WHEELER_PER_KM
        txt += f" For {km:g} km by {veh}, that's **{inr(km * rate)}**."
    return Result(txt, ["3.4"])


def a_claims(p, s):
    txt = ("Submit claims with bills in PeopleHub (*Expenses > New Claim*) within **30 days** of the trip ending. "
           "Claims submitted between 31 and 60 days need HRBP approval, and **claims submitted after 60 days are "
           "not reimbursed**.")
    d = s.get("days")
    if d is not None:
        txt += " " + (f"At {d} days you're within the normal window." if d <= 30 else
                      f"At {d} days it needs HRBP approval." if d <= 60 else
                      f"At {d} days it can't be reimbursed.")
    return Result(txt, ["3.5"])


def a_notice(p, s):
    if p.is_intern:
        return Result(f"As an intern, your notice period is **{NOTICE_INTERN} days**.", ["5.1"])
    if p.probation is None:
        return ask(*ASK_STATUS)
    if p.probation == "On probation":
        return Result(f"You're on probation, so your notice period is **{NOTICE_PROBATION} days** (this applies to "
                      "any band during probation).", ["5.1"])
    if p.band is None:
        return ask(*ASK_BAND)
    return Result(f"As a confirmed Band {p.band} employee, your notice period is **{NOTICE[p.band]} days**.", ["5.1"])


def a_resign_how(p, s):
    return Result("To resign, submit your resignation in PeopleHub: *Separation > Resign*. Your reporting manager and "
                  "HRBP are notified automatically. The notice period may be shortened by paying the shortfall "
                  "(calculated on basic salary), subject to HRBP approval. Full and Final settlement is processed "
                  "within 45 days of your last working day.", ["5.2", "5.3", "5.4"])


def a_buyout(p, s):
    return Result("Yes, the notice period may be shortened by **paying the shortfall** (calculated on basic salary), "
                  "**subject to HRBP approval**. The pack doesn't give a formula beyond that — "
                  f"{p.hrbp} can confirm the amount.", ["5.3"])


def a_fnf(p, s):
    return Result("Full and Final (F&F) settlement is processed within **45 days** of the last working day.", ["5.4"])


def a_posh_info(p, s):
    return Result(f"Complaints of sexual harassment are handled by the **Internal Committee (IC)** under the POSH Act, "
                  f"2013. You can raise a complaint by email to **{IC_EMAIL}** or in writing to any IC member, ideally "
                  "within **3 months** of the incident (or of the last incident in a series); the IC may extend this "
                  "by up to 3 more months for valid reasons. Identities of the complainant, respondent and witnesses "
                  "are kept confidential, and retaliation against anyone who complains in good faith is a "
                  f"disciplinary offence. You can also reach out to {p.hrbp} for support.",
                  ["4.2", "4.3", "4.4", "4.5"])


def a_eap_info(p, s):
    return Result(f"The Employee Assistance Programme offers free, confidential counselling for you and your immediate "
                  f"family, 24×7: **{EAP}**.", ["6.1"])


def a_contacts(p, s):
    who = f"Your HRBP is **{p.hrbp_name}** ({p.hrbp_email}). " if p.hrbp_name else ""
    return Result(f"{who}Other contacts: HR Helpdesk {HELPDESK} · Payroll {PAYROLL} · POSH Internal Committee "
                  f"{IC_EMAIL} · Employee Assistance Programme 1800-000-4357 / eap@kavach.example.", ["7"])


def a_probation_info(p, s):
    if p.is_intern:
        return Result("Interns are not on probation — probation applies to all new employees except interns.", ["about"])
    base = "All new employees (except interns) are on probation for the first **6 months** from their date of joining."
    if p.is_guest or not p.doj:
        return Result(base + " Your status is shown in PeopleHub.", ["about"])
    if p.probation == "On probation":
        end = add_months(p.doj, 6)
        return Result(f"{base} You joined on {p.doj:%d %b %Y} and our records (as of 15 Nov 2026) show you **on "
                      f"probation**; six months from joining is **{end:%d %b %Y}**. Your confirmation status is "
                      "updated in PeopleHub.", ["about"])
    return Result(f"{base} Our records (as of 15 Nov 2026) show you as **{p.probation}**.", ["about"])


def a_profile(p, s):
    if p.is_guest:
        return Result("You're chatting without an Employee ID, so I don't have your profile. Share your Employee ID "
                      "to get personalised answers.", [])
    return Result(f"Here's what I use to personalise answers: **{p.name}** ({p.employee_id}) · Band {p.band} · "
                  f"{p.role_type} · {p.city} · {p.probation} · HRBP {p.hrbp_name} ({p.hrbp_email}).", [])


ANSWERS = {
    "sick_leave": a_sick_leave, "earned_leave": a_earned_leave, "leave_general": a_leave_general,
    "maternity": a_maternity, "paternity": a_paternity, "bereavement": a_bereavement, "leave_apply": a_leave_apply,
    "working_hours": a_working_hours, "late_marks": a_late_marks, "regularisation": a_regularisation, "wfh": a_wfh,
    "hotel": a_hotel, "daily_allowance": a_daily_allowance, "travel_mode": a_travel_mode,
    "conveyance": a_conveyance, "travel_general": a_travel_general, "claims": a_claims, "notice": a_notice, "resign_how": a_resign_how,
    "buyout": a_buyout, "fnf": a_fnf, "posh_info": a_posh_info, "eap_info": a_eap_info, "contacts": a_contacts,
    "probation_info": a_probation_info, "profile": a_profile,
}
