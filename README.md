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

The board is a fixed operational snapshot: **September 21, 2026, 18:00 America/Toronto (22:00 UTC)**. Tomorrow's dispatch is **September 22 at 06:00 EDT (10:00 UTC)**. It does not use today's date to age these events.

## Tonight's top 3 for Maple Freight

1. **Item:** V-137 oil-pressure alert. **Why it matters:** The supplied reference says P0524 means low engine oil pressure and requires stopping immediately, although the vendor labels this event MEDIUM. **Evidence from the data:** A-784686 occurred September 21 at 14:32 EDT. WO-5540 closed at 07:40 that morning and addressed P0217 coolant-temperature readings, a different code. All four P0217 events and receipts precede closure; no post-repair P0217 recurrence is supplied. **Next action (who, by when):** Operations manager and maintenance lead: contact the vehicle/driver now, follow the reference's stop instruction, and obtain a maintenance decision before dispatch.
2. **Item:** V-151 misfire inspection and overdue-service coordination. **Why it matters:** P0300 calls for inspection within 24 hours; that interval has elapsed by the snapshot. **Evidence from the data:** A-668410 occurred September 20 at 15:09:50 EDT, making its reference inspection deadline September 21 at 15:09:50. A-927832 reports 2,350 km overdue at 06:00 September 21. WO-5541 books oil/filter service for October 5; it does not document a misfire repair. **Next action (who, by when):** Maintenance lead: arrange the misfire inspection tonight and review the service booking with dispatch before 06:00. The data supplies no mileage-based stop threshold.
3. **Item:** Confirm V-158 inspection timing against dispatch. **Why it matters:** Its misfire already has an open work order; the useful action is coordination. **Evidence from the data:** P0300 A-468820 occurred September 21 at 17:09:01 EDT. WO-5543 opened at 17:30 and books inspection "first thing" September 22, without an exact time. **Next action (who, by when):** Maintenance lead and dispatcher: confirm tonight whether that booking precedes 06:00 dispatch and decide the vehicle's assignment. Reuse WO-5543.

## What I built, and for whom

A printable operations action board for the manager arranging tonight's work and tomorrow's dispatch. Open the top three, review each item's source evidence and timing, then coordinate the listed next action using existing maintenance/dispatch channels. The board contains eight grouped actions, within the team's approximate ten-action capacity. It shows the reasoning and uncertainties instead of assigning every raw alert a priority label.

The remaining actions are a V-133 speeding-evidence review and four historical misfire-resolution checks. V-133 has eight speeding events and six of the largest supplied known-limit exceedances; A-280491 records 108 km/h against 60 km/h, a 48 km/h difference. The older P0300 records for V-113, V-111, V-126, and V-131 require checking resolution, not an assertion that those vehicles remain faulty.

Evidence sections retain original alert IDs, event and received times, relevant work orders, reviewed exclusions, and data limitations. `output/report.json` provides the same analysis for inspection. The board is advisory; it does not send instructions, modify work orders, or record completion.

Data normalization/grouping, issue formation, and prioritization are separate functions in `maple/core.py`; `maple/render.py` handles HTML/text presentation. The command-line entry point only reads inputs and writes reports. This is a reviewed report for the supplied snapshot, not a general live-alert classification service.

## Assumptions I made

