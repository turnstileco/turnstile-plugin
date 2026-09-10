#!/usr/bin/env python3
"""Deterministic pre-flight scanner for a Turnstile skill. Informs; never decides.

Usage:
    python3 scripts/scan_skill.py plugins/*/skills/*/
    python3 scripts/scan_skill.py --root pr-content            # scan every skill under a tree
    python3 scripts/scan_skill.py --root pr-content --format json --exit-zero

This is the mechanical half of SPEC.md's security table (TS-SEC-01…16). It greps a
skill's bundled files for secrets, hardcoded environment, remote dependencies,
DOM-injection sinks, network egress and injection-shaped prose; it enumerates the
MCP tools the skill actually names and diffs the scopes those tools require
against the scopes the frontmatter declares.

**It does not pass or fail a skill.** A finding is evidence for a human, keyed to
a `TS-SEC-NN` criterion. Its findings are non-negotiable regardless of what any
model later concludes; a clean scan is not a pass.

TRUST MODEL — read this before changing anything here.

  This script is Tier 0 repo tooling. At review time it is run from a *trusted*
  checkout (`origin/main`), never from the pull request under review, because a
  PR can edit the very scanner meant to check it. `scripts/review_pr_security.py`
  is the wrapper that makes that the default path.

  The skill being scanned is UNTRUSTED DATA. This script therefore:
    - never imports, executes, or evals anything it reads,
    - never follows a symlink (a PR could point one at ~/.ssh/id_rsa and have
      the contents echoed into a public CI log),
    - never prints a matched secret verbatim — excerpts are masked,
    - caps how much of any one file it will read,
    - reads its waiver registry from THIS checkout, never from --root. The
      registry (`standards/scan-waivers.json`) arrives with the trusted tooling.
      An in-PR waiver would undo the whole `pull_request_target` design: a PR
      could annotate its own High finding down to Medium and turn the required
      `scan` check green. Granting a waiver is a maintainer act on `main`; a
      skill's own PR cannot grant one. If you ever make this read a waiver out
      of the tree being scanned, you have deleted the gate. Don't.

Reuses `validate_skill.parse_frontmatter` / `strip_frontmatter` so the scanner and
the gate can never disagree about what a skill declares. Dependency-free: stdlib.

Exit: 0 = nothing at or above the severity threshold, 1 = something is, 2 = usage
error (which includes a malformed or illegal waiver registry — a gate that cannot
read its own configuration must not report a pass). The threshold defaults to
`high`, because SPEC.md says a High finding blocks a release while a Medium is
recorded for a human to rule on. `--fail-on` moves it; `--exit-zero` disables it.
"""

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_skill import parse_frontmatter, strip_frontmatter  # noqa: E402

# --------------------------------------------------------------- constants
# Repo-specific doc references live HERE, at the top. Keep divergences
# confined to this block: everything below it is meant to stay portable, so a
# fix here is a mechanical port anywhere else this scanner runs. In this repo
# all three references point at "SPEC.md".
CRITERIA_REF = "SPEC.md"
SCOPES_REF = "SPEC.md"
GATE_REF = "SPEC.md"
WAIVERS_REF = "standards/scan-waivers.json"
# ------------------------------------------------------------ end constants

MAX_FILE_BYTES = 2 * 1024 * 1024  # a reference file is prose, not a disk image
EXCERPT_CHARS = 100

BINARY_SUFFIXES = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".pdf", ".zip", ".skill",
    ".pptx", ".docx", ".xlsx", ".woff", ".woff2", ".ttf", ".otf", ".mp4", ".mov",
}

# Files that *execute*. A DOM sink or a network call here is a live behavior of
# whatever the skill emits.
CODE_SUFFIXES = {
    ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".html", ".htm", ".css",
    ".py", ".sh", ".bash",
}

# Checks whose meaning depends on whether the file executes. `.innerHTML =` in a
# markdown file is documentation — very possibly documentation of this exact rule
# — while in a .js file it is CWE-79. Prose still raises the finding, because a
# SKILL.md can *instruct* Claude to emit an exfiltration call, but at a severity
# that asks a human to look rather than blocking a merge. A security document
# has to be able to name the sinks it hunts for without failing its own scan.
CONTEXT_SENSITIVE_CHECKS = {"TS-SEC-09", "TS-SEC-10", "TS-SEC-11"}

# Checks whose meaning depends on whether Claude *loads the file as instructions*.
# TS-SEC-12 hunts instruction-shaped text. Its attack surface is exactly the two
# places Claude reads as instructions: the `SKILL.md` body, and `references/**`,
# which SKILL.md points at. Everywhere else in a skill folder — `CHANGELOG.md`,
# `assets/`, `scripts/` — the same words are being *described*, not asserted, and
# fire at Medium for a human to rule on. The rationale is the same one behind the
# context-sensitive checks above: a control that fires on the document describing
# it is a control people learn to ignore — a changelog that honestly documents a
# prompt-injection defense must not be unmergeable for saying so.
#
# The scoping is deliberately by *surface*, not by file type. Dropping all markdown
# to Medium would gut the check: `references/**` is markdown, and markdown is where
# the payload goes — it is exactly what Claude loads.
SURFACE_SENSITIVE_CHECKS = {"TS-SEC-12"}


