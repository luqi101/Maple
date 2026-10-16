# Maple Freight: Luqi

## How to run it

Requires Python 3.10 or newer. There are no packages to install, API keys, paid services, or runtime AI calls.

```sh
git clone https://github.com/luqi101/Maple.git
cd Maple
python3 app.py
open output/index.html
```

On other operating systems, open `output/index.html` in a browser. The command also writes `output/report.json` and a complete plain-text handover in `output/actions.txt`, and prints a short terminal summary. Use `python3 app.py --full-text` to print all evidence. Generated files are ignored by Git; rerun the command to recreate them. The supplied files stay unchanged.

Verified on Python 3.12/macOS. Python's `zoneinfo` needs an IANA timezone database, normally supplied by macOS/Linux. Other operating systems and older Python versions were not tested.

```sh
python3 -m unittest discover -s tests -v
```

The command automatically includes the supplied `hamilton_backfill.csv`. The updated information cutoff is **September 21, 2026, 18:47:27 America/Toronto (22:47:27 UTC)**, including the last received row. Tomorrow's dispatch remains **September 22 at 06:00 EDT (10:00 UTC)**. The original [18:00 baseline decision](docs/baseline-1800.md) is preserved separately. The report does not use today's date to age events.

## Tonight's top 3 for Maple Freight

1. **Item:** V-108 newly revealed critical engine faults. **Why it matters:** The supplied reference calls P0217 critical, stop vehicle; P0524 requires stopping immediately. Both new alerts are vendor-MEDIUM. **Evidence from the data:** A-120811 recorded P0217 at 12:05 EDT, 107 C; A-707191 recorded P0524 at 15:41 EDT, 88 kPa. They arrived at 18:47:00 and 18:47:15. WO-5512 closed September 9 for P0171, a different code, and does not clear these September 21 events. **Next action (who, by when):** Operations manager and maintenance lead: contact the vehicle/driver now, follow the reference stop instructions, and coordinate one inspection covering both faults before any dispatch. The readings are recorded evidence, not an independently confirmed diagnosis.
2. **Item:** V-137 oil-pressure alert. **Why it matters:** P0524 requires stopping immediately, although the vendor labels this event MEDIUM. **Evidence from the data:** A-784686 occurred September 21 at 14:32 EDT. WO-5540 closed at 07:40 and addressed P0217 coolant-temperature readings, a different code. All four supplied P0217 events and receipts precede closure; no post-repair P0217 recurrence is supplied. **Next action (who, by when):** Operations manager and maintenance lead: contact the vehicle/driver now, follow the reference's stop instruction, and obtain a maintenance decision before dispatch. V-108 appears first only because its latest critical event is later; both require immediate attention.
3. **Item:** V-151 misfire inspection and overdue-service coordination. **Why it matters:** P0300 calls for inspection within 24 hours; that interval has elapsed. **Evidence from the data:** A-668410 occurred September 20 at 15:09:50 EDT; the reference inspection deadline was September 21 at 15:09:50. A-927832 reports 2,350 km overdue at 06:00 September 21. WO-5541 books oil/filter service for October 5 and does not document a misfire repair. **Next action (who, by when):** Maintenance lead: arrange the misfire inspection tonight and review the service booking with dispatch before 06:00. The data supplies no mileage-based stop threshold.

## What changed after the new information

`NEW_INFORMATION.pdf` confirms Hamilton's cellular gateway was unreliable and reconnected at 18:47, delivering ten held alerts. This supersedes the vendor's normal-connectivity claim. The original [18:00 reasoning and top three](docs/baseline-1800.md) remain available: V-137, V-151, V-158. The updated top three are **V-108, V-137, V-151**. V-158 remains action 4: confirm whether WO-5543's "first thing" inspection precedes 06:00 dispatch; reuse the existing booking.

