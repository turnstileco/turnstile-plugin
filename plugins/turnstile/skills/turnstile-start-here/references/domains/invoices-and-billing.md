# Invoices & billing

What the assistant can see and do with your invoices. Visibility comes first — most days you only
need the reads. The lifecycle actions come second, and each one is labeled with what it
really does, because in this area a mistake can email a customer. The full safety tier
system is in `references/write-safety.md`; this file tells you how it applies to invoices.

## Contents

- [See where your invoices stand](#see-where-your-invoices-stand)
- [The safety gate: check before any change](#the-safety-gate-check-before-any-change)
- [Lifecycle actions, each with its safety posture](#lifecycle-actions-each-with-its-safety-posture)
- [Tools beyond this list](#tools-beyond-this-list)
- [Verify this area works](#verify-this-area-works)

## See where your invoices stand

Three read-only tools cover almost every invoice question, and none of them can change
anything or email anyone:

- `Turnstile:list_turnstile_invoices` — your invoice list, filterable by status (draft,
  issued, and so on), payment status, customer, due date, billing entity, subscription,
  requires-review, and issue-date and target-issue-date ranges, among others; the tool's
  own schema is the authoritative filter list. This is the tool behind questions like
  *"What's unpaid right now?"*, *"Which invoices are overdue?"*, and *"What's still
  waiting on review?"* The assistant reads the list to the end, so "show me all overdue
  invoices" really means all of them. Invoice rows carry their line items, so an open-ended
  ask can flood the session: before one, narrow it — which customers, which period, which
  status — with `AskUserQuestion` where it exists and a plain question otherwise.
- **"Unpaid" means `status: ISSUED`.** An issued invoice is one the customer owes; a
  draft is not owed yet, so leave drafts out of an unpaid view unless asked, and leave
  `UNCOLLECTIBLE` invoices out too unless asked. `paymentStatus` is a filter, not a
  field on the rows; the row carries `paymentSubStatus`, which is often null.
- **Money is in minor units, and currency lives on the line items.** An invoice's
  `totalChargeMinor` is cents (or the currency's smallest unit): divide by 100 before
  showing a dollar figure, or a naive read overstates by 100×. The invoice row does not
  carry a currency; each line item does. Group totals by the line-item currency and
  never add two currencies into one number.
- `Turnstile:get_turnstile_invoice` — one invoice in full detail, including which actions
  are currently allowed on it (more on that gate below).
- `Turnstile:list_turnstile_invoice_lines` — the line items behind an invoice, when you
  want to see what a total is made of.

Good starting prompts: *"Give me an aging view of unpaid invoices"* · *"Which invoices
require review before they can go out?"* · *"Show me everything due in the next two weeks."*

## The safety gate: check before any change

Every Turnstile invoice knows which actions are currently allowed on it, and why the
others are blocked. That answer comes back with `Turnstile:get_turnstile_invoice`, and
the invoice list carries it too when asked with `expand: ["eligibleActions"]` (the tool
caps that expand at 25 invoices per response), which is how to triage a batch. Triage
from the list; act from the get: read the single invoice again immediately before any
write. No exceptions, even if the invoice was on screen a moment ago.

- If the gate says an action is allowed, the assistant may offer it (and still asks you before
  doing it).
- If the gate says an action is **not** allowed, the assistant relays the blocking message to you
  word for word — it is written by Turnstile for exactly this moment (for example, that
  usage data is still being collected). The assistant does not paraphrase it, second-guess it, or
  look for a workaround. A blocked action stays blocked until Turnstile says otherwise.

## Lifecycle actions, each with its safety posture

Where review is required, the flow is **approve, then issue** — two separate, separately
confirmed steps.

- `Turnstile:evaluate_turnstile_invoice_readiness` — **careful: this is a write dressed as
  a check.** It saves its result onto the invoice, so the assistant asks before running it rather
  than treating it as a free look. Usually the gate above already answers the question.
- `Turnstile:approve_turnstile_invoice` — clears the review requirement on an invoice that
  was waiting on someone's sign-off. It does not send anything.
- `Turnstile:issue_turnstile_invoice` — **irreversible.** Issuing finalizes the invoice
  and sends a real email to your customer, and that email cannot be recalled. The assistant will
  say this plainly and get your explicit confirmation, one invoice at a time, every time.
- `Turnstile:cancel_turnstile_invoice` — moves a draft to cancelled. Recoverable — nothing
  has been sent — and, like every write, confirmed first.
- `Turnstile:resend_turnstile_invoice` — **emails the customer again on every single
  call.** There is no duplicate protection, so "resend it twice" means two more emails in
  their inbox. The assistant confirms before each send.
- `Turnstile:mark_turnstile_invoice_as_paid` — **terminal.** Records a payment that
  happened outside Turnstile (a wire, a check) and closes the invoice for good. Use it
  only when you're certain the money actually arrived.

Every one of these follows the confirmation rules in `references/write-safety.md`.

## Tools beyond this list

Your session may include additional invoicing tools beyond those named here — Turnstile
ships new MCP capabilities continuously, and your account's tool list is the source of
truth. If you see a tool here that your session lacks, it may not be available on your
plan yet; that is an account/rollout question for Turnstile support, not a product gap.

## Verify this area works

Ask: *"List my five most recent invoices with their status and payment status."*

The assistant should call `Turnstile:list_turnstile_invoices` and come back with a short table or
list — each invoice with its customer, amount, status (such as draft or issued), and
payment state — without asking for any confirmation, because reading is always safe.
The list carries a `customerId`, not a name; one
`Turnstile:get_turnstile_customer_name` per distinct customer fills the column. If it
errors or comes back empty when you know invoices exist, revisit
`references/domains/getting-set-up.md`.
