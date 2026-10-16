"""Synthetic safety checks; no real conversation logs or credentials are fixtures."""

import unittest

from scripts.export_session import redact, visible_message


def message(role="assistant", phase=None, channel=None, text="Synthetic visible text"):
    return {
        "type": "response_item",
        "payload": {
            "type": "message",
            "role": role,
            "phase": phase,
            "channel": channel,
            "content": [{"type": "output_text", "text": text}],
        },
    }


class VisibleMessageTests(unittest.TestCase):
    def test_explicit_visible_phases_preserve_original_text(self):
        for phase in ("commentary", "final", "final_answer"):
            with self.subTest(phase=phase):
                self.assertEqual(
                    visible_message(message(phase=phase)),
                    ("assistant", "Synthetic visible text", phase),
                )

    def test_explicit_visible_channel_is_supported(self):
        self.assertEqual(visible_message(message(channel="final"))[1], "Synthetic visible text")

    def test_system_and_developer_roles_are_never_exported(self):
        for role in ("system", "developer"):
            with self.subTest(role=role):
                self.assertIsNone(visible_message(message(role=role, phase="commentary")))

    def test_hidden_unknown_and_unspecified_assistant_phases_are_excluded(self):
        for phase in ("analysis", "summary", "reasoning", "future_phase", None):
            with self.subTest(phase=phase):
                self.assertIsNone(visible_message(message(phase=phase)))

    def test_hidden_channel_overrides_visible_phase(self):
        for channel in ("analysis", "summary", "reasoning"):
            with self.subTest(channel=channel):
                self.assertIsNone(visible_message(message(phase="commentary", channel=channel)))

    def test_duplicate_events_and_tool_records_are_excluded(self):
        duplicate = message(phase="commentary")
        duplicate["type"] = "event_msg"
        self.assertIsNone(visible_message(duplicate))
        for item_type in ("function_call", "function_call_output", "custom_tool_call", "custom_tool_call_output", "reasoning", "agent_message"):
            with self.subTest(item_type=item_type):
                item = message(phase="commentary")
                item["payload"]["type"] = item_type
                self.assertIsNone(visible_message(item))

    def test_environment_and_open_page_wrappers_are_excluded(self):
        for text in ("\n<environment_context>synthetic</environment_context>", "<external_codex_apps_open_page>{}</external_codex_apps_open_page>"):
            with self.subTest(wrapper=text.split(">")[0]):
                self.assertIsNone(visible_message(message(role="user", text=text)))
        self.assertEqual(visible_message(message(role="user", text="Actual synthetic task"))[1], "Actual synthetic task")

    def test_encrypted_and_other_non_text_content_is_never_copied(self):
        item = message(phase="commentary")
        item["payload"]["content"].append({"type": "encrypted_content", "encrypted_content": "Synthetic excluded payload"})
        self.assertEqual(visible_message(item)[1], "Synthetic visible text")
        item["payload"]["content"] = item["payload"]["content"][1:]
        self.assertIsNone(visible_message(item))


class RedactionTests(unittest.TestCase):
    def test_synthetic_credential_patterns_receive_labelled_redactions(self):
        # Construct fake values from pieces so this test contains no token literal.
        fake_suffix = "synthetic" * 4
        samples = (
            "s" + "k" + "-" + fake_suffix,
            "gh" + "p" + "_" + fake_suffix,
            "Authorization: " + "Bearer " + fake_suffix,
            "https://" + "fakeuser:" + fake_suffix + "@example.invalid",
            "api_key=" + fake_suffix,
            "https://example.invalid?token=" + fake_suffix,
        )
        for text in samples:
            with self.subTest(pattern=text.split(fake_suffix)[0]):
                safe, counts = redact(text, "/synthetic/workspace", "/synthetic/home")
                self.assertNotIn(fake_suffix, safe)
                self.assertIn("[REDACTED", safe)
                self.assertGreater(counts["obvious credentials"], 0)

    def test_home_and_workspace_replacements_are_labelled(self):
        safe, counts = redact(
            "/synthetic/home/Maple/data/alerts.csv and /synthetic/home/notes.txt",
            "/synthetic/home/Maple",
            "/synthetic/home",
        )
        self.assertEqual(safe, "[WORKSPACE]/data/alerts.csv and [HOME]/notes.txt")
        self.assertEqual(counts["local paths"], 2)
        self.assertEqual(counts["obvious credentials"], 0)


if __name__ == "__main__":
    unittest.main()
