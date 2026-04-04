---
name: gog
description: Use when interacting with Google Workspace via the gog CLI—authenticate accounts, search/send Gmail, manage Calendar events, query Drive/Contacts, and edit Sheets/Docs directly from the terminal.
metadata:
  openclaw:
    emoji: "🎮"
    requires:
      bins: ["gogcli"]
    install:
      - id: brew
        kind: brew
        formula: steipete/tap/gogcli
        bins: ["gogcli"]
        label: Install gogcli (brew)
---

# gog — Google Workspace CLI playbook

## Quick start / setup
1. **Install CLI**: `brew install steipete/tap/gogcli` (binary `gogcli`; if PATH uses `gog`, adapt commands accordingly).
2. **Load OAuth client**: `gogcli auth credentials /path/to/client_secret.json` (desktop app credentials). Repeat with `--client work` for multiple projects.
3. **Add account**: `gogcli auth add you@gmail.com --services gmail,calendar,drive,contacts,docs,sheets` (use `--manual` or `--remote` when headless).
4. **Verify tokens**: `gogcli auth list --check`. Use `gogcli auth status` to confirm scopes.
5. **Default context**: export `GOG_ACCOUNT=you@gmail.com` (or use `gogcli auth alias set work work@company.com`).
6. Prefer `--json` for scripting, `--plain` for TSV, `--no-input` for CI, `--results-only` to drop envelopes.

## Gmail operations
### Search & inspection
- Thread search: `gogcli gmail search 'in:inbox newer_than:7d' --max 20 --json`.
- Message search (no threading): `gogcli gmail messages search "from:person@domain.com" --max 50 --json`.
- Fetch thread: `gogcli gmail thread get <threadId> --full --json` (add `--download --out-dir ./attachments`).

### Sending mail
- Plain text quick send: `gogcli gmail send --to a@b.com --subject "Hi" --body "Message"`.
- Multiline: `gogcli gmail send --to ... --subject ... --body-file ./body.txt` or `--body-file -` with heredoc.
- HTML: `--body-html '<p>Hi</p>'` (plain text fallback recommended).
- Reply: `gogcli gmail send --reply-to-message-id <msgId> --to ... --subject "Re: ..." --body ...`.
- Drafts: `gogcli gmail drafts create --to ... --subject ... --body-file ./draft.txt`; send via `gogcli gmail drafts send <draftId>`.

### Labels & settings
- List labels: `gogcli gmail labels list --json`.
- Inspect counts: `gogcli gmail labels get INBOX --json --results-only`.
- Apply labels to threads: `gogcli gmail labels modify <threadId> --add Label_1 --remove UNREAD`.

## Calendar operations
- List calendars: `gogcli calendar calendars --json`.
- List events: `gogcli calendar events primary --from 2026-04-01 --to 2026-04-05 --json` (or `--days 7`, `--today`).
- Create meeting: `gogcli calendar create primary --summary "Project Sync" --from 2026-04-01T09:00:00+07:00 --to 2026-04-01T10:00:00+07:00 --description "Agenda" --attendees a@b.com,c@d.com --with-meet`.
- Update: `gogcli calendar update primary <eventId> --summary "New title" --event-color 7`.
- Colors reference: `gogcli calendar colors` (IDs 1-11; e.g., 7=#46d6db, 10=#51b749).
- Deleting/rescheduling may require `--force` for non-interactive confirmation.

## Drive & Contacts
- Drive search: `gogcli drive search "name contains 'report'" --max 20 --json` (flags mirror Drive API search syntax).
- Download/export: `gogcli drive files export <fileId> --mime application/pdf`.
- Contacts: `gogcli contacts list --max 20 --json` or `gogcli contacts search "company:OpenAI"`.

## Sheets workflows
- Read values: `gogcli sheets get <sheetId> "Tab!A1:D20" --json`.
- Update range: `gogcli sheets update <sheetId> "Tab!A1:B2" --values-json '[["A","B"],["1","2"]]' --input USER_ENTERED`.
- Append rows: `gogcli sheets append <sheetId> "Tab!A:C" --values-json '[["x","y","z"]]' --insert INSERT_ROWS`.
- Clear: `gogcli sheets clear <sheetId> "Tab!A2:Z"`.
- Inspect metadata: `gogcli sheets metadata <sheetId> --json`.

## Docs usage
- Export to text: `gogcli docs export <docId> --format txt --out ./doc.txt`.
- Quick view: `gogcli docs cat <docId>`.
- Copy docs/slides: `gogcli docs copy <docId> --name "Copy"` / `gogcli slides copy ...`.

## Operational tips
- Use `--client NAME` for multiple OAuth buckets (stored as `credentials-NAME.json`).
- Keyring backend: `gogcli auth keyring file` + `GOG_KEYRING_PASSWORD` for headless; defaults to OS keychain.
- Service accounts/domain delegation: `gogcli auth service-account add ...` then inspect via `gogcli auth list`.
- For Windows automation, parse JSON via PowerShell `ConvertFrom-Json` or Python if `jq` absent.
- Capture event/message IDs from command output for later automations.

Use this skill whenever tasks require controlling Gmail/Calendar/Drive/Contacts/Sheets/Docs through gog instead of the Google web UI.
