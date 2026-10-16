"""Data cleaning, issue formation, and explicit prioritization; no display code.

Only the supplied export is evidence. All recommendations are advisory and use
the fixed scenario clock, never the computer's current date.
"""

from __future__ import annotations

import csv
import hashlib
import math
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

EASTERN = ZoneInfo("America/Toronto")
SNAPSHOT = datetime(2026, 9, 21, 18, tzinfo=EASTERN)
DISPATCH = datetime(2026, 9, 22, 6, tzinfo=EASTERN)
DEFAULT_DATA = Path(__file__).resolve().parent.parent / "data"
UNKNOWN_REFERENCE = "Unknown — reference unavailable"


def parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"UTC timestamp requires a timezone: {value}")
    return parsed.astimezone(timezone.utc)


def parse_local(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%d %H:%M").replace(tzinfo=EASTERN)


def number(value):
    """Unknown/invalid numeric information stays unknown, never zero."""
    if value is None or str(value).strip() == "":
        return None
    try:
        parsed = float(value)
        return parsed if math.isfinite(parsed) else None
    except (ValueError, TypeError):
        return None


def read_csv(path: Path, required: set[str]) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{path.name}: missing columns {', '.join(sorted(missing))}")
        rows = list(reader)
    if any(None in row or any(v is None for v in row.values()) for row in rows):
        raise ValueError(f"{path.name}: malformed CSV row; inspect the supplied file")
    return rows


def group_alerts(rows: list[dict]) -> list[dict]:
    """Group identical payloads except ID/receipt, retaining all raw evidence.

    This is an action-counting assumption, not proof of retransmission. A changed
    severity, driver, value, DTC, or event time remains a different payload.
    """
    buckets = defaultdict(list)
    for row in rows:
        key = tuple(sorted((k, v) for k, v in row.items()
                           if k not in {"alert_id", "received_time_utc"}))
        buckets[key].append(dict(row))
    groups = []
    for key, raw in buckets.items():
        first = raw[0]
        group = {k: first.get(k, "") for k in
                 ("vehicle_id", "driver_id", "alert_type", "vendor_severity", "unit", "dtc_code")}
        group.update(
            id="event-" + hashlib.sha256(repr(key).encode()).hexdigest()[:12],
            alert_ids=[r["alert_id"] for r in raw],
            event_time=parse_utc(first["event_time_utc"]),
            received_times=[parse_utc(r["received_time_utc"]) for r in raw],
            value=number(first.get("value")),
            posted_limit_kmh=number(first.get("posted_limit_kmh")),
            raw_rows=raw,
        )
        groups.append(group)
    return sorted(groups, key=lambda g: (g["event_time"], g["id"]))


def reference_urgency(group: dict, references: dict) -> str:
    reference = references.get(group.get("dtc_code"), {})
    return reference.get("reference_urgency") or UNKNOWN_REFERENCE


def repair_state(group: dict, work_orders: list[dict]) -> dict:
    """Only an explicit same-code closed repair addresses an earlier event.

    Receipt time never reopens a repaired event. Absence of a matching work order
    means unknown resolution; it does not mean a fault is currently active.
    """
    code = group.get("dtc_code", "")
    if not code:
        return {"state": "unknown", "work_order_ids": []}
    matching = []
    for order in work_orders:
        text = order.get("work_done", "") + " " + order.get("technician_note", "")
        if (order["vehicle_id"] == group["vehicle_id"]
                and order.get("status", "").casefold() == "closed"
                and order.get("closed_local")
                and re.search(r"\b" + re.escape(code) + r"\b", text, re.IGNORECASE)):
            matching.append((parse_local(order["closed_local"]), order["wo_id"]))
    later = sorted((closed, wo) for closed, wo in matching if closed >= group["event_time"])
    if later:
        return {"state": "documented_repair", "work_order_ids": [wo for _, wo in later]}
    if matching:
        return {"state": "post_repair_event", "work_order_ids": [max(matching)[1]]}
    return {"state": "unknown", "work_order_ids": []}


def maintenance_state(value) -> str:
    value = number(value)
    if value is None:
        return "unknown"
    return "not_yet_due" if value < 0 else "overdue" if value > 0 else "due"


def driver_context(driver_id: str, groups: list[dict], vehicles: dict) -> dict:
    selected = [g for g in groups if g["driver_id"] == driver_id]
    vehicle_ids = sorted({g["vehicle_id"] for g in selected})
    distances = [number(vehicles.get(v, {}).get("km_driven_14d")) for v in vehicle_ids]
    vehicle_km = sum(distances) if distances and all(v is not None for v in distances) else None
    return {
        "driver_id": driver_id,
        "raw_alert_count": sum(len(g["raw_rows"]) for g in selected),
        "event_group_count": len(selected),
        "vehicles": vehicle_ids,
        "vehicle_km": vehicle_km,
        "driver_km": None,
        "exposure_note": "Vehicle kilometers are not driver exposure. Driver kilometers, hours, trips, and assignment history are unavailable; no worst-driver ranking is supported.",
    }


def iso_local(value: datetime) -> str:
    return value.astimezone(EASTERN).isoformat()


def event_evidence(group: dict, references: dict, work_orders: list[dict]) -> dict:
    repair = repair_state(group, work_orders)
    return {
        "alert_ids": group["alert_ids"],
        "alert_type": group["alert_type"], "dtc_code": group["dtc_code"],
        "event_time": iso_local(group["event_time"]),
        "received_times": [iso_local(t) for t in group["received_times"]],
        "value": group["value"], "unit": group["unit"],
        "posted_limit_kmh": group["posted_limit_kmh"],
        "vendor_severity": group["vendor_severity"],
        "meaning": references.get(group["dtc_code"], {}).get("meaning", "Unknown fault meaning") if group["alert_type"] == "engine_fault" else "",
        "reference_urgency": reference_urgency(group, references) if group["alert_type"] == "engine_fault" else "Not a DTC event",
        "receipt_lag_seconds": max((t - group["event_time"]).total_seconds() for t in group["received_times"]),
        "repair_state": repair["state"], "raw_rows": group["raw_rows"],
    }


def form_issues(groups: list[dict], vehicles: dict, references: dict, work_orders: list[dict]) -> list[dict]:
    """One shop coordination issue per vehicle, plus one safety-review candidate.

    All unaddressed reference-critical/high DTCs are candidates. Lower urgency
    engine codes and ordinary overdue readings remain visible in the appendix.
    """
    candidates = defaultdict(list)
    for group in groups:
        urgency = reference_urgency(group, references)
        if (group["alert_type"] == "engine_fault"
                and (urgency.startswith("Critical") or urgency.startswith("High"))
                and repair_state(group, work_orders)["state"] != "documented_repair"):
            candidates[group["vehicle_id"]].append(group)
    issues = []
    for vehicle_id, faults in candidates.items():
        latest = max(faults, key=lambda g: g["event_time"])
        critical = any(reference_urgency(g, references).startswith("Critical") for g in faults)
        related = list(faults)
        maintenance = [g for g in groups if g["vehicle_id"] == vehicle_id and g["alert_type"] == "maintenance_due"]
        latest_service = max(maintenance, key=lambda g: g["event_time"], default=None)
        if latest_service and maintenance_state(latest_service["value"]) in {"due", "overdue"}:
            related.append(latest_service)
        orders = [o for o in work_orders if o["vehicle_id"] == vehicle_id]
        matching_open = [o for o in orders if o["status"].casefold() == "open"
                         and ("misfire" in (o["work_done"] + " " + o["technician_note"]).casefold()
                              or any(g["dtc_code"] in o["work_done"] + " " + o["technician_note"] for g in faults))]
        recent = latest["event_time"].astimezone(EASTERN).date() >= (SNAPSHOT - timedelta(days=1)).date()
        inspection_deadline = min(g["event_time"] for g in faults) + timedelta(hours=24)
        inspection_overdue = inspection_deadline <= SNAPSHOT
        if critical:
            primary = max((g for g in faults if reference_urgency(g, references).startswith("Critical")), key=lambda g: g["event_time"])
            code = primary["dtc_code"]
            meaning = references.get(code, {}).get("meaning", "Fault meaning unavailable")
            title = f"{code}: {meaning} — confirm stopped and obtain mechanic assessment"
            why = f"The supplied {code} reference says: {reference_urgency(primary, references)}. The vendor labels this event {primary['vendor_severity']}."
            other_repaired_codes = {g["dtc_code"] for g in groups if g["vehicle_id"] == vehicle_id
                                    and g["dtc_code"] != code
                                    and repair_state(g, work_orders)["state"] == "documented_repair"}
            if other_repaired_codes:
                why += " Documented repairs for different codes (" + ", ".join(sorted(other_repaired_codes)) + ") do not resolve this event."
            action = f"Confirm the vehicle is stopped now; ask the maintenance lead to assess the reported {code} fault and confirm dispatch clearance."
            deadline = "Tonight immediately; confirm clearance before September 22, 06:00 EDT"
            status = "Immediate reference action; current vehicle status unknown"
            uncertainty = "The export cannot establish current mechanical condition or prove a diagnosis. A repair for a different code does not establish clearance for this fault."
            priority = 0
            basis = "Supplied DTC reference: " + reference_urgency(primary, references)
        elif matching_open:
            title = "Coordinate booked misfire inspection with 06:00 dispatch"
            why = "A recent P0300 event has an open misfire inspection booked first thing tomorrow. The work order supplies no exact appointment time or dispatch clearance."
            action = "Confirm the existing inspection time and coordinate the dispatch plan with maintenance; use the open work order rather than creating a duplicate."
            deadline = "Tonight: agree the plan for September 22, 06:00 EDT dispatch"
            status = "Open inspection booked; dispatch timing unconfirmed"
            uncertainty = "First thing tomorrow does not establish whether inspection precedes dispatch. No supplied inspection result establishes clearance."
            priority = 2
            basis = "Reference: inspect within 24 h; open booking overlaps the dispatch decision"
        elif recent:
            title = "Misfire inspection overdue; review the delayed service booking" if inspection_overdue else "Arrange reported misfire inspection within its reference window"
            why = f"The P0300 reference calls for inspection within 24 h, by {iso_local(inspection_deadline)}."
            why += " That time has passed at the snapshot." if inspection_overdue else " That deadline is still ahead at the snapshot."
            if latest_service and latest_service["value"] is not None:
                why += f" The same vehicle reports {latest_service['value']:g} km overdue; its scheduled oil/filter service does not document misfire inspection."
            action = "Ask the maintenance lead to arrange or verify misfire inspection tonight and review the service booking; coordinate the result with the morning dispatch plan."
            deadline = "Tonight; reference inspection deadline already passed" if inspection_overdue else "Coordinate tonight; inspect by " + iso_local(inspection_deadline)
            status = "Inspection deadline passed; resolution unknown" if inspection_overdue else "Reference inspection due; resolution unknown"
            uncertainty = "The supplied work orders do not establish that misfire inspection occurred. No supplied kilometer threshold authorizes an automatic maintenance stop."
            priority = 1 if inspection_overdue else 2
            basis = "Reference: inspect within 24 h; recent inspection and service coordination"
        else:
            title = "Verify resolution of an older reported misfire"
            why = "A P0300 event has no matching closed repair in the supplied work orders. Its reference inspection window has passed."
            action = "Check the maintenance record and current vehicle status; document whether this reported misfire was inspected or still needs attention before dispatch."
            deadline = "Tonight: verify status for September 22, 06:00 EDT dispatch"
            status = "Historical report; resolution unknown"
            uncertainty = "No matching supplied repair is not proof that the fault remains active. This is a verification task, not a diagnosis."
            priority = 4
            basis = "Reference-high historical event with no supplied same-code closure; newest event first"
        # Previous same-vehicle repairs provide context but cannot clear another code.
        context = [g for g in groups if g["vehicle_id"] == vehicle_id
                   and g["alert_type"] == "engine_fault"
                   and repair_state(g, work_orders)["state"] == "documented_repair"]
        all_evidence = sorted({g["id"]: g for g in related + context}.values(), key=lambda g: g["event_time"])
        issues.append({
            "id": f"shop-{vehicle_id}", "vehicle_id": vehicle_id,
            "depot": vehicles.get(vehicle_id, {}).get("depot", "Unknown depot"),
            "category": "Maintenance / dispatch", "title": title, "why": why,
            "next_action": action, "owner": "Operations manager + maintenance lead",
            "deadline": deadline, "status": status, "uncertainty": uncertainty,
            "priority_basis": basis, "alert_ids": [aid for g in all_evidence for aid in g["alert_ids"]],
            "work_order_ids": [o["wo_id"] for o in orders], "work_orders": orders,
            "inspection_deadline": iso_local(inspection_deadline) if not critical else None,
            "inspection_overdue": inspection_overdue if not critical else False,
            "evidence": [event_evidence(g, references, work_orders) for g in all_evidence],
            "_priority": priority, "_latest": latest["event_time"].timestamp(),
        })
    speeding = defaultdict(list)
    for group in groups:
        if (group["alert_type"] == "speeding" and group["value"] is not None
                and group["posted_limit_kmh"] is not None and group["unit"] == "km/h"):
            speeding[group["vehicle_id"]].append(group)
    if speeding:
        # One safety slot: greatest observed known-limit excess, not a risk threshold.
        vehicle_id = max(sorted(speeding), key=lambda v: max(g["value"] - g["posted_limit_kmh"] for g in speeding[v]))
        events = speeding[vehicle_id]
        largest = max(events, key=lambda g: g["value"] - g["posted_limit_kmh"])
        issues.append({
            "id": f"speed-review-{vehicle_id}", "vehicle_id": vehicle_id,
            "depot": vehicles.get(vehicle_id, {}).get("depot", "Unknown depot"),
            "category": "Safety review", "title": "Review repeated recorded speeding with the safety manager",
            "why": f"{len(events)} payload groups have recorded limits. The largest records {largest['value']:g} km/h against {largest['posted_limit_kmh']:g}, a {largest['value'] - largest['posted_limit_kmh']:g} km/h difference.",
            "next_action": "Review the recorded events and posted-limit accuracy with the safety manager, then agree the appropriate driver conversation before the next dispatch.",
            "owner": "Safety manager", "deadline": "Tonight or before next dispatch",
            "status": "Evidence review recommended; no driver ranking",
            "uncertainty": "Map-provider limits may be inaccurate. The export lacks route context and driver exposure; these readings do not establish a worst driver.",
            "priority_basis": "One safety-review slot: vehicle with the greatest observed known-limit speed excess; no invented safety cutoff",
            "alert_ids": [aid for g in events for aid in g["alert_ids"]],
            "work_order_ids": [], "work_orders": [],
            "evidence": [event_evidence(g, references, work_orders) for g in events],
            "_priority": 3, "_latest": max(g["event_time"].timestamp() for g in events),
        })
    return issues


def prioritize(issues: list[dict], limit: int = 10) -> tuple[list[dict], list[dict]]:
    ordered = sorted(issues, key=lambda i: (i["_priority"], -i["_latest"], i["id"]))
    cleaned = [{k: v for k, v in issue.items() if not k.startswith("_")} for issue in ordered]
    return cleaned[:limit], cleaned[limit:]


def audit_data(rows: list[dict], groups: list[dict], vehicles: dict) -> dict:
    lags = [(parse_utc(r["received_time_utc"]) - parse_utc(r["event_time_utc"])).total_seconds() for r in rows]
    maintenance = [g for g in groups if g["alert_type"] == "maintenance_due"]
    latest = {}
    for group in maintenance:
        latest[group["vehicle_id"]] = group
    night = lambda r: r["alert_type"] in {"device_unplugged", "camera_offline"} and parse_utc(r["event_time_utc"]).astimezone(EASTERN).hour == 23
    firmware = Counter(v["device_firmware"] for v in vehicles.values())
    braking = Counter(vehicles.get(r["vehicle_id"], {}).get("device_firmware", "unknown") for r in rows if r["alert_type"] == "harsh_braking")
    return {
        "raw_alert_count": len(rows), "event_group_count": len(groups),
        "suspected_duplicate_pairs": sum(len(g["raw_rows"]) == 2 for g in groups),
        "suspected_repeat_rows": len(rows) - len(groups),
        "duplicate_id_count": len(rows) - len({r["alert_id"] for r in rows}),
        "missing_posted_limit_count": sum(r["alert_type"] == "speeding" and not r["posted_limit_kmh"] for r in rows),
        "delayed_over_hour_count": sum(s > 3600 for s in lags),
        "delayed_over_day_count": sum(s > 86400 for s in lags),
        "hamilton_delayed_count": sum(s > 3600 and vehicles.get(r["vehicle_id"], {}).get("depot") == "Hamilton Depot" for r, s in zip(rows, lags)),
        "max_lag_seconds": max(lags, default=0),
        "negative_lag_count": sum(s < 0 for s in lags),
        "conditional_missing_value_count": sum(not r["value"] for r in rows),
        "invalid_numeric_count": sum(bool(r[field]) and number(r[field]) is None for r in rows for field in ("value", "posted_limit_kmh")),
        "unknown_vehicle_count": sum(r["vehicle_id"] not in vehicles for r in rows),
        "unknown_dtc_count": 0,
        "maintenance_positive_count": sum(maintenance_state(g["value"]) == "overdue" for g in latest.values()),
        "maintenance_negative_count": sum(maintenance_state(g["value"]) == "not_yet_due" for g in latest.values()),
        "maintenance_observed_vehicle_count": len(latest),
        "night_window_raw_count": sum(night(r) for r in rows),
        "firmware_vehicle_counts": dict(firmware), "firmware_braking_raw_counts": dict(braking),
        "notes": [
            "Matching payloads are grouped only when every CSV field except alert_id and received_time_utc matches. Raw rows, IDs, severities, and all receipt times remain accessible. Retransmission is suspected, not proven.",
            "Missing posted limits remain unknown: no inferred speed excess or fallback posted limit. All supplied speeding units are km/h (55–131); there is no supplied basis for unit conversion or declaring large readings corrupt.",
            "The 248 blank value/unit pairs are 153 camera/device events and 95 engine faults. A missing numerical reading does not erase a DTC or establish safety.",
            "Hamilton has a delayed-delivery pattern, not a proven common batch or diagnosed gateway failure. Use event time for chronology, receipt time for delivery freshness.",
            "Maintenance values are dated observations: negative means not yet due. Only three maintenance readings are from September 21; 20 vehicles have no supplied reading. Do not project current mileage from 14-day totals.",
            "Vendor notes describe 23:00–00:00 local device/camera events as expected updates. Outside-window alerts remain in the raw data; isolated events do not establish continuing downtime.",
            "Firmware 4.2.1 is associated with more low-magnitude braking reports: 12/60 vehicles account for 488/837 raw braking rows. This observation does not prove a firmware defect or worse driving.",
            "No GPS, trip history, driver-specific kilometers/hours, assignment history, complete repair history, or current mechanical/dispatch status is supplied. Absent evidence remains unknown.",
            "One-hour and one-day delivery summaries describe latency; they are not invented operational safety thresholds. The yesterday/today grouping used for recent inspection coordination is a documented product ordering choice, not a diagnosis.",
        ],
    }


def build_report(data_dir: Path | str = DEFAULT_DATA) -> dict:
    data_dir = Path(data_dir)
    alerts = read_csv(data_dir / "alerts.csv", {"alert_id", "vehicle_id", "driver_id", "alert_type", "vendor_severity", "event_time_utc", "received_time_utc", "value", "unit", "posted_limit_kmh", "dtc_code"})
    vehicle_rows = read_csv(data_dir / "vehicles.csv", {"vehicle_id", "depot", "device_firmware", "assigned_driver", "km_driven_14d"})
    reference_rows = read_csv(data_dir / "dtc_reference.csv", {"dtc_code", "meaning", "reference_urgency"})
    all_orders = read_csv(data_dir / "work_orders.csv", {"wo_id", "vehicle_id", "opened_local", "closed_local", "status", "work_done", "technician_note"})
    vehicles = {v["vehicle_id"]: v for v in vehicle_rows}
    references = {r["dtc_code"]: r for r in reference_rows}
    eligible = [r for r in alerts if parse_utc(r["event_time_utc"]) <= SNAPSHOT and parse_utc(r["received_time_utc"]) <= SNAPSHOT]
    groups = group_alerts(eligible)
    orders = [o for o in all_orders if parse_local(o["opened_local"]) <= SNAPSHOT]
    if any(o["closed_local"] and parse_local(o["closed_local"]) > SNAPSHOT for o in orders):
        raise ValueError("Work orders contain post-snapshot closure data; review as-of status before generating a report")
    audit = audit_data(eligible, groups, vehicles)
    audit["excluded_after_snapshot_count"] = len(alerts) - len(eligible)
    audit["unknown_dtc_count"] = sum(r["alert_type"] == "engine_fault" and r["dtc_code"] not in references for r in eligible)
    issues, overflow = prioritize(form_issues(groups, vehicles, references, orders))
    audit["overflow_issue_count"] = len(overflow)
    audit["vendor_high_reference_low_count"] = sum(r["alert_type"] == "engine_fault" and r["vendor_severity"] == "HIGH" and references.get(r["dtc_code"], {}).get("reference_urgency", "").startswith("Low") for r in eligible)
    audit["vendor_high_engine_count"] = sum(r["alert_type"] == "engine_fault" and r["vendor_severity"] == "HIGH" for r in eligible)
    context = driver_context("D-17", groups, vehicles)
    drivers = [{
        "title": "D-17: highest raw count does not establish worst driver",
        "facts": [f"{context['raw_alert_count']} raw alerts / {context['event_group_count']} matching-payload groups; observed vehicle V-142, firmware 4.2.1.",
                  "V-142 has 3,650 vehicle km, the fleet maximum. All alert assignments match current assignments, but assignment history is unavailable.",
                  "D-17 has 55 raw / 51 grouped braking events; 48 raw readings are 0.40–0.43 g. Firmware and exposure qualify the comparison.",
                  "Individually reviewable events still exist: A-131693 (0.62 g braking on September 21) and A-120165 (85 km/h against recorded 60)."],
        "uncertainty": context["exposure_note"], **context,
    }]
    repaired = [g for g in groups if g["alert_type"] == "engine_fault" and repair_state(g, orders)["state"] == "documented_repair"]
    routine = [g for g in groups if g["alert_type"] == "engine_fault" and not reference_urgency(g, references).startswith(("Critical", "High"))]
    unknown_faults = [g for g in groups if g["alert_type"] == "engine_fault" and g["dtc_code"] not in references]
    appendix = [
        {"title": "Documented same-code repairs", "detail": "V-137 P0217, V-114 P0217, V-101 P0300, V-149 P0300, and V-108 P0171 have supplied closed repairs after their events. No same-code post-repair recurrence is supplied. A closed work order is documented repair evidence, not proof of future mechanical safety.",
         "alert_ids": [a for g in repaired for a in g["alert_ids"]], "work_order_ids": sorted({wo for g in repaired for wo in repair_state(g, orders)["work_order_ids"]}),
         "evidence": [event_evidence(g, references, orders) for g in repaired]},
        {"title": "Routine / monitor engine codes", "detail": f"{len(routine)} payload groups are reference-medium next-service or reference-low monitoring/emissions codes. {audit['vendor_high_reference_low_count']}/{audit['vendor_high_engine_count']} vendor-HIGH engine rows are reference-low. Preserve these for service planning rather than consuming tonight's leading slots.",
         "alert_ids": [a for g in routine for a in g["alert_ids"]], "work_order_ids": []},
        {"title": "Maintenance coverage and dated readings", "detail": "40 vehicle readings after grouping: 16 positive/overdue, 24 negative/not yet due. Only three are from snapshot day. Smaller or older positive readings remain service-planning evidence; no service-stop cutoff is supplied.", "alert_ids": [a for g in groups if g["alert_type"] == "maintenance_due" for a in g["alert_ids"]], "work_order_ids": ["WO-5541"]},
        {"title": "Device/camera events and existing shop context", "detail": "23 raw rows are within the documented nightly update window, including 22 V-118 rows. V-123 unplugged events precede the WO-5531 harness repair; no later unplugged recurrence is supplied. WO-5536 says V-102 is parked/not dispatched with its unit removed; there is no V-102 unplugged alert to invent. Other isolated device events remain unverified, not assumed resolved.", "alert_ids": [a for g in groups if g["alert_type"] in {"device_unplugged", "camera_offline"} for a in g["alert_ids"]], "work_order_ids": ["WO-5531", "WO-5536"]},
    ]
    for issue in overflow:
        appendix.append({"title": "Capacity overflow: " + issue["title"], "detail": issue["why"] + " Next: " + issue["next_action"], "alert_ids": issue["alert_ids"], "work_order_ids": issue["work_order_ids"]})
    if unknown_faults:
        appendix.append({"title": "Unknown fault-reference urgency — review required", "detail": "Unmapped DTCs are unknown, not low or safe; review their raw evidence before making a dispatch decision.", "alert_ids": [a for g in unknown_faults for a in g["alert_ids"]], "work_order_ids": []})
    return {
        "title": "What needs me tonight?", "as_of": iso_local(SNAPSHOT), "dispatch_at": iso_local(DISPATCH),
        "issues": issues, "audit": audit, "drivers": drivers, "appendix": appendix,
        "sources": ["alerts.csv", "vehicles.csv", "dtc_reference.csv", "work_orders.csv", "vendor_notes.md"],
        "source_sha256": {name: hashlib.sha256((data_dir / name).read_bytes()).hexdigest() for name in ["alerts.csv", "vehicles.csv", "dtc_reference.csv", "work_orders.csv", "vendor_notes.md"]},
        "policy": "Critical reference actions first; recent overdue inspection second; booked pre-dispatch coordination third; one strongest recorded-speed review fourth; older reference-high status checks newest-first. Cap ten and expose overflow. Recent means event on snapshot day or previous local day; it is an explicit ordering assumption, not a safety cutoff.",
    }
