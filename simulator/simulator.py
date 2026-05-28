"""
simulator.py
Real-time smart grid sensor simulator for Nigerian distribution feeders.
Generates transformer telemetry, fault events, and outage alerts.
Author: Ella | NSERC Portfolio CLD-001
"""

import json
import time
import random
import math
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, asdict
from typing import Optional

random.seed()

FEEDERS = [
    {"id": "ABJ-F01", "disco": "Abuja DisCo",         "lga": "Municipal",      "capacity_kva": 500,  "load_class": "mixed"},
    {"id": "ABJ-F02", "disco": "Abuja DisCo",         "lga": "Gwagwalada",     "capacity_kva": 300,  "load_class": "residential"},
    {"id": "IKJ-F01", "disco": "Ikeja DisCo",         "lga": "Ikeja",          "capacity_kva": 1000, "load_class": "commercial"},
    {"id": "IKJ-F02", "disco": "Ikeja DisCo",         "lga": "Agege",          "capacity_kva": 750,  "load_class": "industrial"},
    {"id": "EKO-F01", "disco": "Eko DisCo",           "lga": "Victoria Island","capacity_kva": 2000, "load_class": "commercial"},
    {"id": "EKO-F02", "disco": "Eko DisCo",           "lga": "Surulere",       "capacity_kva": 800,  "load_class": "residential"},
    {"id": "KAN-F01", "disco": "Kano DisCo",          "lga": "Fagge",          "capacity_kva": 600,  "load_class": "mixed"},
    {"id": "PHC-F01", "disco": "Port Harcourt DisCo", "lga": "GRA",            "capacity_kva": 1500, "load_class": "industrial"},
    {"id": "IBD-F01", "disco": "Ibadan DisCo",        "lga": "Ibadan North",   "capacity_kva": 400,  "load_class": "residential"},
    {"id": "YOL-F01", "disco": "Yola DisCo",          "lga": "Yola North",     "capacity_kva": 200,  "load_class": "residential"},
]

FAULT_TYPES = [
    "Phase Imbalance", "Overvoltage", "Undervoltage", "Overcurrent",
    "Earth Fault", "Harmonic Distortion", "Thermal Overload",
    "Conductor Sag", "Insulation Failure", "Transformer Oil Leak",
]

THRESHOLDS = {
    "voltage_pu_low":       0.90,
    "voltage_pu_high":      1.10,
    "load_pct_warning":     80,
    "load_pct_critical":    95,
    "temperature_warning":  70,
    "temperature_critical": 85,
    "power_factor_low":     0.80,
}


@dataclass
class TransformerReading:
    reading_id:        str
    timestamp:         str
    feeder_id:         str
    disco:             str
    lga:               str
    voltage_pu:        float
    voltage_phase_a_v: float
    voltage_phase_b_v: float
    voltage_phase_c_v: float
    current_a:         float
    load_kva:          float
    load_pct:          float
    power_factor:      float
    frequency_hz:      float
    temperature_c:     float
    oil_level_pct:     float
    is_energised:      bool
    status:            str
    alert_code:        Optional[str]
    alert_message:     Optional[str]


@dataclass
class OutageEvent:
    event_id:            str
    timestamp:           str
    feeder_id:           str
    disco:               str
    lga:                 str
    event_type:          str
    fault_type:          Optional[str]
    estimated_customers: int
    estimated_mwh_lost:  float
    cause:               str
    severity:            str


