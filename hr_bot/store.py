"""Data loading (roster + policy pack check) and CSV logging."""
from __future__ import annotations

import csv
import os
import threading
import uuid
from datetime import date, datetime
from pathlib import Path

import pandas as pd

from .policy import POLICY_ANCHORS, Profile

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("HR_BOT_DATA_DIR", ROOT / "data"))
LOG_DIR = Path(os.getenv("HR_BOT_LOG_DIR", ROOT / "logs"))
ROSTER_COLS = ["employee_id", "name", "band", "role_type", "city", "date_of_joining", "probation_status",
               "hrbp_name", "hrbp_email"]
MSG_COLS = ["timestamp", "session_id", "employee_id", "role", "message", "topic", "flag_type", "policy_refs",
            "hrbp_name", "hrbp_email"]
ALERT_COLS = ["alert_id", "timestamp", "session_id", "employee_id", "flag_type", "priority", "topic", "routed_to",
              "hrbp_name", "hrbp_email", "summary", "status"]


class DataError(RuntimeError):
    pass


def load_policy(path: Path | None = None) -> str:
    path = path or DATA_DIR / "Kavach_HR_Policy_Pack.md"
    if not path.exists():
        raise DataError(f"Policy pack not found at {path}. Extract Kavach_Assignment_Attachments.zip into data/.")
    text = path.read_text(encoding="utf-8")
    missing = [a for a in POLICY_ANCHORS if a not in text]
    if missing:
        raise DataError(f"Policy pack does not match the engine's transcribed values; missing: {missing[:3]}")
    return text


def load_roster(path: Path | None = None) -> dict[str, Profile]:
    path = path or DATA_DIR / "Kavach_Employee_Roster.csv"
    if not path.exists():
        raise DataError(f"Employee roster not found at {path}. Extract Kavach_Assignment_Attachments.zip into data/.")
    df = pd.read_csv(path, dtype=str).fillna("")
    if (miss := set(ROSTER_COLS) - set(df.columns)):
        raise DataError(f"Roster is missing columns: {sorted(miss)}")
    roster = {}
    for r in df.to_dict("records"):
        eid = r["employee_id"].strip().upper()
        try:
            doj = date.fromisoformat(r["date_of_joining"].strip())
        except ValueError:
            doj = None
        roster[eid] = Profile(eid, r["name"].strip(), r["band"].strip(), r["role_type"].strip(),
                              r["probation_status"].strip(), r["city"].strip(), doj,
                              r["hrbp_name"].strip(), r["hrbp_email"].strip())
    return roster


# ponytail: one process-wide lock around CSV appends; swap for a DB/Google Sheet with row-level writes at scale.
_lock = threading.Lock()


def _append(path: Path, cols: list[str], row: dict) -> None:
    with _lock:
        path.parent.mkdir(parents=True, exist_ok=True)
        new = not path.exists() or path.stat().st_size == 0
        with path.open("a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            if new:
                w.writeheader()
            w.writerow({c: row.get(c, "") for c in cols})


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def log_message(**row) -> None:
    _append(LOG_DIR / "messages.csv", MSG_COLS, {"timestamp": now(), **row})


def log_alert(**row) -> str:
    aid = "AL-" + uuid.uuid4().hex[:8].upper()
    _append(LOG_DIR / "alerts.csv", ALERT_COLS, {"alert_id": aid, "timestamp": now(), "status": "open", **row})
    return aid


def read_alerts() -> pd.DataFrame:
    p = LOG_DIR / "alerts.csv"
    return pd.read_csv(p, dtype=str).fillna("") if p.exists() else pd.DataFrame(columns=ALERT_COLS)


def set_alert_status(alert_id: str, status: str) -> None:
    with _lock:
        df = read_alerts()
        df.loc[df["alert_id"] == alert_id, "status"] = status
        df.to_csv(LOG_DIR / "alerts.csv", index=False)
