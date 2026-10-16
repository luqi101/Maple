"""Check the handover preserves evidence and works outside the default output directory."""

from copy import deepcopy
from html.parser import HTMLParser
import unittest

from maple.core import build_report
from maple.render import render_html, render_text


class ReportMarkup(HTMLParser):
    def __init__(self):
        super().__init__()
        self.issue_count = 0
        self.links = []
        self.record_details = 0
        self.open_details = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "article" and attrs.get("class") == "issue":
            self.issue_count += 1
        if tag == "a":
            self.links.append(attrs.get("href"))
        if tag == "details":
            self.record_details += 1
            self.open_details += "open" in attrs


class RenderingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_untrusted_strings_are_text_and_cannot_add_markup(self):
        report = deepcopy(self.report)
        payload = '<script>alert("fixture")</script>'
        report["issues"][0]["title"] = payload
        report["issues"][0]["work_orders"][0]["technician_note"] = payload
        report["audit"]["notes"].append(payload)
        html = render_html(report)
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;alert(&quot;fixture&quot;)&lt;/script&gt;", html)

    def test_source_links_follow_output_relative_mapping_and_quote_paths(self):
        report = deepcopy(self.report)
        report["source_links"] = {"alerts.csv": "../../supplied data/alerts.csv", "vendor_notes.md": "../input/vendor notes.md"}
        markup = ReportMarkup()
        markup.feed(render_html(report))
        self.assertIn("../../supplied%20data/alerts.csv", markup.links)
        self.assertIn("../input/vendor%20notes.md", markup.links)
        self.assertIn("report.json", markup.links)

    def test_work_order_closure_and_booking_context_are_readable(self):
        html = render_html(self.report)
        text = render_text(self.report)
        for output in (html, text):
            self.assertIn("Sep 21, 2026 · 7:40 a.m. EDT", output)
            self.assertIn("Booked for 2026-10-05", output)
            self.assertIn("Booked first thing 2026-09-22", output)
            self.assertIn("Not closed in supplied record", output)

    def test_collapsed_evidence_preserves_every_referenced_alert_id(self):
        html = render_html(self.report)
        markup = ReportMarkup()
        markup.feed(html)
        self.assertIn("<details><summary>Source records", html)
        self.assertEqual(markup.open_details, 0)
        for item in self.report["issues"] + self.report["appendix"]:
            for alert_id in item.get("alert_ids", []):
                self.assertIn(alert_id, html)

    def test_action_count_policy_and_critical_caveats_are_visible(self):
        html = render_html(self.report)
        markup = ReportMarkup()
        markup.feed(html)
        self.assertEqual(markup.issue_count, 8)
        self.assertEqual(markup.issue_count, len(self.report["issues"]))
        self.assertIn(self.report["policy"], html)
        self.assertIn("Fixed snapshot, not live.", html)
        self.assertIn("does not provide dispatch clearance", html)


if __name__ == "__main__":
    unittest.main()
