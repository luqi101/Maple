"""Render the fixed Maple Freight snapshot without network or runtime dependencies."""

from datetime import datetime
from html import escape
from pathlib import PurePosixPath
from urllib.parse import quote
from zoneinfo import ZoneInfo


def _h(value):
    return escape(str(value if value is not None else ""), quote=True)


def _items(value):
    if value is None:
        return []
    return value if isinstance(value, (list, tuple)) else [value]


def _date(value, seconds=False):
    if not value:
        return "Not supplied"
    try:
        stamp = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if stamp.tzinfo:
            stamp = stamp.astimezone(ZoneInfo("America/Toronto"))
        else:
            stamp = stamp.replace(tzinfo=ZoneInfo("America/Toronto"))
        clock = stamp.strftime("%I:%M:%S" if seconds else "%I:%M").lstrip("0")
        suffix = "a.m." if stamp.hour < 12 else "p.m."
        return f"{stamp.strftime('%b')} {stamp.day}, {stamp.year} · {clock} {suffix} {stamp.tzname() or 'Eastern'}"
    except (ValueError, TypeError):
        return str(value)


def _number(value):
    if value is None or value == "":
        return "—"
    if isinstance(value, (float, int)):
        return f"{value:,g}"
    return str(value)


def _lag(seconds):
    if seconds is None:
        return "Not supplied"
    seconds = round(float(seconds))
    hours, rest = divmod(seconds, 3600)
    minutes, seconds = divmod(rest, 60)
    return f"{hours}h {minutes}m {seconds}s" if hours else f"{minutes}m {seconds}s"


def _ids(values):
    return ", ".join(str(v) for v in _items(values)) or "None supplied"


def _source_link(source, mapping=None):
    name = PurePosixPath(str(source)).name
    data_files = {"alerts.csv", "vehicles.csv", "dtc_reference.csv", "work_orders.csv", "vendor_notes.md"}
    relative = "../data/" + name if name in data_files else "../" + name
    if mapping:
        relative = mapping.get(str(source), mapping.get(name, relative))
    return f'<a href="{_h(quote(relative))}">{_h(name)}</a>'


_AUDIT_LABELS = [
    ("baseline_raw_alert_count", "Original export alert rows"),
    ("backfill_row_count", "New Hamilton backfill rows"),
    ("repeated_input_row_count", "Repeated input rows excluded"),
    ("raw_alert_count", "Raw alert rows"),
    ("event_group_count", "Event groups after suspected duplicate grouping"),
    ("suspected_duplicate_pairs", "Suspected duplicate pairs"),
    ("missing_posted_limit_count", "Speeding rows missing a posted limit"),
    ("delayed_over_hour_count", "Rows received more than 1 hour late"),
    ("delayed_over_day_count", "Rows received more than 24 hours late"),
    ("hamilton_delayed_count", "Hamilton rows received more than 1 hour late"),
    ("max_lag_seconds", "Longest delivery delay"),
    ("conditional_missing_value_count", "Blank numeric values (interpret by alert type)"),
    ("maintenance_positive_count", "Vehicles with latest positive overdue reading"),
    ("maintenance_negative_count", "Vehicles with latest negative, not-yet-due reading"),
    ("maintenance_observed_vehicle_count", "Vehicles with a maintenance observation"),
    ("night_window_raw_count", "Device/camera rows within the local update window"),
]


