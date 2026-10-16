"""Risk-focused rules checks; SYN-* records below are synthetic fixtures.

The source-data integration checks use the supplied CSVs without modifying them.
"""

import csv
from datetime import timedelta
import json
from pathlib import Path
import unittest

from maple.core import (
    SNAPSHOT,
    build_report,
    driver_context,
    form_issues,
    group_alerts,
    maintenance_state,
    parse_local,
    parse_utc,
    reference_urgency,
    repair_state,
)


def synthetic_alert(**changes):
    """A deliberately synthetic CSV-shaped record, never customer evidence."""
    row = {
        "alert_id": "SYN-A-1",
        "vehicle_id": "SYN-V-1",
        "driver_id": "SYN-D-1",
        "alert_type": "engine_fault",
        "vendor_severity": "LOW",
        "event_time_utc": "2026-09-21T11:00:00Z",
        "received_time_utc": "2026-09-21T18:00:00Z",
        "value": "105",
        "unit": "C",
        "posted_limit_kmh": "",
        "dtc_code": "P0217",
    }
    row.update(changes)
    return row


def synthetic_work_order(**changes):
    row = {
        "wo_id": "SYN-WO-1",
        "vehicle_id": "SYN-V-1",
        "opened_local": "2026-09-20 16:00",
        "closed_local": "2026-09-21 07:40",
        "status": "Closed",
        "work_done": "Synthetic repair for test only",
        "technician_note": "P0217 readings resolved for this synthetic case.",
    }
    row.update(changes)
    return row


def only_group(*rows):
    groups = group_alerts(list(rows))
    if len(groups) != 1:
        raise AssertionError(f"Expected one synthetic event, got {len(groups)}")
    return groups[0]


class TimestampTests(unittest.TestCase):
    def test_scenario_snapshot_is_september_21_at_18_eastern(self):
        self.assertIsNotNone(SNAPSHOT.utcoffset())
        self.assertEqual(SNAPSHOT, parse_utc("2026-09-21T22:00:00Z"))

    def test_work_order_local_time_uses_toronto_scenario_offset(self):
        local = parse_local("2026-09-21 07:40")
        self.assertEqual(local.utcoffset(), timedelta(hours=-4))
        self.assertEqual(local, parse_utc("2026-09-21T11:40:00Z"))
        self.assertEqual(parse_utc("2026-09-21T11:40:00Z").utcoffset(), timedelta(0))


class EventGroupingTests(unittest.TestCase):
    def test_redelivery_preserves_both_ids_and_delivery_times(self):
        first = synthetic_alert()
        second = synthetic_alert(
            alert_id="SYN-A-2", received_time_utc="2026-09-21T18:00:03Z"
        )
        group = only_group(first, second)
        self.assertCountEqual(group["alert_ids"], ["SYN-A-1", "SYN-A-2"])
        self.assertEqual(group["event_time"], parse_utc(first["event_time_utc"]))
        self.assertEqual(len(group["received_times"]), 2)
        self.assertEqual(len(group["raw_rows"]), 2)
        self.assertEqual(group["value"], 105.0)
        self.assertIsNone(group["posted_limit_kmh"])

    def test_different_event_times_are_distinct_despite_matching_payload(self):
        groups = group_alerts([
            synthetic_alert(),
            synthetic_alert(alert_id="SYN-A-2", event_time_utc="2026-09-21T12:00:00Z"),
        ])
        self.assertEqual(len(groups), 2)

    def test_different_codes_or_values_do_not_merge(self):
        groups = group_alerts([
            synthetic_alert(),
            synthetic_alert(alert_id="SYN-A-2", dtc_code="P0524"),
            synthetic_alert(alert_id="SYN-A-3", value="106"),
        ])
        self.assertEqual(len(groups), 3)