All ten new IDs are unique and absent from the original export. Their events occurred between 12:05 and 17:21:16 EDT, before the original snapshot; receipts are 18:47:00–18:47:27. The report advances its information cutoff to include those actual receipt times, while retaining event chronology. V-108's two reference-critical faults become one vehicle action, making **nine actions**. The eight other rows provide context: V-126's 104 against 60 km/h is a 44 km/h exceedance, below V-133's existing 48 km/h maximum; V-131's 131 km/h has no posted limit, so its excess is unknown. V-124's P0171 reference says next service; V-135's 87 against 80 km/h, two harsh events, and two idling rows do not displace the stronger supported actions. These records remain reviewable.

Combined counts are **2,380 rows / 2,246 payload groups**, with the same 134 suspicious pairs; **134** delivery lags exceed one hour, **131 Hamilton**, and 21 exceed 24 hours. Missing posted limits on speeding rows increase from 85 to 86. Source files remain separate and unchanged. Re-loading an identical alert ID is idempotent; a conflicting payload for an existing ID raises `ValueError` rather than overwriting evidence. Confirmed gateway unreliability does not establish a continuous outage interval, current mechanical condition, or that silence proves clearance.

Verification: **50 tests passed**, including repeated-backfill loading, conflicting-ID rejection, baseline reproduction, event/receipt separation, and V-108's unrelated-code repair history. The updated desktop/mobile page, source links, deterministic regeneration, and print generation were checked. Reproduce the old report separately with `python3 app.py --baseline --output-dir /tmp/maple-baseline-check`; default startup always includes the new information.

## What I built, and for whom

A printable operations action board for the manager arranging tonight's work and tomorrow's dispatch. Open the top three, review each item's source evidence and timing, then coordinate the listed next action using existing maintenance/dispatch channels. The updated board contains nine grouped actions, within the team's approximate ten-action capacity. It shows the reasoning and uncertainties instead of assigning every raw alert a priority label.

After the top three come V-158's existing inspection/dispatch coordination, a V-133 speeding-evidence review, and four historical misfire-resolution checks. V-133 has eight speeding events; A-280491 records 108 km/h against 60 km/h, a 48 km/h difference. The older P0300 records for V-113, V-111, V-126, and V-131 require checking resolution, not an assertion that those vehicles remain faulty.

Evidence sections retain original alert IDs, event and received times, relevant work orders, reviewed exclusions, and data limitations. `output/report.json` provides the same analysis for inspection. The board is advisory; it does not send instructions, modify work orders, or record completion.

Data normalization/grouping, issue formation, and prioritization are separate functions in `maple/core.py`; `maple/render.py` handles HTML/text presentation. The command-line entry point only reads inputs and writes reports. This is a reviewed report for the supplied snapshot, not a general live-alert classification service.

## Assumptions I made

- Work-order local timestamps mean `America/Toronto`, as required by the scenario; September dates are EDT, UTC minus four hours. Event time determines chronology and age. Received time describes delivery.
- The DTC reference supplies engine-fault urgency. A code is evidence for the reference's next action, not a confirmed mechanical diagnosis. A closed repair addresses the documented code; it does not establish future safety or resolve unrelated codes.
- Alerts matching on every supplied field except `alert_id` and `received_time_utc` are suspicious duplicate-event groups. All original IDs and receipt times remain available. This is a transparent grouping assumption despite the vendor's exactly-once claim.
- The original export has 2,370 rows and 2,236 matching-payload groups; with the ten supplied backfill rows, counts are 2,380 and 2,246. Both contain the same 134 suspicious pairs. Updated delays over one hour total 134, including 131 Hamilton; 21 exceed 24 hours. Maximum delay remains 29:58:29. The new PDF now confirms Hamilton gateway unreliability; the data does not establish the full extent of missing telemetry.
- Maintenance values below zero mean not yet due. There are readings for 40 vehicles: 16 positive and 24 negative after grouping. Most readings predate the snapshot; I do not project current mileage from fourteen-day totals.
- The vendor documents a 23:00–00:00 local update window. Twenty-three matching device/camera rows fall inside it. Isolated outside-window events do not establish continuous downtime. V-123's unplugged events precede its documented harness repair.
- D-17 has 107 raw rows and 100 matching-payload groups, associated with V-142 and firmware 4.2.1. V-142's 3,650 km are vehicle exposure, not a verified driver denominator. Assignment history and driver exposure are absent, so the board does not call D-17 the worst driver. Firmware differences are a comparison caveat, not proof that any event is false.
- Vendor severity is retained as evidence, not accepted as the action rule: 31 of 41 vendor-HIGH engine rows are P0420, which the reference labels LOW. Missing limits, units, invalid values, and other quality caveats remain visible in the report rather than becoming invented risk scores.
- The explicit action order is reference-critical first (latest event breaks ties), recent overdue inspection next, existing inspection/dispatch coordination, one strongest recorded-speed review, and older reference-high status checks newest-first. "Recent" means the snapshot's local day or previous local day; this is an ordering choice, not a safety threshold. Any capacity overflow remains visible. Repeated unresolved reports do not reset the earliest 24-hour reference inspection deadline.