class GridSimulator:
    def __init__(self, interval_seconds=10, fault_probability=0.04):
        self.interval     = interval_seconds
        self.fault_prob   = fault_probability
        self.feeder_states = {f["id"]: {"energised": True, "outage_start": None}
                              for f in FEEDERS}
        self.reading_count = 0
        self.alert_count   = 0
        self._callbacks    = []

    def on_reading(self, cb):
        self._callbacks.append(cb)

    def _hour_load_factor(self):
        hour = datetime.now().hour
        peak    = 0.95 + 0.35 * math.exp(-0.5 * ((hour - 19) / 3) ** 2)
        morning = 0.20 * math.exp(-0.5 * ((hour - 8)  / 2) ** 2)
        return min(peak + morning, 1.0)

    def _generate_reading(self, feeder):
        fid       = feeder["id"]
        energised = self.feeder_states[fid]["energised"]
        hf        = self._hour_load_factor()

        base_pct = {"residential": 45, "commercial": 60,
                    "industrial": 70, "mixed": 50}.get(feeder["load_class"], 50)
        load_pct = base_pct * hf * random.uniform(0.85, 1.15)
        load_kva = (feeder["capacity_kva"] * load_pct / 100) if energised else 0.0

        sag   = max(0, (load_pct - 70) * 0.002)
        v_pu  = (1.0 - sag + random.gauss(0, 0.02)) if energised else 0.0
        v_pu  = round(max(0, v_pu), 4)
        nom_v = 415
        va = round(nom_v * v_pu + random.uniform(-5, 5), 1)
        vb = round(nom_v * v_pu + random.uniform(-8, 8), 1)
        vc = round(nom_v * v_pu + random.uniform(-8, 8), 1)

        current_a = round((load_kva * 1000) / (1.732 * nom_v + 0.001), 2)
        pf        = round(random.uniform(0.75, 0.98), 3) if energised else 0.0
        freq      = round(random.gauss(50.0, 0.15), 2)  if energised else 0.0
        temp      = round(30 + (load_pct / 100) * 55 + random.gauss(0, 3), 1) if energised else 30.0
        oil       = round(random.uniform(75, 100) - (temp - 30) * 0.1, 1)

        status = "NORMAL"
        code   = None
        msg    = None

        if not energised:
            status, code, msg = "FAULT",    "OUTAGE", f"Feeder {fid} de-energised"
        elif v_pu < THRESHOLDS["voltage_pu_low"]:
            status, code, msg = "WARNING",  "UV01",   f"Undervoltage: {v_pu:.3f} pu"
        elif v_pu > THRESHOLDS["voltage_pu_high"]:
            status, code, msg = "CRITICAL", "OV01",   f"Overvoltage: {v_pu:.3f} pu"
        elif load_pct > THRESHOLDS["load_pct_critical"]:
            status, code, msg = "CRITICAL", "OL02",   f"Critical overload: {load_pct:.1f}%"
        elif load_pct > THRESHOLDS["load_pct_warning"]:
            status, code, msg = "WARNING",  "OL01",   f"High load: {load_pct:.1f}%"
        elif temp > THRESHOLDS["temperature_critical"]:
            status, code, msg = "CRITICAL", "TH02",   f"Critical temp: {temp}°C"
        elif pf < THRESHOLDS["power_factor_low"] and energised:
            status, code, msg = "WARNING",  "PF01",   f"Low power factor: {pf:.3f}"

        if status != "NORMAL":
            self.alert_count += 1

        return TransformerReading(
            reading_id=f"{fid}-{int(time.time())}-{random.randint(1000,9999)}",
            timestamp=datetime.now(timezone.utc).isoformat(),
            feeder_id=fid, disco=feeder["disco"], lga=feeder["lga"],
            voltage_pu=v_pu, voltage_phase_a_v=va,
            voltage_phase_b_v=vb, voltage_phase_c_v=vc,
            current_a=current_a, load_kva=round(load_kva, 2),
            load_pct=round(load_pct, 2), power_factor=pf,
            frequency_hz=freq, temperature_c=temp, oil_level_pct=oil,
            is_energised=energised, status=status,
            alert_code=code, alert_message=msg,
        )

    def _maybe_inject_fault(self, feeder):
        fid   = feeder["id"]
        state = self.feeder_states[fid]

        if not state["energised"] and state["outage_start"]:
            elapsed = time.time() - state["outage_start"]
            if elapsed > random.uniform(180, 600):
                state["energised"]    = True
                state["outage_start"] = None
                return OutageEvent(
                    event_id=f"EVT-{fid}-{int(time.time())}",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    feeder_id=fid, disco=feeder["disco"], lga=feeder["lga"],
                    event_type="OUTAGE_END", fault_type=None,
                    estimated_customers=0, estimated_mwh_lost=0,
                    cause="Auto-recloser restored supply", severity="INFO",
                )
            return None

        if state["energised"] and random.random() < self.fault_prob:
            state["energised"]    = False
            state["outage_start"] = time.time()
            fault      = random.choice(FAULT_TYPES)
            customers  = int(feeder["capacity_kva"] / 10 * random.uniform(0.5, 2.0))
            return OutageEvent(
                event_id=f"EVT-{fid}-{int(time.time())}",
                timestamp=datetime.now(timezone.utc).isoformat(),
                feeder_id=fid, disco=feeder["disco"], lga=feeder["lga"],
                event_type="OUTAGE_START", fault_type=fault,
                estimated_customers=customers,
                estimated_mwh_lost=round(feeder["capacity_kva"] * 0.001 * random.uniform(1, 4), 2),
                cause=f"Detected: {fault}",
                severity="CRITICAL" if customers > 5000 else "HIGH",
            )
        return None

    def run(self, max_iterations=None, output_file=None):
        print(f"Smart Grid Simulator started — {len(FEEDERS)} feeders")
        print(f"Fault probability: {self.fault_prob*100:.1f}% per interval")
        print("Press Ctrl+C to stop\n")

        iteration = 0
        try:
            while max_iterations is None or iteration < max_iterations:
                readings = [self._generate_reading(f) for f in FEEDERS]
                events   = [e for f in FEEDERS
                            if (e := self._maybe_inject_fault(f)) is not None]

                self.reading_count += len(readings)
                alerts = [r for r in readings if r.status != "NORMAL"]

                ts = datetime.now().strftime("%H:%M:%S")
                print(f"[{ts}] Readings: {len(readings)} | "
                      f"Alerts: {len(alerts)} | Events: {len(events)} | "
                      f"Total alerts: {self.alert_count}")

                for a in alerts:
                    print(f"  [{a.status}] {a.feeder_id} — {a.alert_message}")
                for ev in events:
                    icon = "🔴" if ev.event_type == "OUTAGE_START" else "🟢"
                    print(f"  {icon} {ev.feeder_id} — {ev.cause}")

                for
