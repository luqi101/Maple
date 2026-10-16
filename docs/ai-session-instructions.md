# AI session hand-in

The repository includes [an actual visible-message extraction](ai-session.md): original user prompts and visible assistant responses mechanically copied from this conversation's verified local VS Code session log. Its header records source metadata, cutoff, exclusions, and labelled redactions. It is not a native UI export and omits tool/agent traces and internal material. No native UI export or share URL has been obtained. A native export, if available, can supplement this existing artifact.

1. Use the conversation application's original-session export or share feature if available. If using the **Codex CLI**, `/export session.md` is the documented CLI export command; do not assume that command is available in an editor extension or another interface. See the [official conversation export instructions](https://learn.chatgpt.com/docs/developer-commands?surface=ide#export-a-conversation-with-export).
2. Save the genuine export in the repository or place the actual accessible share link in the README's **AI use** section. Verify that a reviewer can open it.
3. If the interface has no export/share capability, copy the original visible conversation in order into `docs/ai-session.md`, retaining speaker roles and the actual text. Label it a **manual transcript**, identify any omitted or unavailable portions, and include visible delegated-agent material if available. Do not invent hidden reasoning, reconstruct messages from memory, or describe a partial copy as complete.
4. Redact credentials or private tokens if present and mark redactions explicitly. Keep task instructions, prompts, outputs, and corrections that explain the work.
5. Update the README with the real file/link and its provenance. An incomplete manual transcript should remain clearly disclosed as incomplete.

To refresh the supplied extraction, run `python3 scripts/export_session.py --source <exact-current-session-jsonl-path>` from the repository root. The script does not discover sessions; it validates that the selected source's workspace matches this repository. Review the output before publishing. Do not point it at another conversation.

This instructions file is not itself an AI session export or transcript.
