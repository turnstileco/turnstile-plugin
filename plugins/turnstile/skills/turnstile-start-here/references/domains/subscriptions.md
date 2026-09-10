# Subscriptions

Subscriptions are your live customer agreements: what each customer is on, what it's
worth, when it started, and when it comes up for renewal. Through the assistant, this area answers
"what's active, what's expiring, and what's it all worth?"

**One naming note, once:** what the app calls a *subscription*, the underlying system also
calls a *contract*. The assistant may mention "contract" tools — same record, two views: the
contract view is the agreement (terms, value, revisions), the subscription view is the
billing side (what gets invoiced, when). Everywhere below we say "subscription."

## What you can ask today

- "Which subscriptions are active right now?"
- "When does the Acme subscription end, and does it auto-renew?"
- "What comes up for renewal in the next 90 days?"
- "What's the annual recurring revenue across my subscriptions?"
- "Show me the full terms of the Northwind agreement."
- "Which subscriptions ended last quarter without renewing?"

## What these tools tell you

- `Turnstile:list_turnstile_subscriptions` — all your subscriptions with status, customer,
  and service dates. The starting point for "what's active?" and "what's expiring?"
- `Turnstile:get_turnstile_subscription` — one subscription in billing terms: total value,
  service dates, expiry, auto-renew, and its invoice history.
- `Turnstile:list_turnstile_contracts` — the same agreements from the contract side,
  with the negotiated value and terms. Both lists carry **annual recurring revenue
  (ARR)** per agreement.
- `Turnstile:get_turnstile_contract` — one agreement in contract terms: the negotiated
  value and terms behind the billing.

## Good to know

- **ARR is on both views.** Either list answers an ARR question; if the assistant
  reaches for contract tools rather than subscription tools, that is a choice of
  lens, not a data need. An ARR total is those per-record fields summed, one
  currency per total (`domains/reporting.md`).
- **Same record, two lenses.** A subscription and its contract share an identity; getting
  "both" is not double-counting, it's the agreement view and the billing view of one deal.
- **Renewal questions come from dates.** "What's up for renewal?" is answered by reading
  end dates and auto-renew flags off the list — expect the assistant to walk the list rather than
  query a special renewals report.
- **A single subscription can carry a long invoice history.** If you only want the
  agreement itself — dates, value, renewal — say so, and the assistant can skip the invoice
  detail rather than wading through it.
- **This skill does not teach amending, renewing, or terminating a subscription.** Use
  the assistant to spot what needs attention, then make the change in the Turnstile app. If
  your session carries contract write tools for those actions, they are Tier 2 in
  `../write-safety.md`: termination in particular takes effect immediately, with no
  draft step.

Your session may include additional subscription tools beyond those named here — Turnstile
ships new MCP capabilities continuously, and your account's tool list is the source of
truth. If you see a tool here that your session lacks, it may not be available on your plan
yet; that is an account/rollout question for Turnstile support, not a product gap.

## Verify this area works

Ask: **"List my active subscriptions."**

A good result: the assistant uses `Turnstile:list_turnstile_subscriptions` and returns
subscriptions with customer names, statuses, and dates that match what you see in the
Turnstile app. Empty results where you know agreements exist, or an error, means the
connection needs attention — not that the data is gone.