def _evidence_table(evidence):
    rows = []
    for event in _items(evidence):
        received = "<br>".join(_h(_date(v, True)) for v in _items(event.get("received_times"))) or "Not supplied"
        code = event.get("dtc_code") or "—"
        measurement = f"{_number(event.get('value'))} {event.get('unit') or ''}".strip()
        if event.get("posted_limit_kmh") is not None:
            measurement += f"; posted limit {_number(event['posted_limit_kmh'])} km/h"
        reference = event.get("reference_urgency") or "Not supplied for this event type"
        meaning = event.get("meaning") or event.get("dtc_meaning") or ""
        provenance = ", ".join(str(v) for v in _items(event.get("sources")))
        rows.append(
            "<tr>"
            f"<td><strong>{_h(event.get('alert_type', ''))}</strong><br><code>{_h(code)}</code>"
            f"<div class='record-ids'>{_h(_ids(event.get('alert_ids')))}</div>"
            + (f"<div class='muted'>Source: {_h(provenance)}</div>" if provenance else "")
            + "</td>"
            f"<td>{_h(_date(event.get('event_time'), True))}</td>"
            f"<td>{received}<div class='muted'>Lag: {_h(_lag(event.get('receipt_lag_seconds')))}</div></td>"
            f"<td>{_h(measurement)}<br><span class='muted'>Vendor: {_h(event.get('vendor_severity') or 'Not supplied')}</span></td>"
            f"<td>{_h(meaning)}{'<br>' if meaning else ''}{_h(reference)}<div class='muted'>{_h(event.get('repair_state') or '')}</div></td>"
            "</tr>"
        )
    if not rows:
        return "<p>No alert evidence rows attached. Review the work-order evidence and supplied files.</p>"
    return (
        "<div class='table-scroll'><table><thead><tr><th>Event &amp; record IDs</th><th>Event time · Eastern</th>"
        "<th>Received time · Eastern</th><th>Reading &amp; vendor label</th><th>Reference / repair context</th>"
        "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>"
    )


def _work_order_table(orders):
    if not orders:
        return "<p class='context'>No supplied work order for this issue. This does not prove no repair occurred.</p>"
    rows = []
    for order in orders:
        closed = _date(order.get("closed_local")) if order.get("closed_local") else "Not closed in supplied record"
        rows.append(
            f"<tr><td><strong>{_h(order.get('wo_id'))}</strong><br>{_h(order.get('status'))}</td>"
            f"<td>{_h(_date(order.get('opened_local')))}</td><td>{_h(closed)}</td>"
            f"<td>{_h(order.get('work_done'))}</td><td>{_h(order.get('technician_note'))}</td></tr>"
        )
    return (
        "<h4>Work-order evidence</h4><div class='table-scroll'><table><thead><tr>"
        "<th>Work order / status</th><th>Opened · Eastern</th><th>Closed · Eastern</th>"
        "<th>Work recorded</th><th>Technician note / booking</th></tr></thead><tbody>"
        + "".join(rows) + "</tbody></table></div>"
    )


def _update_html(update, as_of):
    if not update:
        return ""
    before = " → ".join(str(v) for v in _items(update.get("baseline_top_three")))
    after = " → ".join(str(v) for v in _items(update.get("updated_top_three")))
    notes = "".join(f"<li>{_h(note)}</li>" for note in _items(update.get("notes")))
    return (
        "<section class='update-notice' aria-labelledby='update-heading'>"
        "<h2 id='update-heading'>What changed after the new information</h2>"
        f"<p>{_h(update.get('backfill_row_count', 'New'))} delayed Hamilton alerts arrived in the 6:47 p.m. EDT batch "
        f"(through {_h(_date(as_of, True))}). Their events occurred earlier the same day, before the original 6:00 p.m. snapshot.</p>"
        f"<p><strong>Before:</strong> {_h(before)}<br><strong>After:</strong> {_h(after)}</p>"
        f"<ul>{notes}</ul></section>"
    )


