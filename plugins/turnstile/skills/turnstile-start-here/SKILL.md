---
name: turnstile-start-here
description: "Orientation for the Turnstile MCP: what your connected tools can do, organized by the modules you know from the Turnstile app (quotes, subscriptions, invoices and billing, customers, catalog, reporting), with example prompts, read-vs-write safety guidance, and a starting menu. Use when someone is new to the Turnstile MCP, or asks 'what can I do with Turnstile', 'where do I start', 'show me the menu', 'what can this connector do', 'help me get started with Turnstile', or is about to take a first write action (issuing, sending, updating) through the Turnstile MCP."
version: 1.0.0
metadata:
  class: generative-workflow
  persona: all
  recipe-type: skill
  supervision: asks-before-each-action
  risk: medium
  access: read-write
  connectors: none
  scopes: customer:read, customer:write, invoices:read, invoices:write, quote:read, subscription:read, contract:read, usage:read, metrics:read, metrics:write, product:read, product:write, units:read, units:write
  owner: Explosion5000
  audience: public
  surfaces: claude-code, cowork
---

# Turnstile Start Here

Turnstile runs your quote-to-cash: quotes, subscriptions, invoices, customers,
catalog, reporting. Its MCP connection lets you work all of that from a
conversation. This skill is the front door, and it answers one question:
*what can I do with Turnstile from here, and how do I do it safely?* It maps
what you can do, in the same module language the Turnstile app uses, and
teaches the safety habits that matter when a tool can email your customer.

## Contents

- What goes in, what comes out
- Two rules before anything else
- First time here? Connect and verify
- The menu
- Your first five prompts
- Read vs write, in one paragraph
- Routing: where the detail lives
- Boundaries
- Get help

## What goes in, what comes out

**Inputs:** a connected Turnstile MCP session and a question — "what can I do?",
a module name, a menu number, or a task in your own words. No files, no
setup beyond the connection itself.

**Outputs:** orientation and guided action — the menu of what your account can
do, example prompts that work today, guided walkthroughs from the domain
references, and for any write, a named record, a stated consequence, and an
explicit confirmation before anything irreversible happens. This skill never
takes a Tier 2 action (see `references/write-safety.md`) without your
confirmation, and it produces no artifacts or files.

## Two rules before anything else

**1. Your session's tool list is the source of truth.** Turnstile ships,
updates, and sometimes retires MCP tools continuously, and your account's
plan and rollout decide exactly which tools you have. This skill describes
the stable shape of the surface — the modules, the safety tiers, the
workflows — not the authoritative tool list:

- A tool named here but **missing from your session**: it may not be
  available on your plan yet. Say so — never "Turnstile can't do X". The
  Turnstile app can usually do it today, and support can say what's rolling
  out.
- A tool **in your session but not named here**: it is newer than this
  skill. Its own description tells you what it does; for how carefully to
  treat it, `references/write-safety.md` § Unknown tools.
- For the full list, read the tools in this session. This skill ships no
  roster of its own, because any copy is older than the session that loads it.
- Tool names here are written `Turnstile:<tool_name>`. The prefix before the
  colon differs by host (a connector name on one, a plugin prefix on another);
  the name after the colon is what to match against your session's list.

**2. Reads are free; writes follow the tiers.** Anything that lists or gets
is safe to explore with. Anything that issues, sends, marks, or updates
follows the three-tier rules in `references/write-safety.md` — the short
version: irreversible or outward actions get a named record, a stated
consequence, and your explicit yes, every time.

## First time here? Connect and verify

If Turnstile tools already appear in this session, skip to the menu, with one
exception: when someone says they *just* connected, ping once first, because
"added" is not "connected". If no tools appear:
your Turnstile admin connects the Turnstile MCP where you chat (on claude.ai:
Settings → Connectors; similar on Claude Desktop and other assistants —
Turnstile's help center article "Connect Turnstile to an AI assistant using
MCP" at help.turnstile.ai has current steps per surface, including ChatGPT —
this guidance applies to any assistant connected to the Turnstile MCP).

Then **verify — "added" is not "connected"**: run
`Turnstile:ping_turnstile_api`. A healthy response proves the pipe works. No
response or an auth error means reconnect or reauthorize before trusting
anything else. `references/domains/getting-set-up.md` covers this end to end.

## The menu

When someone asks "what can I do?" (or anything menu-shaped), present
exactly this, numbered, then act on their pick — a number, a name, or free
text all work. A bare pick means: load that module's reference, describe what
it can do, and offer its prompts. Run a read only when they ask for one.