def loads_as_instructions(rel: str) -> bool:
    """True for the paths Claude reads as instructions: SKILL.md and references/**.

    Everything else in a skill folder is data or history. A `CHANGELOG.md` entry
    describing an attack is documentation; the same string under `references/` is
    a payload, because SKILL.md tells Claude to read it.
    """
    return rel == "SKILL.md" or rel.startswith("references/")

# ---------------------------------------------------------------- patterns

# (check_id, severity, label, regex)
SECRET_PATTERNS = [
    ("TS-SEC-01", "high", "private key block",
     r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY-----"),
    ("TS-SEC-01", "high", "Anthropic API key", r"sk-ant-[A-Za-z0-9_\-]{20,}"),
    ("TS-SEC-01", "high", "OpenAI-style API key", r"\bsk-[A-Za-z0-9]{32,}\b"),
    ("TS-SEC-01", "high", "GitHub token", r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
    ("TS-SEC-01", "high", "AWS access key id", r"\bAKIA[0-9A-Z]{16}\b"),
    ("TS-SEC-01", "high", "Slack token", r"\bxox[abposr]-[A-Za-z0-9-]{10,}"),
    ("TS-SEC-01", "high", "Google API key", r"\bAIza[0-9A-Za-z_\-]{35}\b"),
    ("TS-SEC-01", "high", "literal bearer token",
     r"(?i)\bauthorization\s*[:=]\s*[\"']?bearer\s+[A-Za-z0-9._\-]{16,}"),
    # A quoted literal assigned to a secret-shaped name. `${VAR}` and `$(...)`
    # interpolations and obvious placeholders are the documented way to do this,
    # so they must not fire.
    ("TS-SEC-01", "high", "secret assigned a literal value",
     r"(?i)\b(?:api[_-]?key|secret|token|password|passwd|credential)s?\b\s*[:=]\s*"
     r"[\"'](?!\$\{|\$\(|<|YOUR_|xxx|\.\.\.)[^\"'\s]{16,}[\"']"),
]

ENV_PATTERNS = [
    ("TS-SEC-02", "high", "hardcoded UUID (server, connector, or account id)",
     r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-8][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}\b"),
]

INTERNAL_ID_PATTERNS = [
    ("TS-SEC-03", "high", "Google Drive/Docs URL with an embedded file id",
     r"https?://(?:docs|drive|sheets)\.google\.com/[^\s\"'<>)]*/d/[A-Za-z0-9_\-]{20,}"),
    # The classic Drive file-id shape: leading '1', 32-43 more id chars. Guarded
    # against base64 payloads, where that shape occurs by chance — an inlined
    # data: URI is a 3 KB haystack of it.
    ("TS-SEC-03", "medium", "bare string shaped like a Google Drive file id",
     r"\b1[A-Za-z0-9_\-]{32,43}\b"),
    # Backticks required: ids are conventionally written in backticks, and
    # without them `doc comment` and friends match.
    ("TS-SEC-03", "medium", "Coda doc id", r"(?i)\bdoc\s+`[A-Za-z0-9_]{8,12}`"),
]

# A line matching a check's guard is not scanned for that check.
GUARDS = {
    "bare string shaped like a Google Drive file id": re.compile(r"base64,|data:[a-z]+/"),
}

# Checks whose match is itself the sensitive value. Everything else prints the
# line as written: redacting `https://fonts.googleapis.com` helps nobody and
# makes the finding unreadable.
#
# TS-SEC-02 belongs here even though a UUID is an identifier rather than a
# credential. It is, by this scanner's own framing, an internal server /
# connector / account id — the same sensitivity class as the Drive and Coda ids
# in TS-SEC-03. Printing it verbatim would move it from the diff into a CI log.
MASKED_CHECKS = {"TS-SEC-01", "TS-SEC-02", "TS-SEC-03"}

HTML_PATTERNS = [
    ("TS-SEC-08", "medium", "remote <script src>",
     r"<script[^>]+src\s*=\s*[\"']https?://"),
    ("TS-SEC-08", "medium", "remote stylesheet",
     r"<link[^>]+href\s*=\s*[\"']https?://"),
    ("TS-SEC-08", "medium", "remote @import", r"@import\s+url\(\s*[\"']?https?://"),
    ("TS-SEC-08", "medium", "remote <iframe src>",
     r"<iframe[^>]+src\s*=\s*[\"']https?://"),
]

DOM_SINK_PATTERNS = [
    ("TS-SEC-09", "high", "innerHTML assignment", r"\.innerHTML\s*="),
    ("TS-SEC-09", "high", "outerHTML assignment", r"\.outerHTML\s*="),
    ("TS-SEC-09", "high", "document.write", r"\bdocument\.write(?:ln)?\s*\("),
    ("TS-SEC-09", "high", "insertAdjacentHTML", r"\binsertAdjacentHTML\s*\("),
]

EGRESS_PATTERNS = [
    ("TS-SEC-10", "high", "fetch() call", r"(?<![\w.])fetch\s*\("),
    ("TS-SEC-10", "high", "XMLHttpRequest", r"\bXMLHttpRequest\b"),
    ("TS-SEC-10", "high", "navigator.sendBeacon", r"\bnavigator\.sendBeacon\s*\("),
    ("TS-SEC-10", "high", "WebSocket", r"\bnew\s+WebSocket\s*\("),
]

EVAL_PATTERNS = [
    ("TS-SEC-11", "medium", "eval()", r"(?<![\w.])eval\s*\("),
    ("TS-SEC-11", "medium", "new Function()", r"\bnew\s+Function\s*\("),
]

# Prompt injection aimed at whoever reviews or runs the skill (LLM01). Bundled
# references are read into context; text there is an instruction unless proven
# otherwise.
INJECTION_PATTERNS = [
    ("TS-SEC-12", "high", "instruction to ignore prior instructions",
     r"(?i)\b(?:ignore|disregard|forget)\b[^.\n]{0,40}\b(?:previous|prior|above|earlier|all)\b"
     r"[^.\n]{0,20}\binstructions?\b"),
    ("TS-SEC-12", "high", "instruction to report a verdict",
     r"(?i)\breport\s+(?:this\s+)?(?:as\s+)?(?:PASS|SAFE|APPROVED)\b"),
    ("TS-SEC-12", "high", "role reassignment", r"(?i)\byou\s+are\s+now\s+(?:a|an|the)\b"),
    ("TS-SEC-12", "medium", "system-prompt reference",
     r"(?i)\b(?:reveal|print|output|show)\b[^.\n]{0,30}\bsystem\s+prompt\b"),
    ("TS-SEC-12", "high", "security override",
     r"(?i)\b(?:override|bypass|skip)\b[^.\n]{0,30}\b(?:security|review|check|gate)\b"),
]

ALL_PATTERNS = (
    SECRET_PATTERNS + ENV_PATTERNS + INTERNAL_ID_PATTERNS + HTML_PATTERNS
    + DOM_SINK_PATTERNS + EGRESS_PATTERNS + EVAL_PATTERNS + INJECTION_PATTERNS
)
COMPILED = [(cid, sev, label, re.compile(rx)) for cid, sev, label, rx in ALL_PATTERNS]

# ---------------------------------------------------- Turnstile MCP knowledge
# Source: the live MCP's own tool descriptions (the live MCP is authoritative —
# SPEC.md's authority note). This block MIRRORS the canonical internal copy,
# where it is GENERATED from a dated tool snapshot (2026-08-17, 131 tools:
# 52 read, 79 write); mirror updates land as PRs like this one. Scope names
# follow each tool's own description; SCOPE_ALIASES carries the legacy names
# the descriptions still accept, and the declared-vs-observed diff normalizes
# both sides through it.

TOOL_SCOPES = {
    "add_turnstile_invoice_lines": "invoices:write",
    "add_turnstile_usage_event": "usage:write",
    "amend_turnstile_contract": "contract:write",
    "approve_turnstile_invoice": "invoices:write",
    "assign_turnstile_metric_tag": "metrics:write",
    "attach_turnstile_subscription": "invoices:write",
    "author_turnstile_contract_draft_commercial_terms": "contract:write",
    "author_turnstile_quote_commercial_terms": "quote:write",
    "cancel_turnstile_invoice": "invoices:write",
    "charge_turnstile_invoice": "invoices:write",
    "create_turnstile_contract": "contract:write",
    "create_turnstile_contract_draft_access_link": "contract:write",
    "create_turnstile_contract_draft_line_item": "contract:write",
    "create_turnstile_contract_draft_phase": "contract:write",
    "create_turnstile_customer": "customer:write",
    "create_turnstile_invoice": "invoices:write",
    "create_turnstile_metric": "metrics:write",
    "create_turnstile_metric_tag": "metrics:write",
    "create_turnstile_product": "product:write",
    "create_turnstile_quote": "quote:write",
    "create_turnstile_quote_access_link": "quote:write",
    "create_turnstile_quote_line_item": "quote:write",
    "create_turnstile_quote_phase": "quote:write",
    "create_turnstile_support_request": "entity:write",
    "create_turnstile_unit": "units:write",
    "delete_turnstile_contract_draft_line_item": "contract:write",
    "delete_turnstile_contract_draft_phase": "contract:write",
    "delete_turnstile_invoice": "invoices:write",
    "delete_turnstile_invoice_line": "invoices:write",
    "delete_turnstile_metric": "metrics:write",
    "delete_turnstile_quote": "quote:write",
    "delete_turnstile_quote_line_item": "quote:write",
    "delete_turnstile_quote_phase": "quote:write",
    "discard_turnstile_contract_draft": "contract:write",
    "duplicate_turnstile_quote": "quote:write",
    "edit_turnstile_invoice_line": "invoices:write",
    "evaluate_turnstile_invoice_readiness": "invoices:write",
    "finalize_turnstile_contract_draft": "contract:write",
    "get_turnstile_contract": "contract:read",
    "get_turnstile_contract_draft": "contract:read",
    "get_turnstile_contract_draft_commercial_terms": "contract:read",
    "get_turnstile_contract_draft_document": "contract:read",
    "get_turnstile_contract_draft_invoice_preview": "contract:read",
    "get_turnstile_contract_draft_phase": "contract:read",
    "get_turnstile_contract_draft_workflow_settings": "contract:read",
    "get_turnstile_contract_invoice_preview": "contract:read",
    "get_turnstile_contract_phase": "contract:read",
    "get_turnstile_contract_revision": "contract:read",
    "get_turnstile_customer": "customer:read",
    "get_turnstile_customer_name": "customer:read",
    "get_turnstile_invoice": "invoices:read",
    "get_turnstile_metric": "metrics:read",
    "get_turnstile_metric_breakdown": "metrics:read",
    "get_turnstile_metric_values": "metrics:read",
    "get_turnstile_product": "product:read",
    "get_turnstile_quote": "quote:read",
    "get_turnstile_quote_commercial_terms": "quote:read",
    "get_turnstile_quote_invoice_preview": "quote:read",
    "get_turnstile_quote_phase": "quote:read",
    "get_turnstile_quote_signatures": "quote:read",
    "get_turnstile_quote_workflow_settings": "quote:read",
    "get_turnstile_subscription": "subscription:read",
    "import_turnstile_invoice": "invoices:write",
    "issue_turnstile_invoice": "invoices:write",
    "list_turnstile_aggregated_usage": "usage:read",
    "list_turnstile_contract_documents": "contract:read",
    "list_turnstile_contract_draft_documents": "contract:read",
    "list_turnstile_contract_draft_phases": "contract:read",
    "list_turnstile_contract_drafts": "contract:read",
    "list_turnstile_contract_line_items": "contract:read",
    "list_turnstile_contract_phases": "contract:read",
    "list_turnstile_contract_revisions": "contract:read",
    "list_turnstile_contracts": "contract:read",
    "list_turnstile_customers": "customer:read",
    "list_turnstile_filterable_entities": "metrics:read",
    "list_turnstile_invoice_lines": "invoices:read",
    "list_turnstile_invoices": "invoices:read",
    "list_turnstile_metric_tags": "metrics:read",
    "list_turnstile_metrics": "metrics:read",
    "list_turnstile_products": "product:read",
    "list_turnstile_quote_documents": "quote:read",
    "list_turnstile_quote_events": "quote:read",
    "list_turnstile_quote_line_items": "quote:read",
    "list_turnstile_quote_order_flow_events": "quote:read",
    "list_turnstile_quote_participants": "quote:read",
    "list_turnstile_quote_phases": "quote:read",
    "list_turnstile_quotes": "quote:read",
    "list_turnstile_raw_usage": "usage:read",
    "list_turnstile_subscriptions": "subscription:read",
    "list_turnstile_units": "units:read",
    "mark_turnstile_invoice_as_paid": "invoices:write",
    "mark_turnstile_invoice_as_uncollectible": "invoices:write",
    "mark_turnstile_invoice_payment_failed": "invoices:write",
    "mark_turnstile_invoice_payment_pending": "invoices:write",
    "ping_turnstile_api": None,
    "publish_turnstile_contract_draft": "contract:write",
    "publish_turnstile_quote": "quote:write",
    "re_request_turnstile_invoice_review": "invoices:write",
    "recompute_turnstile_usage": "usage:write",
    "reissue_and_issue_turnstile_invoice": "invoices:write",
    "reissue_turnstile_invoice_as_draft": "invoices:write",
    "renew_turnstile_contract": "contract:write",
    "resend_turnstile_contract_draft": "contract:write",
    "resend_turnstile_invoice": "invoices:write",
    "resend_turnstile_quote_email": "quote:write",
    "retract_turnstile_contract_draft": "contract:write",
    "retract_turnstile_quote": "quote:write",
    "search_turnstile_crm_customers": "customer:read",
    "terminate_turnstile_contract": "contract:write",
    "uncancel_turnstile_invoice": "invoices:write",
    "update_turnstile_contract": "contract:write",
    "update_turnstile_contract_draft": "contract:write",
    "update_turnstile_contract_draft_line_item": "contract:write",
    "update_turnstile_contract_draft_phase": "contract:write",
    "update_turnstile_contract_draft_workflow_settings": "contract:write",
    "update_turnstile_customer": "customer:write",
    "update_turnstile_invoice": "invoices:write",
    "update_turnstile_metric": "metrics:write",
    "update_turnstile_product": "product:write",
    "update_turnstile_quote": "quote:write",
    "update_turnstile_quote_line_item": "quote:write",
    "update_turnstile_quote_phase": "quote:write",
    "update_turnstile_quote_workflow_settings": "quote:write",
    "upload_turnstile_contract_document": "contract:write",
    "upload_turnstile_contract_draft_document": "contract:write",
    "validate_turnstile_contract_draft": "contract:write",
    "validate_turnstile_invoice_import": "invoices:write",
    "validate_turnstile_quote": "quote:write",
    "void_and_reissue_turnstile_invoice": "invoices:write",
    "void_and_save_turnstile_invoice_as_draft": "invoices:write",
    "void_turnstile_invoice": "invoices:write",
}
# Legacy scope aliases, straight from the tool descriptions
# ("Requires the 'X' scope (or the legacy 'Y' scope)").
# The declared-vs-observed diff normalizes BOTH sides through this map.
SCOPE_ALIASES = {
    "entity:read": "customer:read",
    "entity:write": "customer:write",
}

WRITE_TOOLS = {t for t, s in TOOL_SCOPES.items() if s and s.endswith(":write")}

# Irreversible-or-outward tools: hand-curated, human judgment over each tool's
# own description — never verb-inference. Classes per SPEC.md's write-safety
# section: sends-to-customer, moves-money, terminal state change,
# writes-through-to-external-systems.
IRREVERSIBLE_TOOLS = {
    # sends-to-customer (cannot unsend)
    "issue_turnstile_invoice",            # "cannot be undone (the email will be delivered)"
    "reissue_and_issue_turnstile_invoice",  # issues + sends in one call
    "resend_turnstile_invoice",           # every call emails the customer, no dedup
    "publish_turnstile_quote",            # emails customer; starts e-sign/payment workflow
    "resend_turnstile_quote_email",       # outward email
    "publish_turnstile_contract_draft",   # starts the customer signature workflow
    "resend_turnstile_contract_draft",    # each call sends a fresh email
    # moves-money
    "charge_turnstile_invoice",           # retries the saved payment method
    # terminal state changes
    "mark_turnstile_invoice_as_paid",     # "terminal state change"; processor write
    "mark_turnstile_invoice_as_uncollectible",  # bad-debt write-off, terminal
    "void_turnstile_invoice",             # ISSUED -> VOID, terminal
    "void_and_reissue_turnstile_invoice",   # voids AND sends the reissue
    "void_and_save_turnstile_invoice_as_draft",  # the void half is terminal
    "terminate_turnstile_contract",       # no draft step; finalized immediately
    "finalize_turnstile_contract_draft",  # a finalized draft is a committed revision
    # writes through to external systems
    "update_turnstile_customer",          # payment-processor record also updated
}

# Waivers are illegal for the three checks the criteria table marks **Never N/A**.
# A secret, a hardcoded server id, and an injection string on an instruction surface
# get fixed, not reasoned about. Naming one of these in the registry is a
# configuration error, not a finding to downgrade — see load_waivers().
NEVER_WAIVABLE = {"TS-SEC-01", "TS-SEC-02", "TS-SEC-12"}

WAIVER_FIELDS = ("skill", "check", "file", "match", "reason", "granted", "granted-by")

# The registry ships with the trusted tooling, NOT with the tree under --root.
# See the TRUST MODEL note above before changing this line.
DEFAULT_WAIVERS = Path(__file__).resolve().parent.parent / "standards" / "scan-waivers.json"

# ---------------------------------------------------------------- machinery


def norm(s: str) -> str:
    """A source line reduced to its content: runs of whitespace collapsed, ends
    trimmed. Indentation and reflowing must not silently void a waiver; changing
    the code itself must."""
    return " ".join(s.split())


def load_waivers(path: Path) -> list:
    """The admin-granted waivers, from the trusted checkout.

    Every failure here exits 2. A gate that cannot read its own configuration has
    no business reporting a pass, and a typo'd `check` field silently honoring
    nothing would be the quietest possible way to lose this control.
    """
    if not path.is_file():
        return []  # no registry is a valid state: nothing has been waived
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        print(f"ERROR: cannot read waiver registry {path}: {e}", file=sys.stderr)
        sys.exit(2)

    entries = raw.get("waivers", [])
    if not isinstance(entries, list):
        print(f"ERROR: {path}: 'waivers' must be a list", file=sys.stderr)
        sys.exit(2)

    # Only the pattern-raised checks are waivable, and that falls out of the design
    # rather than being a rule: a waiver is keyed to a source line, and the checks
    # raised outside scan_text() (TS-SEC-04's scope diff, TS-SEC-14's symlink) have
    # no line to key on. A declared-vs-observed scope mismatch is a frontmatter fix.
    known = {c for c, _, _, _ in ALL_PATTERNS}
    for i, w in enumerate(entries):
        where = f"{path}: waivers[{i}]"
        if not isinstance(w, dict):
            print(f"ERROR: {where} is not an object", file=sys.stderr)
            sys.exit(2)
        missing = [f for f in WAIVER_FIELDS if not str(w.get(f, "")).strip()]
        if missing:
            print(f"ERROR: {where} is missing {', '.join(missing)}", file=sys.stderr)
            sys.exit(2)
        if w["check"] in NEVER_WAIVABLE:
            print(f"ERROR: {where} waives {w['check']}, which the criteria mark "
                  f"'Never N/A' ({CRITERIA_REF}). Fix the finding; do not waive it.",
                  file=sys.stderr)
            sys.exit(2)
        if w["check"] not in known:
            print(f"ERROR: {where} names {w['check']!r}, which no check in this "
                  "scanner raises — a waiver that matches nothing is a typo, not a "
                  "grant", file=sys.stderr)
            sys.exit(2)
        w["_norm"] = norm(w["match"])
        w["_used"] = False
    return entries


def finding(check, severity, path, line, message, excerpt="", waived=False):
    return {
        "check": check,
        "severity": severity,
        "path": path,
        "line": line,
        "message": message,
        "excerpt": excerpt,
        # True only when a maintainer-granted registry entry downgraded this from
        # High. The finding is still here and still reported — `waived` is not
        # `absent`.
        "waived": waived,
    }


def excerpt_for(check: str, line: str, rx: re.Pattern) -> str:
    """One line of evidence, with the matched value redacted when it *is* the
    sensitive thing.

    Findings land in CI logs and PR comments. A scanner that prints the secret it
    found has moved that secret somewhere more public than where it started.

    Redacts *every* match on the line, not just the first. `A=sk-ant-… B=sk-ant-…`
    is one line with two keys, and `re.search` only ever sees the first of them.
    """
    if check in MASKED_CHECKS:
        line = rx.sub("***REDACTED***", line)
    line = line.strip()
    if len(line) > EXCERPT_CHARS:
        line = line[:EXCERPT_CHARS] + "…"
    return line


def readable_files(skill_dir: Path):
    """Every regular file under the skill, never following a symlink out.

    Yields `(path, text, has_nul)`. `text is None` marks a symlink — reported,
    never read. `has_nul` marks a NUL byte in a file whose suffix is not in
    `BINARY_SUFFIXES`, i.e. a file that claims to be text and is not.

    [Fixed 2026-07-16] This function used to `continue` on `b"\\x00" in data[:4096]`
    — "binary by sniff" — which skipped the file **in silence**: no finding, no
    note, nothing in the count. That was a one-byte bypass of every check this
    scanner has. A fixture whose `assets/x.html` began `<script>\\x00` and then
    carried an unescaped `innerHTML`, a `fetch()` to an attacker host, and a
    literal `sk-ant-` key scanned **0 findings, exit 0** — green, past `scan`, a
    required status check. `TS-SEC-01` is marked never-N/A and was defeated by a
    byte.

    Two rules now, and the split is the point:

    - **Known-binary suffix** (`BINARY_SUFFIXES`) → skipped, as always. A `.png`
      is not evidence and never was.
    - **Anything else with a NUL** → decoded anyway (`errors="replace"` handles
      it; NUL is valid UTF-8) *and* flagged. Nothing gets to be unreadable and
      unmentioned at the same time. If a file is legitimately binary, its suffix
      belongs in `BINARY_SUFFIXES` — an explicit, reviewable edit on `main`,
      not a property a skill can assert about itself by embedding a byte.
    """
    root = skill_dir.resolve()
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            yield path, None, False  # reported, never read
            continue
        if not path.is_file():
            continue
        if path.suffix.lower() in BINARY_SUFFIXES:
            continue
        try:
            if path.stat().st_size > MAX_FILE_BYTES:
                continue
            data = path.read_bytes()
        except OSError:
            continue
        # Whole file, not just the first 4KB: the old window missed a NUL at byte
        # 29290 in a 60KB artifact, which is exactly where a real one turned up.
        yield path, data.decode("utf-8", errors="replace"), b"\x00" in data


def waiver_for(waivers: list, check: str, rel: str, line: str):
    """The admin-granted waiver covering this exact sink, or None.

    Keyed on check + file + the normalized line, never the line number: code moves,
    and a waiver that broke every time something shifted a row would be re-granted
    reflexively, which is how a control becomes a rubber stamp. Change the line's
    text, though, and the waiver stops matching — an edited sink has not been
    reviewed in its new form.
    """
    n = norm(line)
    for w in waivers:
        if w["check"] == check and w["file"] == rel and w["_norm"] == n:
            w["_used"] = True
            return w
    return None


def scan_text(rel: str, text: str, findings: list, is_code: bool = True,
              waivers: list = ()) -> None:
    for i, line in enumerate(text.splitlines(), 1):
        if len(line) > 4000:
            line = line[:4000]  # a minified bundle should not stall the regexes
        for check, sev, label, rx in COMPILED:
            guard = GUARDS.get(label)
            if guard and guard.search(line):
                continue
            if not rx.search(line):
                continue
            message = label
            if not is_code and check in CONTEXT_SENSITIVE_CHECKS:
                sev = "medium" if sev == "high" else sev
                message = f"{label} — in prose, not code; documentation or an instruction. A human rules"
            elif check in SURFACE_SENSITIVE_CHECKS and not loads_as_instructions(rel):
                sev = "medium" if sev == "high" else sev
                message = (
                    f"{label} — not on a surface Claude loads as instructions "
                    "(SKILL.md, references/**); described, not asserted. A human rules"
                )
            # Applied last, and only ever downgrades High → Medium. The finding is
            # still reported, still counted, still on the reviewer's screen — it
            # just stops holding the merge button. Same shape as the context rules
            # above; the difference is that a human on `main` granted it.
            w = waiver_for(waivers, check, rel, line)
            waived = bool(w) and sev == "high"
            if waived:
                sev = "medium"
                message = (f"{message} — waived on main by {w['granted-by']} "
                           f"({w['granted']}): {w['reason']}")
            findings.append(
                finding(check, sev, rel, i, message,
                        excerpt_for(check, line, rx), waived=waived)
            )


def scan_declarations(skill_dir: Path, corpus: str, findings: list) -> None:
    """Diff what the frontmatter declares against what the code actually names."""
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        return
    fields, errors = parse_frontmatter(skill_md.read_text(encoding="utf-8"))
    if not fields:
        return
    meta = fields.get("metadata")
    if not isinstance(meta, dict):
        return  # a tooling skill; nothing to diff

    rel = "SKILL.md"
    declared = {
        s.strip() for s in str(meta.get("scopes", "")).split(",") if s.strip()
    }
    if declared == {"none"}:
        declared = set()

    # Both sides of the diff are normalized through SCOPE_ALIASES (the legacy
    # names the tool descriptions themselves still accept, e.g. entity:write
    # for customer:write) so a skill declaring either form matches.
    declared = {SCOPE_ALIASES.get(s, s) for s in declared}

    observed = {t for t in TOOL_SCOPES if re.search(rf"\b{re.escape(t)}\b", corpus)}
    required = {
        SCOPE_ALIASES.get(TOOL_SCOPES[t], TOOL_SCOPES[t])
        for t in observed if TOOL_SCOPES[t]
    }

    for scope in sorted(required - declared):
        tools = sorted(
            t for t in observed
            if TOOL_SCOPES[t] and SCOPE_ALIASES.get(TOOL_SCOPES[t], TOOL_SCOPES[t]) == scope
        )
        findings.append(finding(
            "TS-SEC-04", "high", rel, 0,
            f"scope {scope!r} is required by {', '.join(tools)} but is not declared "
            "in metadata.scopes",
        ))
    for scope in sorted(declared - required):
        findings.append(finding(
            "TS-SEC-04", "medium", rel, 0,
            f"scope {scope!r} is declared but no named tool requires it — "
            f"least privilege ({SCOPES_REF})",
        ))

    writes = observed & WRITE_TOOLS
    access = str(meta.get("access", "")).strip()
    if writes and access == "read-only":
        findings.append(finding(
            "TS-SEC-04", "high", rel, 0,
            f"declares access: read-only but names write tools: {', '.join(sorted(writes))}",
        ))

    if writes and "eligibleActions" not in corpus:
        findings.append(finding(
            "TS-SEC-06", "high", rel, 0,
            f"names write tools ({', '.join(sorted(writes))}) but never mentions "
            "eligibleActions — the action gate. Triage from the list (expand: "
            "eligibleActions, 25 per page), act from a fresh get_turnstile_invoice "
            "for the one invoice immediately before the write (SPEC.md, Write "
            "safety; probed 2026-09-09). This check is an advisory token heuristic: it greps "
            "for the word, and cannot verify the skill actually reads the gate "
            "fresh per invoice, honors `allowed`, and surfaces `blockingReasons` — "
            f"that is a named human-review item ({GATE_REF})",
        ))

    irreversible = observed & IRREVERSIBLE_TOOLS
    supervision = str(meta.get("supervision", "")).strip()
    if irreversible and supervision != "asks-before-each-action":
        findings.append(finding(
            "TS-SEC-07", "high", rel, 0,
            f"names irreversible tools ({', '.join(sorted(irreversible))}) with "
            f"supervision: {supervision or '<unset>'}. An action that cannot be "
            "undone asks before each action",
        ))

    risk = str(meta.get("risk", "")).strip()
    if irreversible and risk == "low":
        findings.append(finding(
            "TS-SEC-07", "high", rel, 0,
            "declares risk: low while naming an irreversible write tool",
        ))


def scan_skill(skill_dir: Path, waivers: list = ()) -> list:
    findings, chunks = [], []
    root = skill_dir.resolve()
    # A waiver names the skill it was granted for. One skill's ruling never leaks
    # into another's, however identical the offending line looks.
    mine = [w for w in waivers if w["skill"] == skill_dir.name]
    for path, text, has_nul in readable_files(skill_dir):
        rel = path.relative_to(root).as_posix()
        if text is None:
            findings.append(finding(
                "TS-SEC-14", "high", rel, 0,
                "symlink in a skill bundle — not followed, not packaged, and a "
                "way to make a reader open a file outside the skill",
            ))
            continue
        if has_nul:
            findings.append(finding(
                "TS-SEC-14", "high", rel, 0,
                "NUL byte in a file whose suffix says text — binary content in a "
                "reviewable file. It makes grep-based tools report nothing on this "
                "file, and until 2026-07-16 it made this scanner skip it silently. "
                "The file IS scanned below regardless; this is the byte itself "
                "being reported. Remove it, or if the file is genuinely binary, "
                "add its suffix to BINARY_SUFFIXES on main",
            ))
        scan_text(rel, text, findings, is_code=path.suffix.lower() in CODE_SUFFIXES,
                  waivers=mine)
        chunks.append(text)
    scan_declarations(skill_dir, "\n".join(chunks), findings)
    order = {"high": 0, "medium": 1, "low": 2}
    findings.sort(key=lambda f: (order.get(f["severity"], 9), f["check"], f["path"], f["line"]))
    return findings


def discover(root: Path):
    seen = []
    for pattern in ("plugins/*/skills/*/SKILL.md", ".claude/skills/*/SKILL.md"):
        seen += [p.parent for p in sorted(root.glob(pattern))]
    return seen


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("skills", nargs="*", type=Path, help="skill directories")
    ap.add_argument("--root", type=Path, help="scan every skill under this tree")
    ap.add_argument("--format", choices=("text", "json"), default="text")
    ap.add_argument("--fail-on", choices=("high", "medium", "low", "never"),
                    default="high",
                    help="minimum severity that exits non-zero (default: high). "
                         "The criteria say a High finding blocks an L2 release; "
                         "a Medium is recorded for a human to rule on.")
    ap.add_argument("--exit-zero", action="store_true",
                    help="report findings but always exit 0 — the same as "
                         "--fail-on never (record, don't block)")
    ap.add_argument("--waivers", type=Path, default=DEFAULT_WAIVERS,
                    help=f"maintainer-granted waiver registry (default: {WAIVERS_REF} "
                         "beside this script). Read from THIS checkout, never from "
                         "--root: a PR must not be able to waive its own findings.")
    args = ap.parse_args()
    threshold = "never" if args.exit_zero else args.fail_on
    waivers = load_waivers(args.waivers)

    targets = list(args.skills)
    if args.root:
        # A zero-skill tree under --root is a successful no-op, not a usage
        # error: the caller asked "scan whatever skills are here" and the
        # honest answer for an empty tree is a clean pass. (Until 2026-07-13
        # this exited 2, which made the scan workflow red on any repo that
        # had not yet grown its first skill.) Passing an explicit skill dir
        # that does not exist is still an error, below.
        found = discover(args.root.resolve())
        if not args.skills and not found:
            print(f"no skills under {args.root}; nothing to scan — "
                  "a zero-skill tree is a clean pass")
            sys.exit(0)
        targets += found
    if not targets:
        print("ERROR: nothing to scan (pass skill dirs or --root)", file=sys.stderr)
        sys.exit(2)

    report, total, waived = [], 0, 0
    counts = {"high": 0, "medium": 0, "low": 0}
    for skill_dir in targets:
        if not (skill_dir / "SKILL.md").is_file():
            print(f"skip: {skill_dir} (no SKILL.md)", file=sys.stderr)
            continue
        findings = scan_skill(skill_dir, waivers)
        total += len(findings)
        for f in findings:
            counts[f["severity"]] = counts.get(f["severity"], 0) + 1
            waived += 1 if f["waived"] else 0
        report.append({"skill": skill_dir.name, "findings": findings})

    if args.format == "json":
        print(json.dumps(report, indent=2))
    else:
        for entry in report:
            print(f"\n=== {entry['skill']} — {len(entry['findings'])} finding(s)")
            for f in entry["findings"]:
                loc = f"{f['path']}:{f['line']}" if f["line"] else f["path"]
                print(f"  [{f['severity'].upper():6}] {f['check']}  {loc}")
                print(f"           {f['message']}")
                if f["excerpt"]:
                    print(f"           > {f['excerpt']}")
        print(f"\n{total} finding(s) across {len(report)} skill(s): "
              f"{counts['high']} high, {counts['medium']} medium, {counts['low']} low.")
        if waived:
            print(f"{waived} finding(s) downgraded High → Medium by a "
                  f"maintainer-granted waiver on main ({WAIVERS_REF}). Still "
                  "findings; still yours to read.")
        print("Evidence for a human reviewer. A clean scan is not a pass "
              f"({CRITERIA_REF}).")

    # A waiver that matches nothing is either a sink that got fixed (delete the row)
    # or one whose code changed under it (re-review, then re-grant). Either way it is
    # stale, and a registry nobody prunes is a registry nobody reads. Reported, never
    # fatal: the tree under --root is only ever a subset of what the registry covers.
    for w in waivers:
        if not w["_used"]:
            print(f"note: stale waiver — {w['skill']} {w['check']} {w['file']} "
                  f"matched nothing ({WAIVERS_REF})", file=sys.stderr)

    # A High finding blocks; a Medium is recorded for a human to rule on, which
    # is what the N/A-with-reasoning rule in §3 is for.
    blocking = {
        "high": counts["high"],
        "medium": counts["high"] + counts["medium"],
        "low": total,
        "never": 0,
    }[threshold]
    if blocking and args.format == "text":
        print(f"\nFAIL: {blocking} finding(s) at or above severity {threshold!r}.",
              file=sys.stderr)
    sys.exit(1 if blocking else 0)


if __name__ == "__main__":
    main()
