#!/usr/bin/env python3
"""Extract visible messages from one explicitly supplied local session log.

This is deliberately not a complete log dump or a native UI export. It never
searches for sessions and never emits tools, internal instructions, or reasoning.
"""

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import re


VISIBLE_PHASES = {"commentary", "final", "final_answer"}
HIDDEN_PHASES = {"analysis", "summary", "reasoning"}
WRAPPERS = ("<environment_context>", "<external_codex_apps_open_page>")
CREDENTIAL_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{16,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{16,}\b"),
    re.compile(r"\bAKIA[A-Z0-9]{16}\b"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{12,}\b"),
)


def redact(text, workspace, home):
    """Return text with labelled path/obvious-secret redactions and counts."""
    counts = Counter()
    for original, marker in ((workspace, "[WORKSPACE]"), (home, "[HOME]")):
        if original and original != "/":
            counts["local paths"] += text.count(original)
            text = text.replace(original, marker)
    for pattern in CREDENTIAL_PATTERNS:
        text, count = pattern.subn("[REDACTED CREDENTIAL]", text)
        counts["obvious credentials"] += count
    replacements = (
        (r"(?i)(Authorization\s*:\s*Bearer\s+)[A-Za-z0-9._~+/=-]+", r"\1[REDACTED CREDENTIAL]"),
        (r"(?i)(https?://)[^\s/@]+:[^\s/@]+@", r"\1[REDACTED URL CREDENTIAL]@"),
        (r"(?i)([?&](?:api[_-]?key|token|secret|password)=)[^\s&#]+", r"\1[REDACTED CREDENTIAL]"),
        (r"(?im)(\b(?:api[_-]?key|access[_-]?token|refresh[_-]?token|password|client[_-]?secret)\b\s*[:=]\s*)[\"']?[^\s\"']+", r"\1[REDACTED CREDENTIAL]"),
    )
    for pattern, replacement in replacements:
        text, count = re.subn(pattern, replacement, text)
        counts["obvious credentials"] += count
    return text, counts


def visible_message(record):
    """Allow only original user messages and explicitly visible assistant text."""
    if record.get("type") != "response_item":
        return None
    payload = record.get("payload", {})
    if payload.get("type") != "message":
        return None
    role = payload.get("role")
    if role not in {"user", "assistant"}:
        return None
    if role == "assistant":
        labels = {payload.get("phase"), payload.get("channel")}
        if labels & HIDDEN_PHASES or not labels & VISIBLE_PHASES:
            return None
    parts = [
        item["text"]
        for item in payload.get("content", [])
        if isinstance(item, dict)
        and item.get("type") in {"input_text", "output_text", "text"}
        and isinstance(item.get("text"), str)
    ]
    if not parts:
        return None
    text = "\n".join(parts)
    if role == "user" and text.lstrip().startswith(WRAPPERS):
        return None
    return role, text, payload.get("phase") or payload.get("channel")


def extract(source, output):
    # Read one file explicitly selected by the caller. No directory scanning.
    lines = source.read_text(encoding="utf-8").splitlines()
    records = []
    skipped_partial = 0
    for index, line in enumerate(lines):
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            if index != len(lines) - 1:
                raise ValueError("Source has a malformed non-final record") from None
            skipped_partial += 1
    metadata = next(
        (r.get("payload", {}) for r in records if r.get("type") == "session_meta"),
        None,
    )
    if not metadata:
        raise ValueError("Source has no session metadata; refusing unverified extraction")
    workspace = metadata.get("cwd", "")
    repository_root = Path(__file__).resolve().parents[1]
    if not workspace or Path(workspace).resolve() != repository_root:
        raise ValueError("Source workspace does not match this repository")
    originator = metadata.get("originator", "unknown")
    counts = Counter()
    redactions = Counter()
    messages = []
    for record in records:
        selected = visible_message(record)
        if selected is None:
            continue
        role, text, phase = selected
        safe, changes = redact(text, workspace, str(Path.home()))
        redactions.update(changes)
        counts[role] += 1
        label = role.capitalize()
        if role == "assistant":
            label += " (" + phase + ")"
        messages.append((label, record.get("timestamp", "timestamp unavailable"), safe))
    generated = datetime.now(timezone.utc).isoformat()
    cutoff = next((r.get("timestamp") for r in reversed(records) if r.get("timestamp")), "unknown")
    header = [
        "# AI session: original visible-message extraction",
        "",
        "This artifact mechanically extracts original visible conversation messages from the current local Codex session log. It is **not a native UI export**, a retrospective summary, or a complete tool trace.",
        "",
        "- Source: local Codex JSONL session log; originator **" + str(originator) + "** (VS Code).",
        "- Source file: `" + source.name + "`.",
        "- Session ID: `" + str(metadata.get("id", "unknown")) + "`.",
        "- Original log start: " + str(metadata.get("timestamp", "unknown")) + ".",
        "- Extraction generated at: " + generated + ".",
        "- Source record cutoff: " + str(cutoff) + ". Messages after this cutoff are not included.",
        "- Included role counts: " + str(counts["user"]) + " user; " + str(counts["assistant"]) + " assistant.",
        "- Included only `response_item` messages: actual user prompts, and assistant text explicitly marked commentary/final/final_answer by phase or channel, in source order.",
        "- Excluded: system/developer instructions, reasoning/analysis/summary, unspecified assistant phases, tool calls/results, event-message duplicates, peer-agent messages, encrypted content, non-text attachments, and environment/open-page wrapper messages.",
        "- Redactions: local workspace/home paths use `[WORKSPACE]` / `[HOME]` (" + str(redactions["local paths"]) + " replacements); obvious credentials use labelled redactions (" + str(redactions["obvious credentials"]) + " replacements). Original wording is otherwise retained; text segments are separated by a newline.",
        "- Incompleteness: the active session may continue; this excludes tool/agent traces and does not claim to contain hidden or unavailable material.",
        "- Incomplete final source records skipped: " + str(skipped_partial) + ".",
        "",
    ]
    body = "\n".join(header)
    for index, (label, timestamp, text) in enumerate(messages, 1):
        body += "\n## " + str(index) + ". " + label + " — " + timestamp + "\n\n" + text + "\n"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(body, encoding="utf-8")
    return counts, redactions


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="Exact current-session JSONL file; no discovery occurs")
    parser.add_argument("--output", type=Path, default=Path("docs/ai-session.md"))
    args = parser.parse_args()
    try:
        counts, redactions = extract(args.source, args.output)
    except (OSError, ValueError) as error:
        # Exception paths can contain local paths; disclose only the error class.
        parser.exit(1, "Export failed (" + type(error).__name__ + "). Verify the explicitly supplied current-session source and workspace.\n")
    print("Visible-message extraction written: " + str(counts["user"]) + " user, " + str(counts["assistant"]) + " assistant messages; " + str(sum(redactions.values())) + " labelled redactions. Tools and internal material excluded.")


if __name__ == "__main__":
    main()
