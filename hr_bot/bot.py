"""Conversation orchestrator: identity, guardrails, sensitive routing, follow-ups, logging."""
from __future__ import annotations

import re
import unicodedata
import uuid
from dataclasses import dataclass, field

from . import llm, nlu, store
from .policy import ANSWERS, EAP, IC_EMAIL, SECTIONS, Profile, Result

MAX_LEN = 1000
GREETING_RE = re.compile(r"^(hi+|hello|hey|namaste|good (morning|afternoon|evening)|thanks?|thank you|ok(ay)?|cool|bye)\W*$")
HELP = ("I can answer questions from the Kavach HR Policy Pack — leave, attendance & WFH, travel & reimbursement, "
        "POSH, separation and wellbeing — personalised to you. Try: *How many sick leaves do I get?* or "
        "*What's my hotel limit in Pune?*")


@dataclass
class Reply:
    text: str
    topic: str
    flags: list[str] = field(default_factory=list)
    refs: list[str] = field(default_factory=list)


@dataclass
class Session:
    roster: dict[str, Profile]
    profile: Profile | None = None       # None until the user identifies (or continues as guest)
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    last_intent: str | None = None
    last_slots: dict = field(default_factory=dict)
    pending: tuple[str, str, dict] | None = None   # (intent, slot, slots so far)
    self_reported: set = field(default_factory=set)

    # ------------------------------------------------------------ identity
    def login(self, raw_id: str) -> Reply:
        eid = re.sub(r"[\s-]", "", (raw_id or "")).upper()
        if not re.fullmatch(r"KV\d{4}", eid):
            return self._finish("(login)", Reply("That doesn't look like a Kavach Employee ID (format: KV followed by "
                                                 "4 digits, e.g. KV1001). Please try again.", "login_invalid"))
        p = self.roster.get(eid)
        if not p:
            self.profile = Profile()
            return self._finish(eid, Reply(f"I couldn't find {eid} in the employee roster. You can re-enter your ID, "
                                           "or continue — I'll ask for details like your band when an answer depends "
                                           "on them.", "login_not_found"))
        self.profile = p
        self.last_intent, self.last_slots, self.pending, self.self_reported = None, {}, None, set()
        who = f"Intern, {p.city}" if p.is_intern else f"Band {p.band}, {p.role_type}, {p.city}, {p.probation}"
        return self._finish(eid, Reply(f"Hi {p.name.split()[0]}! I've got your profile: {who}. "
                                       f"Your HRBP is {p.hrbp_name}. {HELP}", "login"))

    def as_guest(self) -> None:
        self.profile = Profile()

    # ------------------------------------------------------------ main entry
    def respond(self, raw: str) -> Reply:
        if self.profile is None:
            return self.login(raw)
        text = "".join(ch for ch in str(raw or "") if unicodedata.category(ch)[0] != "C" or ch in "\n\t").strip()
        if not text:
            return Reply("Please type a question.", "empty")
        if len(text) > MAX_LEN:
            return self._finish(text[:200] + "…", Reply(f"That message is too long (over {MAX_LEN} characters). "
                                                        "Please ask one question at a time.", "too_long"))
        t = nlu.norm(text)
        p = self.profile

        # identity switch / other employees' IDs
        ids = {re.sub(r"[\s-]", "", m).upper() for m in nlu.EMP_ID_RE.findall(t)}
        if p.is_guest and len(ids) == 1 and not nlu.detect_sensitive(t):
            return self.login(ids.pop())
        flags = nlu.detect_sensitive(t)
        if not flags:
            if nlu.INJECTION_RE.search(t):
                return self._finish(text, Reply(
                    "I can't change how I work or step outside the HR Policy Pack. I only answer from the policy pack, "
                    "for you, and I can't share other employees' information. What policy question can I help with?",
                    "guardrail", ["INJECTION_ATTEMPT"]), alert=False)
            if self._asks_about_others(t, ids):
                return self._finish(text, Reply(
                    "Sorry, I can't share or look up another employee's personal or employment information. I can only "
                    f"answer policy questions for you. For anything else, please contact {p.hrbp}.",
                    "guardrail", ["PRIVACY_REQUEST"]), alert=False)

        if not flags and GREETING_RE.match(t):
            return self._finish(text, Reply(HELP, "greeting"))

        intents, slots = self._understand(t, flags)
        reply = self._compose(t, flags, intents, slots)
        return self._finish(text, reply)

    # ------------------------------------------------------------ understanding
    def _understand(self, t: str, flags: list[str]) -> tuple[list[str], dict]:
        intents, slots = nlu.detect_intents(t), nlu.extract_slots(t)
        if self.pending:
            p_intent, p_slot, p_slots = self.pending
            val = self._parse_slot(p_slot, t)
            if val is not None:
                self.pending = None
                if p_slot in ("band", "probation", "role_type"):
                    setattr(self.profile, p_slot, val)
                    self.self_reported.add(p_slot)
                else:
                    p_slots = {**p_slots, p_slot: val}
                return [p_intent], {**p_slots, **{k: v for k, v in slots.items() if k != p_slot}}
            self.pending = None
        if not intents and slots and self.last_intent:  # "and for Pune?" / "what about 600 km?"
            if any(self.last_intent in nlu.SLOT_INTENTS.get(k, ()) for k in slots):
                return [self.last_intent], {**self.last_slots, **slots}
        if nlu.unsupported_topics(t):  # incidental generic matches shouldn't answer an uncovered question
            intents = [i for i in intents if i not in ("claims", "leave_general", "contacts")]
        if not intents and not flags and not nlu.unsupported_topics(t):
            if (res := llm.classify(t)):
                if res["sensitive"] != "none":  # LLM may only ADD a sensitive route, never remove one
                    flags.append({"posh": "POSH", "distress": "DISTRESS", "exit": "EXIT_INTENT"}[res["sensitive"]])
                if res["intent"] != "unsupported":
                    intents = [res["intent"]]
                    slots = {**res["slots"], **slots}
                    if "city" in res["slots"] and "city" not in nlu.extract_slots(t):
                        slots["city_known"] = res["slots"]["city"].lower() in nlu.KNOWN_CITIES
        return intents, slots

    def _parse_slot(self, slot: str, t: str):
        if slot == "band":
            return nlu.parse_band(t)
        if slot == "probation":
            return nlu.parse_probation(t)
        if slot == "role_type":
            return nlu.parse_role(t)
        if slot == "city":
            if (c := nlu.destination_city(t) or (nlu.find_cities(t) or [(0, None)])[0][1]):
                return c
            word = re.sub(r"[^a-z ]", "", t).strip()
            if 2 < len(word) <= 25 and len(word.split()) <= 2 and not nlu.detect_intents(t):
                return word.title()  # unrecognised city name -> treated as Tier 2/3 with a visible note
            return None
        if slot == "distance_km":
            m = re.search(r"(\d[\d,]*(?:\.\d+)?)", t)
            return float(m.group(1).replace(",", "")) if m else None
        return None

    def _asks_about_others(self, t: str, ids: set[str]) -> bool:
        me = self.profile
        if ids - {me.employee_id}:
            return True
        data_words = re.search(r"band|grade|salary|ctc|phone|number|mobile|email|leave|probation|notice|details|"
                               r"joining|doj|city|address|record|hrbp|confirmed|role|designation|manager", t)
        for p in self.roster.values():
            if p.employee_id == me.employee_id:
                continue
            full, first = p.name.lower(), p.name.split()[0].lower()
            if full in t or re.search(rf"\b{first}(?:'s\b|s'|\s(?:ka|ki|ke)\b)", t) or (data_words and re.search(rf"\b{first}\b", t)):
                return True
        return bool(nlu.PRIVACY_GENERIC_RE.search(t))

    # ------------------------------------------------------------ reply composition
    def _compose(self, t: str, flags: list[str], intents: list[str], slots: dict) -> Reply:
        p, parts, refs, topic = self.profile, [], [], None
        hrbp = p.hrbp
        if "DISTRESS_CRISIS" in flags or "DISTRESS" in flags:
            topic = "wellbeing"
            msg = ("I'm really sorry you're going through this, and I'm glad you said something. You don't have to "
                   f"handle it alone. The Employee Assistance Programme offers free, confidential counselling 24×7 for "
                   f"you and your immediate family: **{EAP}**.")
            if "DISTRESS_CRISIS" in flags:
                msg += (" **If you are in immediate danger or thinking about harming yourself, please contact local "
                        "emergency services or a crisis helpline right now**, and if you can, let someone near you know.")
                refs.append("6.2")
            msg += f" I've also sent an urgent note to {hrbp} so a person can check in with you."
            parts.append(msg)
            refs.append("6.1")
            intents = [i for i in intents if i != "eap_info"]
        if "POSH" in flags:
            topic = topic or "posh"
            parts.append(
                "Thank you for telling me — raising this takes courage. I can't assess what happened, but I can share "
                "how to raise it formally. Complaints of sexual harassment are handled by the **Internal Committee "
                f"(IC)** under the POSH Act, 2013: email **{IC_EMAIL}** or write to any IC member. A complaint should "
                "be made within **3 months** of the incident (or of the last incident, if it's a series); the IC can "
                "extend this by up to 3 more months for valid reasons. The identities of the complainant, respondent "
                "and witnesses are kept **confidential**, and **retaliation** against anyone who complains in good "
                f"faith is a disciplinary offence. {hrbp[0].upper() + hrbp[1:]} can also support you in raising a "
                "complaint. I've logged a confidential POSH alert (without the details of your message) so the right "
                "people are aware.")
            refs += ["4.2", "4.3", "4.4", "4.5"]
            intents = [i for i in intents if i != "posh_info"]
        elif "WORKPLACE_CONCERN" in flags:
            topic = topic or "workplace_concern"
            parts.append(
                "I'm sorry you're dealing with this. The policy pack doesn't set out a process for this kind of "
                f"concern, so I've flagged it to {hrbp}, who can help. If it involves sexual harassment, you can also "
                f"raise it with the Internal Committee at **{IC_EMAIL}** (within 3 months of the incident; "
                "confidential, and retaliation is prohibited).")
            refs += ["4.2", "4.3", "4.4", "7"]

        if "EXIT_INTENT" in flags and not intents:
            intents = ["notice", "resign_how"]
        ask = None
        for intent in intents:
            res: Result = ANSWERS[intent](p, slots)
            if res.ask:
                ask = ask or (intent, res.ask)
                continue
            parts.append(res.text)
            refs += res.refs
            topic = topic or intent
        if intents and not ask:
            self.last_intent = intents[0]
            self.last_slots = {k: v for k, v in slots.items() if k != "city_known"}
        if ask:
            intent, (slot, question) = ask
            self.pending = (intent, slot, {k: v for k, v in slots.items() if k != "city_known"})
            self.last_intent = intent
            parts.append(question)
            topic = topic or intent

        if "EXIT_INTENT" in flags:
            topic = topic or "separation"
            parts.append(f"I've also let {hrbp} know, so they can support you with next steps if you'd like to talk it "
                         "through.")
        if (unk := nlu.unsupported_topics(t)) and not ("POSH" in flags and not intents):
            parts.append(f"I don't know about {', '.join(unk)} — the Kavach HR Policy Pack doesn't cover "
                         f"{'it' if len(unk) == 1 else 'them'}, so I won't guess. Please check with {hrbp}.")
            refs.append("7")
            topic = topic or "unknown"
        if not parts:
            parts.append("I don't know — I couldn't find anything in the Kavach HR Policy Pack that covers this, so I "
                         f"won't guess. Please check with {hrbp}. (I can help with leave, attendance & WFH, travel & "
                         "reimbursement, POSH, separation and wellbeing.)")
            refs.append("7")
            topic = "unknown"

        other_band = nlu.parse_band(t) if not p.is_guest and intents and not ask else None
        if other_band and other_band != p.band:
            own = "Intern" if p.is_intern else f"Band {p.band}"
            asked = "Intern" if other_band == "Intern" else f"Band {other_band}"
            parts.insert(0, f"_You mentioned {asked} — I can only personalise answers to your own profile ({own}), "
                            "so here's what applies to you:_")
        text = "\n\n".join(parts)
        if self.self_reported and not ask and intents:
            text = f"_Based on the details you shared ({', '.join(sorted(self.self_reported))}):_\n\n" + text
        refs = list(dict.fromkeys(refs))
        if refs and not ask:
            text += "\n\n📄 **Source:** Kavach HR Policy Pack v3.2 — " + "; ".join(SECTIONS[r] for r in refs)
        return Reply(text, topic or "unknown", flags, refs)

    # ------------------------------------------------------------ logging
    def _finish(self, user_text: str, reply: Reply, alert: bool = True) -> Reply:
        p = self.profile or Profile()
        eid = p.employee_id or "UNVERIFIED"
        flag_s = ";".join(reply.flags)
        base = dict(session_id=self.session_id, employee_id=eid, topic=reply.topic, flag_type=flag_s,
                    hrbp_name=p.hrbp_name or "", hrbp_email=p.hrbp_email or "")
        logged = ("[withheld: POSH disclosure - routed to Internal Committee; see alerts.csv]"
                  if "POSH" in reply.flags else user_text)
        store.log_message(role="user", message=logged, policy_refs="", **base)
        store.log_message(role="assistant", message=reply.text, policy_refs=";".join(reply.refs), **base)
        if alert:
            hr = (f"HRBP {p.hrbp_name} ({p.hrbp_email})" if p.hrbp_name
                  else "HR Helpdesk (hr.help@kavach.example) - employee not verified")
            for f in reply.flags:
                rule = ALERT_RULES[f]
                store.log_alert(session_id=self.session_id, employee_id=eid, flag_type=f, topic=reply.topic,
                                hrbp_name=p.hrbp_name or "", hrbp_email=p.hrbp_email or "",
                                priority=rule["priority"], summary=rule["summary"],
                                routed_to=rule["routed_to"].format(hr=hr))
        return reply


HR = "{hr}"
ALERT_RULES = {
    "POSH": dict(priority="HIGH", routed_to=f"Internal Committee ({IC_EMAIL}); {HR} for support",
                 summary="POSH concern disclosed in chat. Details withheld from logs; IC route shared. Do not contact "
                         "the respondent; IC to follow up confidentially."),
    "DISTRESS_CRISIS": dict(priority="URGENT", routed_to=HR,
                            summary="Possible self-harm / crisis language. EAP + emergency guidance shared. Contact "
                                    "the employee today."),
    "DISTRESS": dict(priority="URGENT", routed_to=HR,
                     summary="Employee expressed distress / wellbeing concern. EAP contact shared. Please check in."),
    "WORKPLACE_CONCERN": dict(priority="HIGH", routed_to=HR,
                              summary="Workplace conduct concern (e.g. bullying) not covered by the pack. Please follow up."),
    "EXIT_INTENT": dict(priority="MEDIUM", routed_to=HR,
                        summary="Possible resignation / exit intent. Factual separation info shared. Consider a "
                                "retention / stay conversation."),
}