def render_html(report: dict) -> str:
    """Return a self-contained, escaped, print-friendly HTML operations report."""
    issues = _items(report.get("issues"))
    audit = report.get("audit", {})
    top = []
    cards = []
    for index, issue in enumerate(issues, 1):
        anchor = f"issue-{index}"
        if index <= 3:
            top.append(
                f"<a class='top-card' href='#{anchor}'><span class='top-number'>0{index}</span>"
                f"<div><span class='eyebrow'>{_h(issue.get('vehicle_id'))} · {_h(issue.get('depot'))}</span>"
                f"<h3>{_h(issue.get('title'))}</h3><p>{_h(issue.get('why'))}</p>"
                f"<span class='top-deadline'>{_h(_date(issue.get('deadline')))} ↗</span></div></a>"
            )
        uncertainty = issue.get("uncertainty") or "No additional uncertainty supplied."
        cards.append(
            f"<article class='issue' id='{anchor}'><div class='issue-number'>{index:02}</div><div class='issue-body'>"
            f"<div class='issue-meta'><span>{_h(issue.get('vehicle_id'))} · {_h(issue.get('depot'))}</span>"
            f"<span class='badge'>{_h(issue.get('status') or 'Review needed')}</span></div>"
            f"<h3>{_h(issue.get('title'))}</h3><p>{_h(issue.get('why'))}</p>"
            f"<div class='action'><span class='eyebrow'>Next action</span><p>{_h(issue.get('next_action'))}</p>"
            f"<div class='assignment'><span><strong>Owner</strong> {_h(issue.get('owner'))}</span>"
            f"<span><strong>When</strong> {_h(_date(issue.get('deadline')))}</span></div></div>"
            f"<p class='context'><strong>Why this order:</strong> {_h(issue.get('priority_basis'))}</p>"
            f"<p class='context'><strong>What remains uncertain:</strong> {_h(uncertainty)}</p>"
            f"<details class='evidence'><summary>Evidence &amp; timing <span>{len(_items(issue.get('alert_ids')))} alert records</span></summary>"
            f"<p class='record-line'><strong>Alert IDs:</strong> {_h(_ids(issue.get('alert_ids')))}<br>"
            f"<strong>Work orders:</strong> {_h(_ids(issue.get('work_order_ids')))}</p>"
            f"{_evidence_table(issue.get('evidence'))}{_work_order_table(issue.get('work_orders'))}</details></div></article>"
        )
    metrics = "".join(
        f"<tr><th>{_h(label)}</th><td>{_h(_lag(audit[key]) if key == 'max_lag_seconds' else _number(audit[key]))}</td></tr>"
        for key, label in _AUDIT_LABELS if key in audit
    )
    notes = "".join(f"<li>{_h(note)}</li>" for note in _items(audit.get("notes")))
    drivers = "".join(
        "<article class='review-card'>"
        f"<h3>{_h(driver.get('title'))}</h3>"
        + "".join(f"<p>{_h(fact)}</p>" for fact in _items(driver.get("facts")))
        + f"<p class='context'><strong>Limit:</strong> {_h(driver.get('uncertainty'))}</p></article>"
        for driver in _items(report.get("drivers"))
    )
    appendix = "".join(
        f"<article class='review-card'><h3>{_h(item.get('title'))}</h3><p>{_h(item.get('detail'))}</p>"
        f"<details><summary>Source records <span>{len(_items(item.get('alert_ids')))} alert records</span></summary>"
        f"<p class='record-line'>Alerts: {_h(_ids(item.get('alert_ids')))}<br>"
        f"Work orders: {_h(_ids(item.get('work_order_ids')))}</p></details></article>"
        for item in _items(report.get("appendix"))
    )
    sources = "".join(f"<li>{_source_link(source, report.get('source_links', {}))}</li>" for source in _items(report.get("sources")))
    sources += '<li><a href="report.json">Generated report.json · full evidence</a></li>'
    return """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>""" + _h(report.get("title") or "Maple Freight · Tonight's action board") + """</title>
<style>
:root{--ink:#192d2b;--muted:#586862;--paper:#f4f3ed;--line:#d7ddd5;--green:#244c41;--alert:#974627;--cream:#faf0e5}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
a{color:var(--green);text-underline-offset:3px}a:focus-visible,summary:focus-visible{outline:3px solid #b66e20;outline-offset:5px}.shell{max-width:1260px;margin:0 auto;padding:0 36px}
.masthead{background:var(--ink);color:#fff;border-bottom:5px solid #be8353}.brand{padding:20px 0;font-size:14px;font-weight:750;letter-spacing:.15em}.brand span{color:#c6d6cc;font-weight:400;letter-spacing:0;margin-left:14px}
header{padding:44px 0 28px}.eyebrow{text-transform:uppercase;letter-spacing:.1em;font-size:11px;font-weight:750;color:var(--muted)}h1{font-size:clamp(34px,5vw,57px);line-height:1.08;letter-spacing:-.045em;margin:12px 0 19px;max-width:840px}h2{font-size:25px;letter-spacing:-.025em;margin:0}h3{font-size:20px;line-height:1.3;letter-spacing:-.018em;margin:8px 0 10px}p{margin:9px 0 14px}.snapshot{display:flex;flex-wrap:wrap;gap:10px 28px;color:var(--muted);font-size:14px}.snapshot strong{color:var(--ink)}
.notice{padding:13px 17px;background:#e5e9df;border-left:3px solid var(--green);font-size:13px;max-width:980px;margin-top:22px}.update-notice{margin-top:20px;padding:18px 20px;border:1px solid #c9b596;background:#faf4e9;border-radius:4px}.update-notice h2{font-size:20px}.update-notice p,.update-notice li{font-size:13px}.update-notice ul{margin-bottom:0;padding-left:20px}.top-area{padding:15px 0 36px}.section-title{display:flex;align-items:baseline;gap:16px;justify-content:space-between;margin:14px 0 18px}.section-title p{font-size:13px;color:var(--muted);margin:0}.top-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}.top-card{display:flex;gap:14px;padding:22px;background:var(--green);color:white;text-decoration:none;border-radius:5px}.top-card:first-child{background:var(--alert)}.top-card:hover{filter:brightness(1.07)}.top-card .eyebrow{color:#e0e9df}.top-card p{font-size:13px;color:#f3f3e9}.top-card h3{font-size:19px}.top-number{font-size:16px;opacity:.65;font-variant-numeric:tabular-nums}.top-deadline{font-size:12px;font-weight:650}
main{padding-bottom:45px}.issue{display:grid;grid-template-columns:48px minmax(0,1fr);gap:18px;padding:27px 28px;background:#fff;border:1px solid var(--line);border-radius:5px;margin:13px 0;scroll-margin-top:20px}.issue-number{color:#6f8275;font-size:23px;font-weight:600;font-variant-numeric:tabular-nums}.issue-meta{display:flex;flex-wrap:wrap;gap:10px;justify-content:space-between;font-size:12px;font-weight:650;color:var(--muted)}.badge{background:#eef0e8;padding:3px 9px;border-radius:3px;color:#445543}.issue h3{font-size:23px}.issue-body>p{max-width:960px}.action{background:#f0f3ec;padding:15px 18px;border-left:3px solid #52775b;margin:17px 0}.action p{margin:4px 0 12px}.assignment{display:flex;flex-wrap:wrap;gap:7px 26px;font-size:13px}.assignment strong{margin-right:7px}.context{font-size:13px;color:var(--muted)}.context strong{color:#344b41}.record-line{font-size:12px;overflow-wrap:anywhere;color:var(--muted)}
details{border-top:1px solid var(--line);margin-top:18px;padding-top:14px}summary{cursor:pointer;font-size:14px;font-weight:650}summary span{float:right;font-size:12px;font-weight:400;color:var(--muted)}.table-scroll{overflow-x:auto;margin:14px 0}table{border-collapse:collapse;width:100%;font-size:12px;text-align:left}th,td{padding:11px 10px;vertical-align:top;border-bottom:1px solid var(--line)}thead th{background:#f3f4ef;font-size:11px;min-width:145px}.record-ids{font-size:11px;margin-top:8px;overflow-wrap:anywhere}.muted{color:var(--muted);margin-top:6px}code{font-size:12px}
.secondary{margin-top:32px;padding-top:25px;border-top:1px solid #c8d1c5}.secondary>p{color:var(--muted);font-size:14px}.selection-policy{padding:0 0 20px;max-width:1050px}.selection-policy h2{font-size:17px}.selection-policy p{font-size:13px;color:var(--muted)}.audit-details{background:#fff;border:1px solid var(--line);padding:20px;border-radius:4px}.audit-grid{display:grid;grid-template-columns:1fr 1fr;gap:28px;margin-top:15px}.audit-grid th{font-weight:500}.audit-grid td{text-align:right;white-space:nowrap;font-weight:650}.audit-grid ul{padding-left:18px;margin-top:8px;font-size:13px}.audit-grid li{margin:9px 0}.review-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:13px}.review-card{padding:18px 21px;background:#fdfdf9;border:1px solid var(--line);border-radius:4px}.review-card h3{font-size:17px}.review-card p{font-size:13px}.source-list{display:flex;flex-wrap:wrap;gap:10px 24px;padding:0;list-style:none;font-size:13px}footer{border-top:1px solid var(--line);padding:22px 0 35px;color:var(--muted);font-size:12px}
@media(max-width:850px){.top-grid{grid-template-columns:1fr}.top-card p{max-width:620px}.audit-grid{grid-template-columns:1fr;gap:12px}.shell{padding:0 20px}.review-grid{grid-template-columns:1fr}.section-title{align-items:flex-start;flex-direction:column;gap:4px}}
@media(max-width:520px){.issue{grid-template-columns:minmax(0,1fr);padding:20px;gap:5px}.issue-body{min-width:0}.issue-number{font-size:15px}.issue h3{font-size:21px}.brand span{display:block;margin:5px 0 0}.snapshot{display:block}.snapshot span{display:block;margin:5px 0}summary span{float:none;display:block;margin:5px 0}header{padding-top:28px}.action{padding:12px}.shell{padding:0 14px}}
@media print{body{background:#fff;font-size:10pt}.shell{max-width:none;padding:0}.masthead{background:none;color:var(--ink);border-bottom:1px solid var(--line)}.brand{padding:8px 0}.brand span{color:var(--muted)}header{padding:16px 0}h1{font-size:29pt}.top-area{padding-bottom:15px}.top-grid{grid-template-columns:repeat(3,1fr)}.top-card,.top-card:first-child{background:#f2f2e8;color:var(--ink);border:1px solid var(--line);padding:12px;break-inside:avoid}.top-card .eyebrow,.top-card p{color:var(--muted)}.top-card h3{font-size:12pt}.top-card p{font-size:9pt}.issue{padding:15px 10px;break-inside:avoid;grid-template-columns:30px minmax(0,1fr);gap:10px}.issue h3{font-size:15pt}.issue-number{font-size:15pt}.action{padding:10px}.context,.record-line,.assignment{font-size:9pt}details{display:block}details>summary{display:none}details::details-content{display:block!important;content-visibility:visible!important}details>*:not(summary){display:block!important}.table-scroll{overflow:visible}table{font-size:8pt}thead th{min-width:0;font-size:7pt}th,td{padding:6px 4px}.review-card{break-inside:avoid}.review-grid{grid-template-columns:1fr 1fr}.secondary{margin-top:20px;padding-top:15px}a{text-decoration:none}footer{padding:12px 0}}
</style></head><body>
<div class="masthead"><div class="shell brand">MAPLE FREIGHT <span>Operations handover · September 21, 2026</span></div></div>
<div class="shell"><header><div class="eyebrow">Evening operations → morning dispatch</div><h1>What needs me tonight?</h1>
<div class="snapshot"><span><strong>As of</strong> """ + _h(_date(report.get("as_of"), bool(report.get("update")))) + """</span><span><strong>Before dispatch</strong> """ + _h(_date(report.get("dispatch_at"))) + """</span></div>
<div class="notice"><strong>Fixed snapshot, not live.</strong> This read-only report supports the manager’s next actions. It does not provide dispatch clearance. Confirm vehicle status and assigned work with the responsible team.</div>
""" + _update_html(report.get("update"), report.get("as_of")) + """</header><section class="top-area" aria-labelledby="top-heading"><div class="section-title"><h2 id="top-heading">Tonight’s top 3</h2><p>Start here · reference urgency, work orders, and event timing</p></div><div class="top-grid">""" + "".join(top) + """</div></section>
<main><section class="selection-policy" aria-labelledby="policy-heading"><h2 id="policy-heading">How this list was chosen</h2><p>""" + _h(report.get("policy") or "Grouped evidence supports a limited list of next actions; confirm outstanding work before dispatch.") + """</p></section>
<section aria-labelledby="actions-heading"><div class="section-title"><h2 id="actions-heading">Action list</h2><p>""" + str(len(issues)) + """ grouped issues · related records share one action</p></div>""" + "".join(cards) + """</section>
<section class="secondary" aria-labelledby="quality-heading"><h2 id="quality-heading">Data quality &amp; limits</h2><p>Counts describe the supplied export. The evidence retains every source alert ID.</p>
<details class="audit-details"><summary>Inspect export checks and interpretation limits</summary><div class="audit-grid"><table><tbody>""" + metrics + """</tbody></table><ul>""" + notes + """</ul></div></details></section>
<section class="secondary" aria-labelledby="drivers-heading"><div class="section-title"><h2 id="drivers-heading">Driver comparison: what we can say</h2></div><div class="review-grid">""" + drivers + """</div></section>
<section class="secondary" aria-labelledby="review-heading"><div class="section-title"><h2 id="review-heading">Reviewed / not in tonight’s list</h2></div><div class="review-grid">""" + appendix + """</div></section>
<section class="secondary" aria-labelledby="sources-heading"><h2 id="sources-heading">Raw supplied files</h2><p>Open the originals for all observations, including records outside the action list.</p><ul class="source-list">""" + sources + """</ul></section></main>
<footer>Maple Freight · Supplied synthetic data only · All displayed event and work-order times use America/Toronto. Missing repair evidence does not establish that a fault remains active.</footer>
</div></body></html>"""


