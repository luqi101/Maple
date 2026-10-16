# Verification record

Challenge build date: October 16, 2026. Updated report cutoff: September 21, 2026, **18:47:27 America/Toronto**. Original baseline cutoff: 18:00 EDT.

## Adaptation verification

- Personally read `NEW_INFORMATION.pdf` and all ten `hamilton_backfill.csv` rows. The PDF confirms Hamilton's unreliable gateway and held-alert delivery at 18:47, superseding the earlier vendor connectivity claim.
- Independent CSV recomputation passed: ten distinct new alert IDs, zero overlap with original IDs, all Hamilton; all event times precede 18:00 EDT; receipts run 18:47:00–18:47:27. Combined 2,380 rows / 2,246 payload groups; 134 suspicious pairs; 134 delays over one hour, 131 Hamilton; 21 delays over 24 hours; 86 missing-limit speeding rows.
- V-108's two vendor-MEDIUM/reference-critical records verified directly: A-120811 P0217 at 12:05 EDT, 107 C; A-707191 P0524 at 15:41 EDT, 88 kPa. Earlier WO-5512 addressed September 9 P0171, not these faults.
- Preserved the original top-three text directly from Git commit `af7eb03` in [baseline-1800.md](baseline-1800.md) before editing the updated README.
- `python3 -m unittest discover -s tests -v`: **50 tests passed**, including 12 focused backfill checks and an updated-render regression. Identical repeated ingestion produces the same 2,380 rows/2,246 groups; conflicting ID payloads are rejected.
- `python3 app.py`: nine actions, 18:47:27 cutoff, V-108/V-137/V-151 first. `python3 app.py --baseline --output-dir /tmp/maple-baseline-check` separately reproduces 18:00, eight actions, V-137/V-151/V-158 first.
- Actual updated headless Chrome checks passed: nine cards, exact cutoff, before/after notice, grouped V-108 records/source labels/WO-5512, all eight raw-file/JSON links, and 390-pixel expanded-evidence layout without page overflow. Updated print-to-PDF generation passed; cross-browser and real-device checks remain untested.
- Repeated generation produced byte-identical HTML, JSON, and text. All eight original supplied files remain byte-identical to `af7eb03`. Every source link and source SHA-256 hash, including the new PDF/CSV, was verified. All ten normalized held records and original IDs are accessible in JSON with backfill provenance.
- Fresh public GitHub clone of adaptation commit `1c37a839fc48c6e24fc22a2eeaa5dbf694f06466` passed default generation and **all 50 tests**. The clone also reproduced the original baseline with `--baseline`; verified updated counts/top three/as-of, all source links and hashes, both new inputs, and a clean Git working tree. The final hand-in follow-up changes documentation/session provenance only.

## Baseline passes recorded before new information

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
- Current mechanical condition, dispatch clearance, actual driver exposure, firmware causality, and the full extent/duration of missing Hamilton telemetry. The new PDF confirms gateway unreliability; silence does not establish clearance.
- Intent Card and Final Submission form completion; their URLs are on the facilitator's start page, not supplied in this workspace. Repository publication does not submit those forms.
