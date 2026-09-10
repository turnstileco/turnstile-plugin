# Changelog — turnstile-start-here

Newest first. Semver per [SPEC.md](../../../../SPEC.md): PATCH = fix or
wording, MINOR = new backward-compatible capability, MAJOR = breaking. Every
PR that touches this skill adds an entry here — CI checks.

## 1.0.0 — 2026-09-09

First public release.

- **The module menu.** Nine entries in the vocabulary the Turnstile app uses —
  quotes, subscriptions, invoices and billing, customers, catalog, reporting,
  connect and verify — each with example prompts and a domain reference
  behind it.
- **Write safety in three tiers.** Every write waits for a yes. Before acting
  on an invoice the skill re-reads that single invoice, honors its action
  gate, and surfaces any blocking reasons verbatim: triage from the list, act
  from the get.
- **Money is handled correctly.** Amounts are minor units, currency sits on
  the line item, and a total stays in one currency — never a blended sum.
- **What the connection cannot tell you**, stated plainly, so your assistant
  routes you to the Turnstile app instead of guessing.
- **The session's own tool list is authoritative.** The skill reads what your
  assistant actually has connected rather than carrying a frozen roster that
  would go stale.
- **Narrow before you pull.** Ahead of a request that could return more than a
  conversation can hold, the skill asks which customers, which period, or
  which status to scope to.

Versions before `1.0.0` were pre-release drafts and are not published here.
