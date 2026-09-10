# Reporting

The questions the assistant can answer about your revenue, usage, and payment picture — all from
read-only tools, so nothing in this file can change a record or email anyone. Think of it
as an analyst who can pull the numbers on demand: you ask the question in plain English,
the assistant picks the right reads and does the arithmetic.

## The four reads behind most reports

- `Turnstile:list_turnstile_contracts` — your subscriptions viewed as agreements (the
  MCP calls the same records "contracts"; `domains/subscriptions.md` explains the two
  views). Each record carries its annual recurring revenue, as does each record on
  the subscription list; either answers recurring-revenue questions: *"What's our ARR right now?"*, *"Which subscriptions are
  our biggest?"*, *"How is revenue spread across customers?"*
- `Turnstile:list_turnstile_aggregated_usage` — usage totals per subscription over a time
  range, defaulting to the trailing 12 months. The tool for trend questions: *"How has
  usage on the Acme subscription moved this year?"*, *"Which customers are growing?"*
- `Turnstile:list_turnstile_raw_usage` — the individual usage events underneath those
  totals, when a total looks off and you want to see what actually came in.
- `Turnstile:list_turnstile_invoices` — the same invoice list from the billing area, worn
  as a reporting hat: payment timing, how long invoices sit unpaid, issued-versus-paid
  totals by month, which customers pay promptly and which don't.

## Native or computed?

Not every figure in this area comes from Turnstile the same way, and a good answer says
which kind it is.

| Figure | Where it comes from |
|---|---|
| Usage trends | Read directly: `Turnstile:list_turnstile_aggregated_usage` returns totals per period |
| ARR, total contract value | A field on every subscription and contract record; the total is those fields summed, one currency per total (each record carries its own `currency`, and a GBP subscription never adds into a USD figure) |
| Payment timing, days to pay, DSO | Computed by the assistant from paid invoices: `issueDate` against `paidDate`, per invoice, then averaged |
| Issued versus paid by month | Computed from the invoice list |
| Growth accounting, NRR and GRR, cohorts | Computed from subscription and invoice records; nothing native |

Computed figures are only as good as the underlying data. Payment timing on an account
with no real paid invoices (a demo or a fresh implementation) is not a measurement, and
the assistant should say so instead of reporting a number.

## Questions worth asking

- *"Give me an ARR overview — total, and the top ten subscriptions by value."*
- *"Chart usage by month for our three largest subscriptions."*
- *"How long does it take our customers to pay, on average? Who's slowest?"*
- *"Compare what we invoiced last quarter to what's actually been paid."*

A note on completeness: the assistant reads these lists to the end, so totals and
averages are built on everything, not just the first screen; when the set would be too
large for the session, it narrows the ask first (a period, a customer set) rather than
sampling. Aggregated usage works differently — it is time-ranged rather
than paged, so you set the window ("last 6 months") instead.

## What a good answer looks like

Expect the assistant to show its work in finance terms, not tool terms: the figure you asked
for, the period it covers, how many records it was built from, and any caveats — for
example, *"ARR is $2.4M across 31 active subscriptions as of today; two end within
60 days and account for $180K of that."* If a number can be cut more than one way (by
customer, by month, by product), the assistant should say which cut it chose, and you can ask
for another. Two habits worth keeping:

- **Ask for the basis.** "How many invoices is that average built on?" is always a fair
  question, and the assistant should always be able to answer it.
- **Name the window.** "Last quarter" and "the last 90 days" are different numbers.
  The assistant will state the window it used; correct it if it guessed wrong.

## What lives in the Turnstile app instead

Honest boundary: the full accounting views — journal entries, revenue recognition
schedules, and the formal reports your finance close depends on — live in the Turnstile
app's Reporting area, not in these tools. The assistant is excellent for ad-hoc questions and
quick cuts of the data; for the books of record, use the app.

## Tools beyond this list

Your session may include additional reporting and analytics tools beyond those named
here — for example, tools around metrics — Turnstile ships new MCP capabilities
continuously, and your account's tool list is the source of truth. If you see a tool here
that your session lacks, it may not be available on your plan yet; that is an
account/rollout question for Turnstile support, not a product gap.

## Verify this area works

Ask: *"What's our total ARR across active subscriptions?"*

The assistant should call `Turnstile:list_turnstile_contracts`, page through the full list, and
return a single dollar figure plus a short breakdown of the largest subscriptions — with
no confirmation prompts, because everything here is read-only. If the list comes back empty
when you know you have them, your connection or permissions need a look — see
`references/domains/getting-set-up.md`.