## What I deliberately did NOT do (and why)

- Rank every alert high/medium/low: repeated, expected, resolved, and uncertain records would crowd out the limited action list.
- Add driver league tables, inferred driving exposure, invented thresholds, or mechanical diagnoses: the supplied data cannot support them.
- Build accounts, live ingestion, maps, hosting, notifications, or a completion database: a reproducible local snapshot covers the immediate decision.
- Call an LLM at runtime or introduce external data: the supplied reference and explicit rules make this snapshot explainable and reproducible.

## How I checked it's correct

The original baseline passed 37 automated tests and recorded desktop/mobile/print, repeatability, and fresh-public-clone checks; [the baseline record](docs/baseline-1800.md) preserves their scope. The adaptation now passes **50 tests**, also run successfully from a fresh public GitHub clone. Actual updated Chrome checks passed for nine cards, V-108/V-137/V-151 first, the exact 18:47:27 cutoff, grouped V-108 source/repair evidence, all raw-source links, and expanded evidence at 390 pixels without page overflow. Updated print generation, source hashes, original-input preservation, and deterministic regeneration passed. The public clone also verified both default and baseline startup paths and all source links/hashes; see [verification results](docs/verification.md) and [repeatable manual checks](docs/manual-checks.md).

I independently recomputed the ten new IDs, local event/receipt times, combined row/group counts, delivery lags, and missing-limit count directly from the supplied CSVs. Updated checks must cover backfill inclusion, V-108's grouped critical action, changed top three, original-baseline preservation, and identical-ID/conflicting-ID reload behavior, alongside the existing chronology, reference, grouping, renderer, and session-export regressions.

## AI use

- **Tools I used:** OpenAI Codex, including delegated agents, plus local Python and shell inspection.
- **What AI did for me:** Inspected the supplied data, calculated evidence, challenged customer/vendor claims, planned the workflow, and generated implementation, tests, and documentation for review.
- **One thing AI got wrong or incomplete, and how I caught it:** An initial maintenance summary tentatively counted 17 overdue vehicles. Recomputing after matching-payload grouping showed 16 positive and 24 negative readings across 40 vehicles. The documented count was corrected. AI also cannot establish a driver ranking from vehicle mileage alone.
- **Link to / export of my AI session:** [Original visible-message extraction](docs/ai-session.md), mechanically copied from this conversation's verified local VS Code session log by [the extraction script](scripts/export_session.py). It preserves the actual user prompts and explicitly visible assistant commentary/final messages in order, with labelled local-path/credential redactions. Its header records provenance and the extraction cutoff. This is not a native UI export or a complete tool/agent trace; hidden instructions, reasoning, tools, and peer-agent payloads are excluded. See [the session hand-in instructions](docs/ai-session-instructions.md) for an original UI export if available.

## If I had two more days

Validate the action order with the operations manager, add a verified resolution/assignment workflow and audit history, and test realistic maintenance handovers. Obtain driver-level exposure and assignment history before comparing drivers. Investigate firmware sensitivity, gateway recovery, and the completeness of delayed Hamilton data with the vendor. Expand ingestion validation and accessibility checks before considering live use.
