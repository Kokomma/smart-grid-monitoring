"""
alert_processor.py
Azure Function — processes grid sensor events, classifies severity,
determines escalation path and SLA deadline.
Author: Ella | NSERC Portfolio CLD-001
"""

import json
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, asdict
from typing import Optional


ESCALATION_RULES = {
    "OV01":   {"severity": "HIGH",     "notify": ["ops_team"],                              "sla_minutes": 30},
    "UV01":   {"severity": "MEDIUM",   "notify": ["ops_team"],                              "sla_minutes": 60},
    "OL02":   {"severity": "CRITICAL", "notify": ["ops_team", "management", "nerc"],        "sla_minutes": 15},
    "OL01":   {"severity": "MEDIUM",   "notify": ["ops_team"],                              "sla_minutes": 60},
    "TH02":   {"severity": "CRITICAL", "notify": ["ops_team", "management"],                "sla_minutes": 10},
    "PF01":   {"severity": "LOW",      "notify": ["maintenance"],                           "sla_minutes": 480},
    "OUTAGE": {"severity": "CRITICAL", "notify": ["ops_team", "management", "customers"],   "sla_minutes": 5},
}

ACTIONS = {
    "OV01":   "Dispatch field crew to inspect voltage regulator. Check tap changer position.",
    "UV01":   "Monitor load. Check upstream feeder capacity. Notify affected customers.",
    "OL02":   "Immediate load shedding required. Activate emergency generator banks.",
    "OL01":   "Alert maintenance team. Schedule demand-side management for peak hours.",
    "TH02":   "Emergency shutdown may be required. Dispatch thermal inspection team.",
    "PF01":   "Schedule capacitor bank inspection for next maintenance window.",
    "OUTAGE": "Dispatch field crew immediately. Check for vandalism or fallen conductors.",
}


@dataclass
class ProcessedAlert:
    alert_id:          str
    processed_at:      str
    feeder_id:         str
    disco:             str
    lga:               str
    alert_code:        str
    alert_message:     str
    severity:          str
    escalation_path:   list
    sla_deadline:      str
    voltage_pu:        Optional[float]
    load_pct:          Optional[float]
    temperature_c:     Optional[float]
    status:            str
    action_taken:      str


def process_reading(reading: dict) -> Optional[ProcessedAlert]:
    code = reading.get("alert_code")
    if not code or reading.get("status") == "NORMAL":
        return None

    rule = ESCALATION_RULES.get(code, {
        "severity": "UNKNOWN", "notify": ["ops_team"], "sla_minutes": 60
    })

    now      = datetime.now(timezone.utc)
    deadline = (now + timedelta(minutes=rule["sla_minutes"])).isoformat()

    import time, random
    return ProcessedAlert(
        alert_id=f"ALT-{reading.get('feeder_id','X')}-{int(time.time())}",
        processed_at=now.isoformat(),
        feeder_id=reading.get("feeder_id", "UNKNOWN"),
        disco=reading.get("disco", "UNKNOWN"),
        lga=reading.get("lga", "UNKNOWN"),
        alert_code=code,
        alert_message=reading.get("alert_message", ""),
        severity=rule["severity"],
        escalation_path=rule["notify"],
        sla_deadline=deadline,
        voltage_pu=reading.get("voltage_pu"),
        load_pct=reading.get("load_pct"),
        temperature_c=reading.get("temperature_c"),
        status=reading.get("status", "UNKNOWN"),
        action_taken=ACTIONS.get(code, "Review and escalate to operations team."),
    )


def main(reading_json: str) -> dict:
    """
    Entry point — accepts a JSON string of one sensor reading.
    In Azure: replace with azure.functions HttpRequest / EventHub trigger.
    """
    try:
        reading = json.loads(reading_json)
    except json.JSONDecodeError:
        return {"error": "Invalid JSON"}

    alert = process_reading(reading)

    if alert is None:
        return {
            "status": "OK",
            "message": f"Reading from {reading.get('feeder_id','?')} is normal",
            "alert_generated": False,
        }

    print(f"ALERT [{alert.severity}] {alert.feeder_id}: {alert.alert_message}")
    print(f"  Action: {alert.action_taken}")
    print(f"  SLA deadline: {alert.sla_deadline}")
    print(f"  Escalate to: {', '.join(alert.escalation_path)}")

    return {"status": "ALERT_RAISED", "alert": asdict(alert), "alert_generated": True}


if __name__ == "__main__":
    # Test with a sample critical reading
    sample = json.dumps({
        "feeder_id": "IKJ-F01", "disco": "Ikeja DisCo", "lga": "Ikeja",
        "status": "CRITICAL", "alert_code": "OL02",
        "alert_message": "Critical overload: 97.3%",
        "voltage_pu": 0.94, "load_pct": 97.3, "temperature_c": 78.2,
    })
    result = main(sample)
    print("\nResult:", json.dumps(result, indent=2))
