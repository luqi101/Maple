#!/usr/bin/env python3
"""Generate Maple Freight's offline advisory report from supplied data."""

import argparse
import json
import os
import sys
from pathlib import Path

from maple.core import DEFAULT_DATA, build_report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA, help="Supplied CSV directory")
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent / "output")
    parser.add_argument("--full-text", action="store_true", help="Print the complete evidence handover as well as writing it to actions.txt")
    parser.add_argument("--baseline", action="store_true", help="Reproduce the original 18:00 snapshot without the assessment backfill")
    args = parser.parse_args()
    try:
        report = build_report(args.data_dir, include_backfill=not args.baseline)
        locations = report.pop("source_locations")
        report["source_links"] = {name: Path(os.path.relpath(Path(locations[name]), args.output_dir.resolve())).as_posix() for name in report["sources"]}
        from maple.render import render_html, render_text
        args.output_dir.mkdir(parents=True, exist_ok=True)
        (args.output_dir / "index.html").write_text(render_html(report), encoding="utf-8")
        (args.output_dir / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        handover = render_text(report)
        (args.output_dir / "actions.txt").write_text(handover, encoding="utf-8")
        if args.full_text:
            print(handover)
        else:
            print("MAPLE FREIGHT — What needs me tonight?")
            print(f"Fixed snapshot: {report['as_of']}; dispatch September 22, 06:00 EDT")
            if "update" in report:
                print("What changed after the new information: 10 held Hamilton alerts included; baseline V-137/V-151/V-158 → updated " + "/".join(report['update']['updated_top_three']))
            print(f"{len(report['issues'])} grouped actions; {report['audit']['raw_alert_count']:,} raw alerts / {report['audit']['event_group_count']:,} payload groups")
            for index, issue in enumerate(report["issues"][:3], 1):
                print(f"{index}. {issue['vehicle_id']}: {issue['title']}")
                print(f"   Next: {issue['next_action']}")
        print(f"\nOpen in your browser: {(args.output_dir / 'index.html').resolve()}")
        print(f"Machine-readable evidence: {(args.output_dir / 'report.json').resolve()}")
        print(f"Complete text handover: {(args.output_dir / 'actions.txt').resolve()}")
        return 0
    except (OSError, ValueError, KeyError) as error:
        print(f"Report generation failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
