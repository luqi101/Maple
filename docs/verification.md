# Verification record

Challenge build date: October 16, 2026. The report's operational clock remains September 21, 2026, 18:00 America/Toronto.

## Passed

- `python3 app.py`: generated HTML, JSON, plain-text evidence handover, and terminal summary from the supplied inputs with no installed application dependencies or API keys.
- Repeated generation produced byte-identical HTML, JSON, and text. All eight supplied files remain byte-identical to the baseline input commit.
- `python3 -m unittest discover -s tests -v`: **37 tests passed**. Tests use the supplied data or explicitly synthetic fixtures, with no network calls.
- A fresh clone from the **public GitHub repository** at commit `9d8d395f2d8edea1a915f40d4eee0f112dfe4781` independently ran `python3 app.py` and all 37 tests successfully. Relative raw-source links, source SHA-256 hashes, the eight priorities, and an unchanged Git working tree were verified in that clone. The subsequent hand-in commit changes documentation/session provenance only.
- Independent CSV recomputation: 2,370 raw alerts, 2,236 payload groups, 134 suspicious pairs; 124 raw delivery lags over one hour, 121 Hamilton, 21 over one day; maintenance readings for 40 vehicles, 16 positive and 24 negative.
- Actual Chrome headless desktop inspection at 1440 × 1100: eight action cards; top three V-137/V-151/V-158; expected headings; no document-level horizontal overflow. Screenshot visually inspected.
- Browser evidence expansion: V-137's WO-5540 closure at 07:40 EDT, V-151's October 5 booking, V-158's "first thing" note, and original source IDs are visible.
- All five raw-source links and `report.json` resolve to local files.
- Corrected mobile recheck at 390 × 844: with **all** details open, viewport/client/document width are all 390 pixels. Wide evidence tables scroll within their own containers. The corrected screenshot was visually inspected.
- Print-to-PDF generation succeeded. Extracted PDF text contains A-784686, WO-5540, the October 5 service booking, and the "first thing" inspection note. The first printed page was rendered and visually inspected.
- Session extraction tests verify that hidden/system/developer/reasoning/tool material is excluded and that redactions are labelled. The actual visible-message artifact has provenance and a cutoff, rather than a fabricated transcript.

## Problems found and corrected

- Generic critical-fault wording initially assumed P0524. A synthetic P0217 probe exposed this; wording now uses the actual supplied code, meaning, severity, and reference. Regression test passes.
- A recent misfire could initially be described as overdue even with a future deadline. Deadlines now compare against the fixed snapshot and retain the earliest unaddressed event across repeats. Both regression tests pass.
- Expanded evidence tables initially widened the mobile document to 760 pixels. The grid's minimum-width behavior was corrected, then the 390-pixel browser check passed.
- A preliminary investigation count of 17 overdue vehicles was corrected to 16 after matching-payload grouping. It is disclosed in the README's AI-use section.

## Not tested or not established

- Other browser engines, real mobile devices, screen readers, Windows, and older Python versions.
- Live ingestion, multi-user task state, acknowledgement/resolution workflows, and external notifications; these are outside the build.
- Current mechanical condition, dispatch clearance, actual driver exposure, firmware causality, and the cause of Hamilton delays; the export cannot establish these.
- Intent Card and Final Submission form completion; their URLs are on the facilitator's start page, not supplied in this workspace. Repository publication does not submit those forms.
