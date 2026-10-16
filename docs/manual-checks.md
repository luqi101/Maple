# Manual verification

Use only the supplied files. The updated information cutoff is September 21, 2026, **18:47:27 EDT**, including all ten Hamilton backfill receipts. Tomorrow's dispatch is September 22 at 06:00 EDT. The original [18:00 baseline](baseline-1800.md) stays separately documented.

## Build and view

- From the repository root, run `python3 app.py`, then open `output/index.html`. Confirm a terminal summary and `output/report.json` were generated without installing anything or supplying an API key.
- Confirm the browser shows **What needs me tonight?**, **Tonight’s top 3**, **Action list**, **Evidence & timing**, **Data quality & limits**, **Driver comparison: what we can say**, **Reviewed / not in tonight’s list**, and **Raw supplied files**.
- Confirm the snapshot date and dispatch deadline are clearly visible and do not change to the computer's current date. Check the page at a narrow viewport and in print preview for readable text and usable evidence sections.

## Action and evidence checks

- Count nine action items, with V-108, V-137, and V-151 as the top three; V-158 is fourth and V-133 fifth. V-113, V-111, V-126, and V-131 remain historical resolution checks. The wording must distinguish observed evidence from unknown resolution.
- Expand V-108 evidence. Find P0217 A-120811 at 12:05 EDT (107 C) and P0524 A-707191 at 15:41 (88 kPa), received at 18:47:00 and 18:47:15. Both are vendor-MEDIUM but reference-critical. They must form one vehicle action, with reference stop instructions; September 9 P0171 repair WO-5512 must not clear different September 21 codes.
- Expand V-137 evidence. Find A-784686, P0524, event time 14:32 EDT September 21, and the reference's immediate-stop instruction. Compare WO-5540 closing at 07:40 EDT. Confirm the board describes repaired P0217 separately and never turns a delayed pre-repair event into a new post-repair fault.
- Expand V-151 evidence. Find A-668410, P0300, September 20 at 15:09:50 EDT; its 24-hour inspection deadline has elapsed. Find A-927832 and 2,350 km overdue. Confirm WO-5541's October 5 oil/filter booking does not become a completed misfire repair or an invented mileage-based stop rule.
- Expand V-158 evidence. Find A-468820 at 17:09:01 EDT and WO-5543 opened at 17:30. The next step should confirm the existing booking against dispatch, rather than create a second work order or assume "first thing" means before 06:00.
- Check V-133's source A-280491: 108 km/h against a 60 km/h posted limit, giving a 48 km/h difference. Ensure missing-limit speed rows do not receive an invented exceedance.

## Data limitations and exclusions

- Confirm updated counts of 2,380 alerts and 2,246 matching-payload groups, including the original 2,370/2,236 baseline and ten unique backfill IDs. A grouped pair must preserve both IDs and receipt timestamps; both source CSVs remain separate and unchanged.
- Confirm 134 raw rows delayed over one hour, 131 Hamilton, and 21 over 24 hours. The new PDF confirms the gateway was unreliable, superseding the vendor note; it does not establish continuous outage duration or prove silence is clearance.
- Confirm all ten backfill events predate 18:00 EDT but were received 18:47:00–18:47:27. Check V-126 A-499391 yields 44 km/h excess, V-131 A-403125 retains an unknown excess because the limit is missing, and V-124 A-444816 P0171 retains next-service reference urgency. Missing-limit speeding count is 86.
- Confirm maintenance negatives are not overdue actions, dated readings retain their dates, and 40 vehicles split into 16 positive and 24 negative readings after grouping.
- Confirm 23 device/camera rows in the documented local update window are explained in reviewed evidence. V-123's unplugged events should not be described as post-repair recurrence. Single offline/unplugged events must not become a duration estimate.
- Confirm D-17 is not labelled the worst driver. Its 107 raw rows / 100 groups and V-142's 3,650 vehicle km must not become a driver risk rate. Firmware 4.2.1 is a comparison caveat.
- Check that vendor-HIGH P0420 rows are interpreted with the reference's LOW urgency, while vendor-MEDIUM P0524 remains visible as critical.

## Repeatability and hand-in

- Run `python3 -m unittest discover -s tests -v`; record the actual result and resolve failures before claiming success.
- Run `python3 app.py` again and confirm the snapshot, counts, and action order stay stable. Confirm identical-ID repeated ingestion does not inflate counts and conflicting same-ID payloads fail explicitly. Check original files plus `NEW_INFORMATION.pdf` and `hamilton_backfill.csv` remain unchanged.
- Compare `build_report(include_backfill=False)` with the [documented baseline](baseline-1800.md): 18:00 EDT, eight actions, V-137/V-151/V-158 top three. Default generation should include backfill without changing either raw CSV.
- Open raw-source links from the generated page and verify they resolve locally.
- Capture the genuine AI session using [these instructions](ai-session-instructions.md); do not replace it with a retrospective narrative. Verify the repository link and required submission forms separately.

These are verification instructions. A check is complete only after someone actually performs it; this file does not record a pass.
