# Customers

Customers are the companies you sell to — the record that quotes, subscriptions, and
invoices all hang off. Through the assistant, this area covers looking customers up, checking their
billing details, making careful updates to those details, and raising a support ticket
with Turnstile when something needs a human.

## What you can ask today

- "Find the customer record for Acme." (partial names work)
- "What billing email and address do we have on file for Northwind?"
- "List our customers — who's been added most recently?"
- "Update Globex's billing email to ap@globex.com."
- "Open a support ticket with Turnstile about this."

## What these tools tell you

- `Turnstile:list_turnstile_customers` — your customer list. It can filter by name, and
  the filter matches partial names regardless of capitalization — "acme" finds "Acme
  Corporation." When a fragment matches more than one customer, show the matches
  and ask which one before pulling anything else.
- `Turnstile:get_turnstile_customer` — one customer's full record: billing email, billing
  address, and standing.
- `Turnstile:get_turnstile_customer_name` — a quick name lookup when the assistant just needs to
  confirm which customer an ID refers to.
- `Turnstile:update_turnstile_customer` — edits a customer's details (name, billing email,
  billing address). **This is a real change** — see below before using it.
- `Turnstile:create_turnstile_support_request` — opens a genuine support ticket with
  Turnstile's team. The assistant should always show you what it's about to file and ask first —
  a ticket creates real work for a real person.

## Good to know

- **Updating a customer is careful work — insist on the before/after.** Two things make
  this edit unforgiving:
  1. **The billing address is replaced whole, not merged.** If an update supplies a new
     address but leaves out a field — say, the postal code — that field is *cleared*, not
     kept. A well-meant "fix the street line" can silently blank the rest of the address.
  2. **Changes flow straight through to your payment processor.** What lands here lands
     where invoices and payments are handled.
  So the working rule: before any customer update, the assistant must read the current record,
  show you the exact current values next to the exact proposed values, and get your
  explicit go-ahead. If the assistant skips that, ask for the before/after — never approve an
  update you haven't seen in full.
- **"History" means the records that hang off the customer.** There is no per-customer
  activity log or event timeline in the MCP. What the assistant can pull is each customer's
  subscriptions, contracts, and invoices, because
  `Turnstile:list_turnstile_subscriptions`, `Turnstile:list_turnstile_contracts`, and
  `Turnstile:list_turnstile_invoices` all take a `customer` filter. "Show me Acme's
  history" means those three lists, and the assistant should say so rather than imply a
  timeline exists.
- **For "who is paying us?", start from subscriptions, not the customer list.** The
  customer list has no subscription filter and includes every record ever created,
  prospects and test entries included. `Turnstile:list_turnstile_subscriptions` with
  `status: ACTIVE` returns the set under contract today, and every subscription carries
  the customer's name and id, so no second lookup is needed.
  `Turnstile:list_turnstile_contracts` with `status: active` is the same set viewed
  as agreements; both carry ARR. Under contract is not the same as paid up: an active subscription
  can carry $0 ARR, so say "active" rather than "paying", and for who has settled
  their invoices use the invoice list. Any ARR figure in the answer is a field
  summed, one currency per total, and says so (`domains/reporting.md`).
- **A customer id that resolved a moment ago and now returns 404** is a retry, not a
  conclusion. Try once more, then report what happened; do not tell the user the
  customer is gone.
- **Name search beats scrolling.** Rather than paging through the whole list, give the assistant
  a fragment of the name and let the filter find it.
- **Support requests are real tickets.** Great for "this looks wrong on Turnstile's side"
  — but confirm the summary before it's filed, and file once, not repeatedly.

Your session may include additional customer tools beyond those named here — Turnstile
ships new MCP capabilities continuously, and your account's tool list is the source of
truth. If you see a tool here that your session lacks, it may not be available on your
plan yet; that is an account/rollout question for Turnstile support, not a product gap.

## Verify this area works

Ask: **"Find our customer record for [a customer name you know]."**

A good result: the assistant uses `Turnstile:list_turnstile_customers` with the name filter and
returns the customer you meant, with billing details that match the Turnstile app. If a
customer you know exists doesn't come back, the connection needs attention.
