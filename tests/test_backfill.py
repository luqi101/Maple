"""Backfill ingestion checks: synthetic merge fixtures and actual supplied rows."""

import csv
from pathlib import Path
import unittest

from maple.core import build_report, group_alerts, merge_alert_sources, parse_utc, repair_state


def synthetic_merge_row(**changes):
    """Synthetic CSV record used only to exercise ingestion conflicts/reloads."""
    row = {
        "alert_id": "SYN-BACKFILL-A-1",
        "vehicle_id": "SYN-V-1",
        "driver_id": "SYN-D-1",
        "alert_type": "engine_fault",
        "vendor_severity": "MEDIUM",
        "event_time_utc": "2026-09-21T16:05:00Z",
        "received_time_utc": "2026-09-21T22:47:00Z",
        "value": "107",
        "unit": "C",
        "posted_limit_kmh": "",
        "dtc_code": "P0217",
    }
    row.update(changes)
    return row


class MergeSourceTests(unittest.TestCase):
    def test_identical_id_and_payload_are_idempotent_with_source_provenance(self):
        row = synthetic_merge_row()
        merged, provenance, repeated = merge_alert_sources([
            ("synthetic-base.csv", [row]),
            ("synthetic-update.csv", [dict(row)]),
        ])
        self.assertEqual(merged, [row])
        self.assertCountEqual(provenance[row["alert_id"]], ["synthetic-base.csv", "synthetic-update.csv"])
        self.assertEqual(repeated, 1)

    def test_reloading_the_same_source_does_not_repeat_records_or_provenance(self):
        row = synthetic_merge_row()
        merged, provenance, repeated = merge_alert_sources([
            ("synthetic-update.csv", [row]),
            ("synthetic-update.csv", [dict(row)]),
        ])
        self.assertEqual(len(merged), 1)
        self.assertEqual(provenance[row["alert_id"]], ["synthetic-update.csv"])
        self.assertEqual(repeated, 1)

    def test_same_id_with_conflicting_unit_is_rejected(self):
        with self.assertRaises(ValueError):
            merge_alert_sources([
                ("synthetic-base.csv", [synthetic_merge_row()]),
                ("synthetic-update.csv", [synthetic_merge_row(unit="F")]),
            ])

    def test_distinct_ids_with_identical_event_payload_preserve_both_ids(self):
        first = synthetic_merge_row()
        second = synthetic_merge_row(alert_id="SYN-BACKFILL-A-2")
        merged, provenance, repeated = merge_alert_sources([
            ("synthetic-base.csv", [first]), ("synthetic-update.csv", [second]),
        ])
        self.assertEqual(len(merged), 2)
        self.assertEqual(repeated, 0)
        grouped = group_alerts(merged)
        self.assertEqual(len(grouped), 1)
        self.assertCountEqual(grouped[0]["alert_ids"], [first["alert_id"], second["alert_id"]])
        self.assertEqual(len(provenance), 2)


