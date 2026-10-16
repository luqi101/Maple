# Original 18:00 baseline, before Hamilton backfill

Preserved from submitted commit `af7eb03` before adapting to `NEW_INFORMATION.pdf` and `hamilton_backfill.csv`. This records the original decision and its original information limits; it is not the updated action list. The exact original README and verification record remain in that Git commit.

The original Intent Card form contents were not supplied. This preserves the repository's original reasoning, not a reconstructed or claimed form submission.

Snapshot: September 21, 2026, **18:00 EDT (22:00 UTC)**. Dispatch: September 22, **06:00 EDT**. Only the original export was available: 2,370 rows, 2,236 payload groups, 134 suspicious duplicate pairs; 124 delays over one hour, including 121 Hamilton, and 21 over 24 hours. Vendor notes claimed normal gateway connectivity. The export established a delivery pattern but did not independently establish its cause.

## Original top three and reasoning

1. **Item:** V-137 oil-pressure alert. **Why it matters:** The supplied reference says P0524 means low engine oil pressure and requires stopping immediately, although the vendor labels this event MEDIUM. **Evidence from the data:** A-784686 occurred September 21 at 14:32 EDT. WO-5540 closed at 07:40 that morning and addressed P0217 coolant-temperature readings, a different code. All four P0217 events and receipts precede closure; no post-repair P0217 recurrence is supplied. **Next action (who, by when):** Operations manager and maintenance lead: contact the vehicle/driver now, follow the reference's stop instruction, and obtain a maintenance decision before dispatch.
2. **Item:** V-151 misfire inspection and overdue-service coordination. **Why it matters:** P0300 calls for inspection within 24 hours; that interval has elapsed by the snapshot. **Evidence from the data:** A-668410 occurred September 20 at 15:09:50 EDT, making its reference inspection deadline September 21 at 15:09:50. A-927832 reports 2,350 km overdue at 06:00 September 21. WO-5541 books oil/filter service for October 5; it does not document a misfire repair. **Next action (who, by when):** Maintenance lead: arrange the misfire inspection tonight and review the service booking with dispatch before 06:00. The data supplies no mileage-based stop threshold.
3. **Item:** Confirm V-158 inspection timing against dispatch. **Why it matters:** Its misfire already has an open work order; the useful action is coordination. **Evidence from the data:** P0300 A-468820 occurred September 21 at 17:09:01 EDT. WO-5543 opened at 17:30 and books inspection "first thing" September 22, without an exact time. **Next action (who, by when):** Maintenance lead and dispatcher: confirm tonight whether that booking precedes 06:00 dispatch and decide the vehicle's assignment. Reuse WO-5543.


## Original remaining actions and checks

The original eight actions continued with V-133's strongest recorded speeding evidence, then historical P0300 resolution checks for V-113, V-111, V-126, and V-131. D-17 was not labelled the worst driver; vehicle kilometres were not treated as driver exposure. Negative maintenance readings were not overdue. V-123's unplugged records preceded its harness repair; V-118's recurring device/camera events matched the documented update window.

The original verification record at `af7eb03` reports 37 passing tests, successful desktop/mobile/print checks, deterministic outputs, and successful execution from a public clone of preceding code commit `9d8d395f2d8edea1a915f40d4eee0f112dfe4781`. Those are baseline results, not automatic verification of the later adaptation.

## What later evidence changes

The later PDF explicitly confirms an unreliable Hamilton gateway and a held ten-alert delivery at 18:47. The ten unique records occurred before the original 18:00 snapshot but were received afterward, so they were unavailable to this baseline. V-108's newly revealed reference-critical P0217/P0524 faults add one grouped action and change the top three. The updated README records that decision and the later information cutoff.