- Work-order local timestamps mean `America/Toronto`, as required by the scenario; September dates are EDT, UTC minus four hours. Event time determines chronology and age. Received time describes delivery.
- The DTC reference supplies engine-fault urgency. A code is evidence for the reference's next action, not a confirmed mechanical diagnosis. A closed repair addresses the documented code; it does not establish future safety or resolve unrelated codes.
- Alerts matching on every supplied field except `alert_id` and `received_time_utc` are suspicious duplicate-event groups. All original IDs and receipt times remain available. This is a transparent grouping assumption despite the vendor's exactly-once claim.
- The supplied export has 2,370 rows and 2,236 matching-payload groups, including 134 suspicious pairs. There are 124 rows delayed over one hour, 121 at Hamilton; 21 exceed 24 hours. The maximum delay is 29:58:29. This establishes a delivery pattern, not its cause.
- Maintenance values below zero mean not yet due. There are readings for 40 vehicles: 16 positive and 24 negative after grouping. Most readings predate the snapshot; I do not project current mileage from fourteen-day totals.
- The vendor documents a 23:00–00:00 local update window. Twenty-three matching device/camera rows fall inside it. Isolated outside-window events do not establish continuous downtime. V-123's unplugged events precede its documented harness repair.
- D-17 has 107 raw rows and 100 matching-payload groups, associated with V-142 and firmware 4.2.1. V-142's 3,650 km are vehicle exposure, not a verified driver denominator. Assignment history and driver exposure are absent, so the board does not call D-17 the worst driver. Firmware differences are a comparison caveat, not proof that any event is false.
- Vendor severity is retained as evidence, not accepted as the action rule: 31 of 41 vendor-HIGH engine rows are P0420, which the reference labels LOW. Missing limits, units, invalid values, and other quality caveats remain visible in the report rather than becoming invented risk scores.
- The explicit action order is reference-critical first, recent overdue inspection second, existing inspection/dispatch coordination third, one strongest recorded-speed review fourth, and older reference-high status checks newest-first. "Recent" means the snapshot's local day or previous local day; this is an ordering choice, not a safety threshold. Any capacity overflow remains visible. Repeated unresolved reports do not reset the earliest 24-hour reference inspection deadline.

## What I deliberately did NOT do (and why)

- Rank every alert high/medium/low: repeated, expected, resolved, and uncertain records would crowd out the limited action list.
- Add driver league tables, inferred driving exposure, invented thresholds, or mechanical diagnoses: the supplied data cannot support them.
- Build accounts, live ingestion, maps, hosting, notifications, or a completion database: a reproducible local snapshot covers the immediate decision.
- Call an LLM at runtime or introduce external data: the supplied reference and explicit rules make this snapshot explainable and reproducible.

## How I checked it's correct

**37 automated tests passed** with the command above. They use clearly labelled synthetic fixtures for delayed pre-repair receipts, post-repair events, unrelated-code repairs, DTC/vendor disagreement, duplicate provenance, negative maintenance values, unavailable driver denominators, and inspection-deadline regressions. Supplied-data checks verify counts, eight grouped actions, top-three order, and combined V-151 evidence. Renderer and session-export tests check escaping, source links, work-order visibility, and exclusion of hidden/private session material.

Real headless Chrome checks passed for the eight cards, top-three order, expandable evidence, local raw-file/JSON links, and work-order facts. Desktop screenshots were visually reviewed. A mobile overflow bug with evidence open was fixed; the 390-pixel recheck passed with every evidence section expanded. Print-to-PDF generation passed and extracted text includes the key alert and booking evidence. See [verification results](docs/verification.md) and [repeatable manual checks](docs/manual-checks.md). Cross-browser, real-device, and operational validation remain untested.

I also recomputed the counts directly from the supplied CSVs during investigation. The key counterexamples are V-137's new P0524 versus its repaired P0217, V-151's overdue misfire versus an unrelated future service, and D-17's missing driver-level denominator.

## AI use

- **Tools I used:** OpenAI Codex, including delegated agents, plus local Python and shell inspection.
- **What AI did for me:** Inspected the supplied data, calculated evidence, challenged customer/vendor claims, planned the workflow, and generated implementation, tests, and documentation for review.
- **One thing AI got wrong or incomplete, and how I caught it:** An initial maintenance summary tentatively counted 17 overdue vehicles. Recomputing after matching-payload grouping showed 16 positive and 24 negative readings across 40 vehicles. The documented count was corrected. AI also cannot establish a driver ranking from vehicle mileage alone.
- **Link to / export of my AI session:** [Original visible-message extraction](docs/ai-session.md), mechanically copied from this conversation's verified local VS Code session log by [the extraction script](scripts/export_session.py). It preserves the actual user prompts and explicitly visible assistant commentary/final messages in order, with labelled local-path/credential redactions. Its header records provenance and the extraction cutoff. This is not a native UI export or a complete tool/agent trace; hidden instructions, reasoning, tools, and peer-agent payloads are excluded. See [the session hand-in instructions](docs/ai-session-instructions.md) for an original UI export if available.

## If I had two more days

Validate the action order with the operations manager, add a verified resolution/assignment workflow and audit history, and test the board with realistic maintenance handovers. Obtain driver-level exposure and assignment history before comparing drivers. Investigate firmware sensitivity and Hamilton delivery delays with the vendor using the recorded evidence. Expand ingestion validation and accessibility checks before considering live use.