def render_text(report: dict) -> str:
    """Return a complete plain-text handover with the same underlying evidence."""
    lines = [
        "MAPLE FREIGHT — What needs me tonight?",
        f"As of: {_date(report.get('as_of'), bool(report.get('update')))}",
        f"Before dispatch: {_date(report.get('dispatch_at'))}",
        "Fixed snapshot, not live. Read-only decision support; no dispatch clearance.",
        "Confirm vehicle status and assigned work with the responsible team.",
    ]
    update = report.get("update")
    if update:
        lines.extend([
            "", "What changed after the new information",
            f"{update.get('backfill_row_count', 'New')} delayed Hamilton alerts arrived in the 6:47 p.m. EDT batch (through {_date(report.get('as_of'), True)}).",
            "Their events occurred earlier the same day, before the original 6:00 p.m. snapshot.",
            "Before: " + " → ".join(str(v) for v in _items(update.get("baseline_top_three"))),
            "After: " + " → ".join(str(v) for v in _items(update.get("updated_top_three"))),
        ])
        lines.extend(f"- {note}" for note in _items(update.get("notes")))
    lines.extend(["", "Tonight’s top 3"])
    for index, issue in enumerate(_items(report.get("issues"))[:3], 1):
        lines.extend([
            f"{index}. {issue.get('vehicle_id', '')}: {issue.get('title', '')}",
            f"   Why: {issue.get('why', '')}",
            f"   Next: {issue.get('next_action', '')}",
            f"   Owner: {issue.get('owner', '')}; by: {_date(issue.get('deadline'))}",
        ])
    lines.extend(["", "How this list was chosen", str(report.get("policy", "")), "", "Action list"])
    for index, issue in enumerate(_items(report.get("issues")), 1):
        lines.extend([
            "", f"{index}. {issue.get('vehicle_id', '')} · {issue.get('depot', '')} — {issue.get('title', '')}",
            f"Status: {issue.get('status', '')}", f"Why: {issue.get('why', '')}",
            f"Next action: {issue.get('next_action', '')}",
            f"Owner: {issue.get('owner', '')}; when: {_date(issue.get('deadline'))}",
            f"Priority basis: {issue.get('priority_basis', '')}",
            f"Uncertainty: {issue.get('uncertainty', '')}",
            f"Alert IDs: {_ids(issue.get('alert_ids'))}",
            f"Work orders: {_ids(issue.get('work_order_ids'))}", "Evidence & timing:",
        ])
        for event in _items(issue.get("evidence")):
            lines.extend([
                f"  {_ids(event.get('alert_ids'))} | {event.get('alert_type', '')} | {event.get('dtc_code') or 'no DTC'}",
                "  Source: " + (", ".join(str(v) for v in _items(event.get("sources"))) or "Not supplied"),
                f"  Event: {_date(event.get('event_time'), True)}",
                "  Received: " + "; ".join(_date(v, True) for v in _items(event.get("received_times"))),
                f"  Delivery lag: {_lag(event.get('receipt_lag_seconds'))}",
                f"  Value: {_number(event.get('value'))} {event.get('unit') or ''}; posted limit: {_number(event.get('posted_limit_kmh'))} km/h",
                f"  Vendor: {event.get('vendor_severity') or 'not supplied'}; reference: {event.get('reference_urgency') or 'not supplied for this type'}",
                f"  Code meaning: {event.get('meaning') or event.get('dtc_meaning') or 'not supplied for this type'}",
                f"  Repair context: {event.get('repair_state') or 'not supplied'}",
            ])
        lines.append("Work-order evidence:")
        for order in _items(issue.get("work_orders")):
            closed = _date(order.get("closed_local")) if order.get("closed_local") else "Not closed in supplied record"
            lines.extend([
                f"  {order.get('wo_id', '')} | {order.get('status', '')}",
                f"  Opened: {_date(order.get('opened_local'))}; closed: {closed}",
                f"  Work recorded: {order.get('work_done', '')}",
                f"  Technician note / booking: {order.get('technician_note', '')}",
            ])
        if not issue.get("work_orders"):
            lines.append("  No supplied work order; this does not prove no repair occurred.")
    lines.extend(["", "Data quality & limits"])
    audit = report.get("audit", {})
    for key, label in _AUDIT_LABELS:
        if key in audit:
            value = _lag(audit[key]) if key == "max_lag_seconds" else _number(audit[key])
            lines.append(f"- {label}: {value}")
    lines.extend(f"- {note}" for note in _items(audit.get("notes")))
    lines.extend(["", "Driver comparison: what we can say"])
    for driver in _items(report.get("drivers")):
        lines.append(str(driver.get("title", "")))
        lines.extend(f"- {fact}" for fact in _items(driver.get("facts")))
        lines.append(f"Limit: {driver.get('uncertainty', '')}")
    lines.extend(["", "Reviewed / not in tonight’s list"])
    for item in _items(report.get("appendix")):
        lines.extend([
            f"- {item.get('title', '')}: {item.get('detail', '')}",
            f"  Alerts: {_ids(item.get('alert_ids'))}; work orders: {_ids(item.get('work_order_ids'))}",
        ])
    lines.extend(["", "Raw supplied files"])
    lines.extend(f"- {source}" for source in _items(report.get("sources")))
    lines.append("- Generated report.json (full evidence)")
    lines.extend(["", "All displayed event and work-order times use America/Toronto.",
                  "Missing repair evidence does not establish that a fault remains active."])
    return "\n".join(lines) + "\n"