class RepairEvidenceTests(unittest.TestCase):
    def test_old_event_received_after_repair_is_not_a_new_fault(self):
        group = only_group(synthetic_alert())
        state = repair_state(group, [synthetic_work_order()])
        self.assertEqual(state["state"], "documented_repair")
        self.assertEqual(state["work_order_ids"], ["SYN-WO-1"])
        self.assertLess(group["event_time"], parse_local("2026-09-21 07:40"))
        self.assertGreater(parse_utc("2026-09-21T18:00:00Z"), parse_local("2026-09-21 07:40"))

    def test_event_after_matching_repair_is_a_post_repair_event(self):
        group = only_group(synthetic_alert(event_time_utc="2026-09-21T12:00:00Z"))
        state = repair_state(group, [synthetic_work_order()])
        self.assertEqual(state["state"], "post_repair_event")
        self.assertEqual(state["work_order_ids"], ["SYN-WO-1"])

    def test_an_unrelated_code_does_not_resolve_this_fault(self):
        state = repair_state(
            only_group(synthetic_alert()),
            [synthetic_work_order(technician_note="P0420 repaired in this synthetic case.")],
        )
        self.assertEqual(state["state"], "unknown")
        self.assertEqual(state["work_order_ids"], [])

    def test_code_in_work_description_is_repair_evidence(self):
        state = repair_state(
            only_group(synthetic_alert()),
            [synthetic_work_order(work_done="Synthetic P0217 repair", technician_note="")],
        )
        self.assertEqual(state["state"], "documented_repair")

    def test_another_vehicles_repair_does_not_resolve_this_fault(self):
        state = repair_state(
            only_group(synthetic_alert()),
            [synthetic_work_order(vehicle_id="SYN-V-2")],
        )
        self.assertEqual(state["state"], "unknown")

    def test_open_work_order_is_not_a_completed_repair(self):
        state = repair_state(
            only_group(synthetic_alert()),
            [synthetic_work_order(status="Open", closed_local="")],
        )
        self.assertEqual(state["state"], "unknown")


class UrgencyAndMaintenanceTests(unittest.TestCase):
    def test_reference_urgency_does_not_inherit_vendor_severity(self):
        reference = {"P0217": {"reference_urgency": "Critical - stop vehicle, risk of engine damage"}}
        low_vendor_group = only_group(synthetic_alert(vendor_severity="LOW"))
        self.assertEqual(
            reference_urgency(low_vendor_group, reference),
            "Critical - stop vehicle, risk of engine damage",
        )

    def test_missing_reference_is_explicitly_unknown(self):
        self.assertEqual(
            reference_urgency(only_group(synthetic_alert(dtc_code="SYN-UNKNOWN")), {}),
            "Unknown — reference unavailable",
        )

    def test_maintenance_sign_is_not_reversed(self):
        for value, expected in [(-420.0, "not_yet_due"), (0.0, "due"), (420.0, "overdue"), (None, "unknown")]:
            with self.subTest(value=value):
                self.assertEqual(maintenance_state(value), expected)


class DriverExposureTests(unittest.TestCase):
    def test_vehicle_distance_never_becomes_driver_distance(self):
        groups = group_alerts([
            synthetic_alert(),
            synthetic_alert(alert_id="SYN-A-2", received_time_utc="2026-09-21T18:00:03Z"),
        ])
        vehicles = {
            "SYN-V-1": {
                "vehicle_id": "SYN-V-1",
                "assigned_driver": "SYN-D-1",
                "device_firmware": "4.2.1",
                "km_driven_14d": "3650",
            }
        }
        context = driver_context("SYN-D-1", groups, vehicles)
        self.assertEqual(context["raw_alert_count"], 2)
        self.assertEqual(context["event_group_count"], 1)
        self.assertEqual(context["vehicle_km"], 3650)
        self.assertIsNone(context["driver_km"])
        self.assertEqual(context["vehicles"], ["SYN-V-1"])
        self.assertTrue(context["exposure_note"])


