# Getting set up

How to connect your AI assistant to Turnstile, prove the connection actually works, and
understand what you have (and haven't) been given permission to do. Ten minutes, once.

## Contents

- Connecting the Turnstile MCP
- "Added" is not "connected" — verify by probe
- What permissions mean here
- Integrations are configured in the app, not here
- What this connection cannot tell you
- Tools beyond this list
- Verify this area works

## Connecting the Turnstile MCP

Turnstile connects to AI assistants through an MCP connector. Where you add it depends on
which assistant you use:

- **claude.ai (web)** — Settings → Connectors → add a custom connector with the
  connection details your Turnstile admin provides.
- **Claude Desktop / Cowork** — add the same connector through the desktop app's
  connector settings.
- **ChatGPT** — supported via its connector settings as well, with the same details.

The connection details — the server address and how you sign in — come from your
Turnstile admin, and the step-by-step walkthrough for each assistant lives in Turnstile's
help center article on connecting an AI assistant at help.turnstile.ai. This guide stays
generic on purpose: the assistants' settings screens change more often than this file
does.

## "Added" is not "connected" — verify by probe

A connector can sit in your settings list looking healthy and still not work: the sign-in
may have expired, or permissions may not have been granted yet. So after adding it, don't
trust the settings screen — test it. Ask:

> *"Ping the Turnstile API and tell me if it's healthy."*

The assistant should call `Turnstile:ping_turnstile_api` and report a healthy response within a
few seconds. That one round trip proves the whole chain: the connector is reachable,
you're signed in, and Turnstile is answering.

If the probe fails: remove and re-add the connector, or disconnect and reconnect it to
trigger a fresh sign-in, then probe again. If it still fails, the connection details or
your account's access are the issue — that conversation is with your Turnstile admin.

## What permissions mean here

Your connection carries a set of permissions granted by your Turnstile admin, and they
fall into two broad kinds:

- **Read access** lets the assistant look things up — invoices, contracts, usage, customers.
  Reading never changes anything and never emails anyone.
- **Write access** lets the assistant take actions — approving or issuing an invoice, for
  example. Writes are granted separately, per area, and every write still asks for your
  confirmation before it runs (see `references/write-safety.md`).

If the assistant reports it can see some things but a tool "isn't available" for others, that
usually means the permission wasn't granted — by design, not by accident. Your admin
decides who gets write access to what.

## Integrations are configured in the app, not here

Your CRM, accounting, and payment integrations — HubSpot, Salesforce, Stripe,
QuickBooks, Xero, and the rest — are set up and managed inside the Turnstile app, not
through the MCP connector. Once connected there, their data flows into what the assistant can
already see (a synced customer, a payment status); you never wire an integration through
your AI assistant.

## What this connection cannot tell you

The MCP proves the connection works and shows what is in the account. It does not
expose account settings. There is no tool that:

- lists which integrations are enabled, or checks whether one is healthy;
- verifies a Stripe connection or a webhook;
- lists team members or their roles;
- reports which user or organization the connection is signed in as.

When someone asks "what integrations do I have turned on?", say this first, then point
to the app's Integrations page. Indirect signals exist; offer them, run them only if
asked, and present them as hints, never as a list: a `paymentProcessor` of `STRIPE` on a subscription or invoice
means Stripe is in use for that record; a CRM customer search that returns results
means a CRM is connected. Neither says what else is on.

## Tools beyond this list

Your session may include additional setup and connection tools beyond those named here —
Turnstile ships new MCP capabilities continuously, and your account's tool list is the
source of truth. If you see a tool here that your session lacks, it may not be available
on your plan yet; that is an account/rollout question for Turnstile support, not a
product gap.

## Verify this area works

Ask: *"Ping the Turnstile API, then list one customer so I know reads work."*

The assistant should call `Turnstile:ping_turnstile_api` and report it healthy, then call
`Turnstile:list_turnstile_customers` and name a single real customer from your account —
no confirmation prompts, since both are read-only. A healthy ping plus one real record
means you're fully connected; if either half fails, work through the reconnect steps
above before trying anything else in this skill.
