# Workflows

Five end-to-end recipes for the jobs Turnstile customers run most. Each one names its
trigger phrase, the steps the assistant takes, where it stops for your confirmation, and what
the finished output looks like. Recipes 1, 4, and 5 are entirely read-only; recipes 2
and 3 include actions that email customers, so they follow the confirmation rules in
`references/write-safety.md` to the letter.

## Contents

- [1. Where does my pipeline stand?](#1-where-does-my-pipeline-stand)
- [2. Month-end invoice review](#2-month-end-invoice-review)
- [3. Collections chase](#3-collections-chase)
- [4. Renewal check](#4-renewal-check)
- [5. Usage sanity check](#5-usage-sanity-check)

## 1. Where does my pipeline stand?

**Trigger:** *"Where does my pipeline stand?"* — or "what quotes are out", "what's
waiting on signature".

1. `Turnstile:list_turnstile_quotes` — pull the open quotes, paging until complete.
2. For quotes worth a closer look, `Turnstile:get_turnstile_quote` for the detail and
   `Turnstile:get_turnstile_quote_signatures` for who has signed and who hasn't.
3. Where a quote is stuck, `Turnstile:list_turnstile_quote_participants` shows who is on
   it — the name to chase.

**Safety stops:** none needed — every step is read-only.

**Output:** a short pipeline summary grouped by state — drafts, sent and awaiting
signature, signed — with each quote's customer and value, and a "stuck" list naming the
quote, how long it has waited, and who it is waiting on.

## 2. Month-end invoice review

**Trigger:** *"Run my month-end invoice review."*

1. `Turnstile:list_turnstile_invoices` filtered to invoices that are not paid, paged to
   completeness, grouped by status: drafts, requires-review, issued-but-unpaid.
2. For each invoice requiring review, `Turnstile:get_turnstile_invoice` — the full
   detail **and** the invoice's own gate of currently allowed actions. The list can carry
   the gate too (`expand: ["eligibleActions"]`) for triage; the action still follows a
   fresh fetch of that one invoice.
3. The assistant presents the requires-review invoices one at a time: customer, amount, lines
   worth a glance (`Turnstile:list_turnstile_invoice_lines` if the total needs
   explaining), and what the gate allows.
4. If you approve one: `Turnstile:approve_turnstile_invoice` — confirmed with you first.
   Approval clears review; it sends nothing.
5. To send it: `Turnstile:issue_turnstile_invoice` — **only** if that invoice's gate
   allows issuing, and **only** after you explicitly confirm that specific invoice.
   Issuing emails your customer and cannot be undone, and the assistant says so each time.

**Safety stops:** the gate is re-checked per invoice via
`Turnstile:get_turnstile_invoice` before any action; a blocked action is relayed in
Turnstile's own words and never worked around; approve and issue are each confirmed per
invoice — never "issue them all" in one breath. See `references/write-safety.md`.

**Output:** a month-end summary — counts and totals by status, the reviewed invoices
with approve/issue decisions recorded, and a leftover list of anything blocked, with
Turnstile's stated reason verbatim.

## 3. Collections chase

**Trigger:** *"Who do I need to chase for payment?"*

1. `Turnstile:list_turnstile_invoices` filtered to issued, unpaid, past-due invoices,
   paged to completeness.
2. Compute days outstanding from each due date and sort worst-first.
3. `Turnstile:get_turnstile_customer` for the top offenders — the billing contact who
   should get the nudge.
4. If you want an invoice re-sent: first `Turnstile:get_turnstile_invoice` to confirm
   resending is currently allowed, then `Turnstile:resend_turnstile_invoice` — after an
   explicit per-invoice confirmation, because **every resend emails the customer again**,
   with no duplicate protection. Two resends means two emails.

**Safety stops:** resend is confirmed one invoice at a time, and the assistant states plainly
that an email will go out before you say yes. A polite alternative — you emailing the
contact yourself with the invoice details the assistant drafted — costs nothing and is often
the better first move. See `references/write-safety.md`.

**Output:** an aging table — customer, invoice, amount, days outstanding, billing
contact — plus a record of which invoices were re-sent, if any.

## 4. Renewal check

**Trigger:** *"What's coming up for renewal?"*

1. `Turnstile:list_turnstile_contracts` — every subscription as an agreement record
   (the MCP calls these "contracts"; same record, see `domains/subscriptions.md`), paged
   to completeness, with each one's end date and value in hand.
2. Filter to subscriptions ending inside your window (next 60 or 90 days, your call)
   and sort by end date.
3. For any subscription that deserves a closer look, `Turnstile:get_turnstile_contract`
   for the full terms.

**Safety stops:** none needed — read-only throughout. Renewing or amending a
subscription is not part of this recipe; do that in the Turnstile app, or through
contract write tools your session may carry, which are Tier 2 in
`references/write-safety.md`.

**Output:** a renewal runway — each expiring subscription with customer, end date, and
annual value — plus the headline number: total ARR at stake in the window.

## 5. Usage sanity check

**Trigger:** *"Does the usage on this subscription look right?"*

1. `Turnstile:list_turnstile_aggregated_usage` for the one subscription in question —
   monthly totals over a sensible window (it defaults to the trailing 12 months).
2. Eyeball the shape together: a sudden spike, a month at zero, or a step-change with no
   business explanation is worth a closer look.
3. For any suspicious period, `Turnstile:list_turnstile_raw_usage` — the individual
   events underneath the total, to see whether the anomaly is real usage, a burst of
   duplicates, or a gap where events stopped arriving.

**Safety stops:** none needed — read-only. One firm boundary: if the numbers look wrong,
the fix is **not** to adjust anything from here. The assistant summarizes the evidence — the
subscription, the period, expected versus observed — into a note you can hand to
Turnstile support, who can correct usage data safely.

**Output:** a verdict per period — "looks consistent" or "anomaly found" — with the
evidence, and a ready-to-send summary for support when something is off.