class IssueFormationRegressionTests(unittest.TestCase):
    """Synthetic cases for DTC-specific language and actual inspection timing."""

    def setUp(self):
        self.vehicles = {
            "SYN-V-1": {
                "vehicle_id": "SYN-V-1",
                "depot": "Synthetic test depot",
                "assigned_driver": "SYN-D-1",
                "device_firmware": "4.3.0",
                "km_driven_14d": "1000",
            }
        }
        self.references = {
            "P0217": {
                "meaning": "Engine coolant over-temperature condition",
                "reference_urgency": "Critical - stop vehicle, risk of engine damage",
            },
            "P0300": {
                "meaning": "Random/multiple cylinder misfire detected",
                "reference_urgency": "High - inspect within 24 h",
            },
        }

    def issue_from(self, *rows):
        issues = form_issues(group_alerts(list(rows)), self.vehicles, self.references, [])
        self.assertEqual(len(issues), 1)
        return issues[0]

    def test_critical_coolant_code_does_not_invent_an_oil_pressure_fault(self):
        issue = self.issue_from(synthetic_alert())
        wording = (issue["title"] + " " + issue["why"]).lower().replace("-", " ")
        self.assertIn("p0217", wording)
        self.assertNotIn("p0524", wording)
        self.assertNotIn("oil pressure", wording)

    def test_recent_misfire_with_future_deadline_is_not_called_overdue(self):
        issue = self.issue_from(synthetic_alert(
            dtc_code="P0300", value="", unit="",
            event_time_utc="2026-09-21T21:30:00Z",
            received_time_utc="2026-09-21T21:30:05Z",
        ))
        self.assertEqual(issue["inspection_deadline"], "2026-09-22T17:30:00-04:00")
        self.assertIs(issue["inspection_overdue"], False)
        self.assertNotIn("overdue", issue["title"].lower())
        self.assertNotIn("passed", issue["status"].lower())
        self.assertNotIn("already passed", issue["deadline"].lower())

    def test_repeated_unaddressed_misfires_keep_the_earliest_deadline(self):
        issue = self.issue_from(
            synthetic_alert(
                alert_id="SYN-A-EARLIER", dtc_code="P0300", value="", unit="",
                event_time_utc="2026-09-20T19:00:00Z",
                received_time_utc="2026-09-20T19:00:05Z",
            ),
            synthetic_alert(
                alert_id="SYN-A-LATER", dtc_code="P0300", value="", unit="",
                event_time_utc="2026-09-21T21:30:00Z",
                received_time_utc="2026-09-21T21:30:05Z",
            ),
        )
        self.assertEqual(issue["inspection_deadline"], "2026-09-21T15:00:00-04:00")
        self.assertIs(issue["inspection_overdue"], True)
        self.assertCountEqual(issue["alert_ids"], ["SYN-A-EARLIER", "SYN-A-LATER"])


class SuppliedDataIntegrationTests(unittest.TestCase):
    """Regression checks against the supplied challenge files, not fixtures."""

    @classmethod
    def setUpClass(cls):
        cls.data_dir = Path(__file__).resolve().parents[1] / "data"
        with (cls.data_dir / "alerts.csv").open(newline="", encoding="utf-8") as source:
            cls.alerts = list(csv.DictReader(source))
        cls.alert_by_id = {row["alert_id"]: row for row in cls.alerts}
        cls.report = build_report(cls.data_dir)

    def test_audit_counts_include_suspected_redeliveries(self):
        audit = self.report["audit"]
        self.assertEqual(audit["raw_alert_count"], 2370)
        self.assertEqual(audit["event_group_count"], 2236)
        self.assertEqual(audit["suspected_duplicate_pairs"], 134)

    def test_board_has_eight_grouped_issues_and_expected_dispatch_priorities(self):
        issues = self.report["issues"]
        self.assertEqual(len(issues), 8)
        self.assertEqual([issue["vehicle_id"] for issue in issues[:3]], ["V-137", "V-151", "V-158"])
        for issue in issues:
            with self.subTest(vehicle=issue["vehicle_id"]):
                self.assertTrue(issue["alert_ids"])
                self.assertTrue(issue["evidence"])
                self.assertTrue(all(alert_id in self.alert_by_id for alert_id in issue["alert_ids"]))

    def test_v151_combines_overdue_service_and_misfire_in_one_issue(self):
        matches = [issue for issue in self.report["issues"] if issue["vehicle_id"] == "V-151"]
        self.assertEqual(len(matches), 1)
        evidence = [self.alert_by_id[alert_id] for alert_id in matches[0]["alert_ids"]]
        self.assertTrue(any(row["alert_type"] == "maintenance_due" and float(row["value"]) > 0 for row in evidence))
        self.assertTrue(any(row["alert_type"] == "engine_fault" and row["dtc_code"] == "P0300" for row in evidence))

    def test_report_is_json_serializable(self):
        json.dumps(self.report, allow_nan=False)


if __name__ == "__main__":
    unittest.main()
