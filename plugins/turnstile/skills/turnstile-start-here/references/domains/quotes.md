# Quotes

Quotes are how deals move through Turnstile: you build a quote, send it to your customer,
and they sign or accept it. Through the assistant, this area is about **pipeline visibility** — seeing
what's out, who has signed, what's stuck, and what has happened on a quote since you last
looked. This skill teaches the reads; building and sending quotes happens in the Turnstile
app, or through quote write tools your session may carry (see "Good to know" below).

## What you can ask today

- "Show me my open quotes."
- "Has anyone signed the Acme renewal quote yet? Who's still outstanding?"
- "Who is on the Northwind quote — on our side and theirs?"
- "Walk me through everything that's happened on the Globex quote this month."
- "What documents are attached to the Initech quote?"
- "How is the Acme quote set up to close — e-signature, or accept-and-pay?"

## What these tools tell you

- `Turnstile:list_turnstile_quotes` — your quote pipeline: each quote with its customer
  and current status, newest first. The starting point for "what's out there right now?"
- `Turnstile:get_turnstile_quote` — the full picture of one quote: customer, status,
  value, and dates.
- `Turnstile:get_turnstile_quote_signatures` — who has signed and who hasn't, person by
  person. The definitive answer to "is this deal actually signed?"
- `Turnstile:get_turnstile_quote_workflow_settings` — how the quote is set up to close:
  e-signature, accept-and-pay, or recorded without a signing step.
- `Turnstile:list_turnstile_quote_participants` — everyone attached to the quote, on your
  side and the customer's, and their roles.
- `Turnstile:list_turnstile_quote_documents` — the documents that belong to the quote,
  such as the generated quote PDF and anything uploaded alongside it.
- `Turnstile:list_turnstile_quote_events` — the quote's activity history: what changed,
  and when. Good for "what happened since Monday?"
- `Turnstile:list_turnstile_quote_order_flow_events` — the customer-facing steps of the
  signing/acceptance flow, so you can see exactly where a quote is stuck.

## Good to know

- **Signature status is per-person, not per-quote.** A quote can look "sent" while one of
  three signers has signed. When someone asks "is it signed?", the signatures view is the
  answer — don't infer it from the quote's overall status.
- **Two kinds of history.** The events list is the quote's internal activity trail; the
  order-flow events are the customer's journey through signing or accepting. If a deal
  feels stalled, the order-flow view usually shows the exact step it stopped at.
- **Your session may carry quote write tools** (create, edit, publish). This skill does
  not teach them yet. If you use one, publishing sends the quote to your customer, so it
  follows the Tier 2 rules in `../write-safety.md`. The Turnstile app remains the
  richest place to build complex quotes: build line items, publish, and send there,
  then come back to the assistant to watch progress and answer questions about the pipeline.

Your session may include additional quote tools beyond those named here — Turnstile ships
new MCP capabilities continuously, and your account's tool list is the source of truth. If
you see a tool here that your session lacks, it may not be available on your plan yet; that
is an account/rollout question for Turnstile support, not a product gap.

## Verify this area works

Ask: **"List my five most recent quotes."**

A good result: the assistant uses `Turnstile:list_turnstile_quotes` and returns a short list of
real quotes — customer names and statuses you recognize from the Turnstile app. If it comes
back empty when you know quotes exist, or errors, the connection (not the product) needs
attention.