1. **Quotes** — where every quote stands: sent, viewed, signed, stuck.
2. **Subscriptions** — what's active, terms, ARR, what's renewing. (Your
   session's tools also call these records "contracts": one record, two views.)
3. **Invoices & Billing** — status, aging, collections; issue and resend
   with guardrails.
4. **Customers** — accounts, billing details, and each customer's
   subscriptions and invoices.
5. **Catalog** — products, metrics, and units. (Plans are managed in the
   Turnstile app.)
6. **Reporting** — ARR, usage trends, and payment timing computed from
   invoices.
7. **Connect & verify** — prove the connection works and see what is in
   your account. (Integrations, users, and webhooks are managed in the app.)
8. **Learn the MCP** — how this all works: safety tiers, workflows, what's
   read vs write.
9. **Or just tell me what you need in your own words.**

A number, a name, or free text all work. Every module conversation keeps
option 9 open — always accept a plain-language ask instead of a pick.

**If `AskUserQuestion` is available in this session**, follow the menu with
one call to narrow the start:

- `question`: "Where do you want to start?"
- `options`: the three modules that best fit what they have already said;
  absent any signal, "Invoices & Billing", "Quotes", "Subscriptions"

Three named options, never more — the tool caps at four and supplies its own
free-text choice, which covers option 9 and the six modules not named. Do not
spend a slot restating it, and do not name its label in your own text; the
label differs by surface.

If `AskUserQuestion` is not available, stop after the menu and let them answer
however they like. Never announce the tool's absence. The nine entries above
render as text on every surface — they are what the user needs to see either
way, so present them before the call, not instead of it.

## Your first five prompts

Copy any of these into the chat, verbatim:

1. "Show me my unpaid invoices — issued and not yet paid — sorted by how
   overdue they are."
2. "Which quotes are still waiting on a signature, and who's holding them?"
3. "List my active subscriptions with their renewal dates and ARR."
4. "How does usage this month compare to last month for my biggest
   customer?"
5. "Which customers are slowest to pay?"

All five are reads — safe to run right now, no confirmation needed.

## Read vs write, in one paragraph

Everything you can do splits into looking and acting. Looking (`list_*`,
`get_*`) is always safe. Acting ranges from harmless drafts to emailing a
customer an invoice that cannot be recalled — so acting follows
`references/write-safety.md`: Tier 1 (reversible) says what will change and
waits for your yes, Tier 2 (irreversible or outward) also shows you exactly
what will happen first, and invoice actions check the invoice's own
`eligibleActions` validation gate first via `Turnstile:get_turnstile_invoice`.

## Routing: where the detail lives

| Menu pick | Read this | Sibling skills, if installed |
|---|---|---|
| 1 Quotes | `references/domains/quotes.md` | — |
| 2 Subscriptions | `references/domains/subscriptions.md` | renewals-overview, milestone-lapse-risk |
| 3 Invoices & Billing | `references/domains/invoices-and-billing.md` | invoice-status-overview, days-to-pay-trend-report, turnstile-invoice-workflow |
| 4 Customers | `references/domains/customers.md` | — |
| 5 Catalog | `references/domains/catalog.md` | — |
| 6 Reporting | `references/domains/reporting.md` | revenue-mom, usage-trend-report, turnstile-custom-revenue-analytics |
| 7 Connect & verify | `references/domains/getting-set-up.md` | — |
| 8 Learn the MCP | `references/write-safety.md`, then `references/workflows.md` | turnstile-briefing |
| End-to-end recipes | `references/workflows.md` | — |

Load the reference for the module in play — not all of them. A sibling skill
column entry means: if that skill is installed in this session, offer it
("there's a dedicated invoice-status report skill here — want me to use
it?"); if it isn't installed, don't mention it.

## Boundaries

Never do these:

- Never conclude "Turnstile can't do X" from a tool being absent — absence
  means *not available in this session*, and the app or a newer rollout may
  do it.
- Never narrate a connection or OAuth step as though you performed it — the
  human clicks; you verify with `Turnstile:ping_turnstile_api` afterward.
- Never take a Tier 2 action without naming the record, stating the
  consequence, and getting an explicit yes. "The invoices looked ready" is
  never sufficient grounds.
- Never work around a blocked action. When `eligibleActions` says
  `allowed: false`, relay its `blockingReasons` message verbatim and stop.
- Never pull entire datasets to answer a narrow question — filter, and when
  the ask could flood the session, narrow it first: which customers, which
  period, which status (`AskUserQuestion` where available, a plain question
  otherwise).
- Never present this skill's tool descriptions as the limit of the product —
  the session tool list and the tools' own descriptions are fresher than any
  document, this one included.

## Get help

Something errored, a number looks wrong, or a capability question needs a
human: say so plainly and offer the paths — the customer's Turnstile support
channel, help.turnstile.ai, or (where the session includes it and the user
confirms) `Turnstile:create_turnstile_support_request`, which opens a real
support ticket. Never file a ticket without asking first.
