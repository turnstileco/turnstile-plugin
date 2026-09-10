# Write safety: the three tiers

Every Turnstile MCP tool falls into one of three tiers. The tier decides how
the assistant behaves before calling it. This file is the rule; the domain files
apply it.

## Contents

- The three tiers
- Tier 0 — reads
- Tier 1 — reversible writes
- Tier 2 — irreversible or outward-facing
- The validation gate
- Unknown tools
- The confirmation script

## The three tiers

| Tier | What it covers | Before calling |
|---|---|---|
| 0 | Reads: `list_*`, `get_*`, `Turnstile:ping_turnstile_api` | Just call it |
| 1 | Reversible writes: drafts, edits, cancel-a-draft | Say what will change, wait for a yes |
| 2 | Irreversible or outward: issue, send, mark-paid, customer updates | Show exactly what will happen, get explicit confirmation, check the validation gate first |

The tiers restate Turnstile's own design: the platform keeps mistakes easy to
back out of, **except** the actions that leave the building — an email cannot
be unsent, a payment cannot be un-attempted, a terminal state has no
transition back.

## Tier 0 — reads

Call freely. Reads are how you orient: list first, then get the specific
record. Two habits keep reads safe for your context window: prefer filters
(status, customer, date range) over pulling the world, and before a pull that
could flood the session ("tell me about all my invoices"), narrow it first — ask
which customers, which period, or which status to scope to, with
`AskUserQuestion` where it exists and a plain question otherwise.

One caution that looks like a read but is not:
`Turnstile:evaluate_turnstile_invoice_readiness` **persists its result on the
invoice**. It is a write dressed as a check — treat it as Tier 1 and say so
before running it.

## Tier 1 — reversible writes

Creating or editing a draft, cancelling a draft invoice
(`Turnstile:cancel_turnstile_invoice` — a DRAFT moves to CANCELLED and can be
uncancelled). The assistant states what will change and waits for a yes before
calling the tool. A mistake here is recoverable — that is the definition of
the tier — so the confirmation is short: the record, the change, "go ahead?".
What the tier does not need is the Tier 2 ritual of showing what a customer
will see, because nothing leaves the building.

## Tier 2 — irreversible or outward-facing

Four classes, and the class explains the caution:

- **Sends to a customer** — `Turnstile:issue_turnstile_invoice` ("cannot be
  undone — the email will be delivered"), `Turnstile:resend_turnstile_invoice`
  (every call emails the customer again; there is no dedup).
- **Terminal state change** — `Turnstile:mark_turnstile_invoice_as_paid`
  ("once marked as paid the invoice cannot be transitioned back").
- **Writes through to external systems** —
  `Turnstile:update_turnstile_customer` updates the payment-processor record
  too, and its billing-address field is replaced **atomically**: an omitted
  address field is cleared, not kept. Read the current record first, show the
  exact before/after.
- **Moves money** — payment-collection actions, where they appear on your
  account.

For Tier 2, the assistant must: (1) name the specific record and the specific
action, (2) show what the customer will see or what becomes unchangeable,
(3) ask for explicit confirmation — "proceed?" answered by the human, not
inferred — and (4) check the validation gate below where one exists. One
confirmation covers one action on one record. A batch needs one confirmation
that is (1) fully enumerated — every action with its record, amount, and
effect, nothing summarized away; (2) eligibility-filtered — only items the
validation gate marks `allowed`, with blocked ones listed separately and their
`blockingReasons` verbatim; (3) vetoable line by line, so a bare "yes"
authorizes exactly the enumerated set; and (4) re-checked per item at
execution, because eligibility can change between the list and the call.

## The validation gate

Invoices carry their own safety gate. `Turnstile:get_turnstile_invoice`
returns `eligibleActions` — for each action, whether it is `allowed` and, if
not, human-readable `blockingReasons`. `Turnstile:list_turnstile_invoices`
returns the same gate per invoice when asked with `expand: ["eligibleActions"]`
(the tool caps that expand at 25 invoices per response), which is the right way
to triage which invoices are ready. **Triage from the list; act from the get:
read the single invoice again immediately before any write**, because
eligibility changes between the list and the call. Honor `allowed`; when something is blocked, relay the
blocking reason verbatim — it is written for a human — and never re-derive
"is this safe" from status fields yourself.

Other write surfaces may expose their own validation or preview tools in
your session (names starting with `validate_` or ending `_preview`). Prefer
running those before the real action wherever they exist.

## Unknown tools

Your session may contain tools this skill does not describe — the MCP grows
continuously. For an unfamiliar tool, default to caution: **treat it as
Tier 2 unless its own description clearly marks it read-only.** A tool's
description is good evidence for what it does; it is not a safety waiver.

## The confirmation script

What good Tier 2 behavior sounds like:

> Invoice INV-2041 for Acme Co, $12,400.00, due Sep 15. Its validation gate
> allows issuing. Issuing will email the invoice to billing@acme.com and
> cannot be undone. Issue it?

What it never sounds like: "I went ahead and issued the three invoices that
looked ready."