class SuppliedBackfillTests(unittest.TestCase):
    """These assertions name actual records from hamilton_backfill.csv."""

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.data_dir = cls.root / "data"
        cls.backfill_path = cls.root / "hamilton_backfill.csv"
        with (cls.data_dir / "alerts.csv").open(newline="", encoding="utf-8") as source:
            cls.original = list(csv.DictReader(source))
        with cls.backfill_path.open(newline="", encoding="utf-8") as source:
            cls.backfill = list(csv.DictReader(source))
        with (cls.data_dir / "work_orders.csv").open(newline="", encoding="utf-8") as source:
            cls.work_orders = list(csv.DictReader(source))
        cls.report = build_report(cls.data_dir)

    def test_supplied_backfill_has_ten_new_ids_and_preserves_original_rows(self):
        original_ids = {row["alert_id"] for row in self.original}
        backfill_ids = {row["alert_id"] for row in self.backfill}
        self.assertEqual(len(self.backfill), 10)
        self.assertEqual(len(backfill_ids), 10)
        self.assertFalse(original_ids & backfill_ids)
        merged, _, repeated = merge_alert_sources([
            ("alerts.csv", self.original), ("hamilton_backfill.csv", self.backfill),
        ])
        self.assertEqual(len(merged), 2380)
        self.assertEqual(repeated, 0)
        by_id = {row["alert_id"]: row for row in merged}
        self.assertTrue(all(by_id[row["alert_id"]] == row for row in self.original))

    def test_updated_audit_and_top_three(self):
        audit = self.report["audit"]
        self.assertEqual(audit["baseline_raw_alert_count"], 2370)
        self.assertEqual(audit["backfill_row_count"], 10)
        self.assertEqual(audit["raw_alert_count"], 2380)
        self.assertEqual(audit["event_group_count"], 2246)
        self.assertEqual(len(self.report["issues"]), 9)
        self.assertEqual([issue["vehicle_id"] for issue in self.report["issues"][:3]], ["V-108", "V-137", "V-151"])
        self.assertEqual(self.report["as_of"], "2026-09-21T18:47:27-04:00")
        self.assertEqual(self.report["update"]["baseline_top_three"], ["V-137", "V-151", "V-158"])
        self.assertTrue(self.report["update"]["notes"])

    def test_each_new_alert_retains_its_backfill_source_label(self):
        provenance = self.report["alert_provenance"]
        for row in self.backfill:
            with self.subTest(alert_id=row["alert_id"]):
                self.assertIn("hamilton_backfill.csv", provenance[row["alert_id"]])

    def test_v108_is_one_issue_with_both_critical_codes_and_original_timing(self):
        matches = [issue for issue in self.report["issues"] if issue["vehicle_id"] == "V-108"]
        self.assertEqual(len(matches), 1)
        evidence = {
            alert_id: event
            for event in matches[0]["evidence"]
            for alert_id in event["alert_ids"]
        }
        expected = {
            "A-120811": ("P0217", "2026-09-21T12:05:00-04:00", "2026-09-21T18:47:00-04:00"),
            "A-707191": ("P0524", "2026-09-21T15:41:00-04:00", "2026-09-21T18:47:15-04:00"),
        }
        for alert_id, (code, event_time, received_time) in expected.items():
            with self.subTest(alert_id=alert_id):
                event = evidence[alert_id]
                self.assertEqual(event["dtc_code"], code)
                self.assertEqual(event["vendor_severity"], "MEDIUM")
                self.assertTrue(event["reference_urgency"].startswith("Critical"))
                self.assertEqual(event["event_time"], event_time)
                self.assertIn(received_time, event["received_times"])
                self.assertEqual(event["repair_state"], "unknown")

    def test_old_lean_code_work_order_does_not_clear_new_v108_codes(self):
        faults = [row for row in self.backfill if row["vehicle_id"] == "V-108" and row["alert_type"] == "engine_fault"]
        self.assertEqual(len(faults), 2)
        old_order = next(order for order in self.work_orders if order["wo_id"] == "WO-5512")
        self.assertIn("P0171", old_order["technician_note"])
        for group in group_alerts(faults):
            with self.subTest(code=group["dtc_code"]):
                state = repair_state(group, [old_order])
                self.assertEqual(state["state"], "unknown")
                self.assertEqual(state["work_order_ids"], [])

    def test_repeated_backfill_path_does_not_duplicate_the_updated_report(self):
        repeated = build_report(self.data_dir, backfill_paths=[self.backfill_path, self.backfill_path])
        self.assertEqual(repeated["audit"]["raw_alert_count"], 2380)
        self.assertEqual(repeated["audit"]["event_group_count"], 2246)
        self.assertEqual(repeated["audit"]["repeated_input_row_count"], 10)
        self.assertEqual(len(repeated["issues"]), 9)
        self.assertEqual([issue["vehicle_id"] for issue in repeated["issues"]], [issue["vehicle_id"] for issue in self.report["issues"]])

    def test_original_baseline_remains_explicitly_reproducible(self):
        original = build_report(self.data_dir, include_backfill=False)
        self.assertEqual(original["audit"]["raw_alert_count"], 2370)
        self.assertEqual(original["audit"]["event_group_count"], 2236)
        self.assertEqual(original["as_of"], "2026-09-21T18:00:00-04:00")
        self.assertEqual(len(original["issues"]), 8)

    def test_backfill_receipt_time_does_not_replace_the_earlier_event_time(self):
        baseline_cutoff = parse_utc("2026-09-21T22:00:00Z")
        self.assertTrue(all(parse_utc(row["event_time_utc"]) < baseline_cutoff for row in self.backfill))
        self.assertTrue(all(parse_utc(row["received_time_utc"]) > baseline_cutoff for row in self.backfill))


if __name__ == "__main__":
    unittest.main()
