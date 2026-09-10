---
name: skill-name
description: What this skill does and when Claude should use it, written in third person with the trigger phrases a user would actually type. ("Answers X when the user asks 'show me Y', 'which Z are overdue', ...")
version: 0.1.0
metadata:
  class: generative-workflow
  # The default for layers 1–3 (SPEC.md, "What a skill is" and "Artifact
  # layers"). `deterministic-artifact` is layer 4 only — a pinned, branded
  # template emitted verbatim — and the PR that introduces it states the reason.
  persona: finance | deal-maker | cs-renewals | marketing | all
  recipe-type: skill
  # The default for layers 1–3. `artifact` is layer 4 only; `scheduled-task`
  # for a skill that runs on a schedule.
  supervision: review-before-running | runs-automatically | asks-before-each-action
  risk: low | medium | high
  access: read-only | read-write
  connectors: <comma-separated connectors beyond Turnstile, or none>
  scopes: <comma-separated least-privilege Turnstile MCP scopes, or none>
  owner: <github login that resolves to a real account and a person who will maintain this>
  audience: public
  # Required (SPEC.md). `public` is the only valid value in this repo, and CI
  # enforces it.
  # surfaces: claude-ai, cowork, claude-code
  # Optional (SPEC.md, machine-readable "Runs on"). OMIT IT and the skill
  # supports every surface, which is almost always what you want. Declare it
  # only to exclude one: a skill that omits `claude-ai` is not packaged into a
  # .skill release asset, because that download could not work.
---

# skill-name

One paragraph: the question this skill answers, for whom, and what the answer
looks like in chat.

## What goes in, what comes out

**Inputs:** what the user provides, and what the skill reads from connectors. Say
"none" if the skill needs nothing to start.

**Outputs:** what a run produces — the answer in chat; for layers 3–4, the file or
the artifact. Name the filename pattern if it writes one.

## The question this answers

One sentence. Would you show a new customer this on the first or second call?
If not, it is not yet a skill (SPEC.md, "What a skill is").

## Prerequisites

- Turnstile MCP connected (ships with this plugin; OAuth on first use)
- Any other connectors this skill needs, named explicitly

## Instructions

1. If the request could return more than a session can hold ("tell me about all
   my invoices"), narrow it first with `AskUserQuestion`: which customers, which
   period, which status. At most four options plus free text.
2. Call the tools by their fully-qualified names (`Turnstile:list_turnstile_invoices`)
   at run time, on live data. Never bake in a snapshot, and never state what the
   MCP can or cannot do: the session's own tool list is the source of truth.
3. Present the answer in chat: the numbers, what they mean, and what to do next.
   Money is integer minor units, one currency per total; `currency` is on the
   line item, not the invoice.
4. If a write is involved: triage with `Turnstile:list_turnstile_invoices`
   (`expand: ["eligibleActions"]`, 25 per page), then for the one invoice you
   are about to act on read the gate fresh via `Turnstile:get_turnstile_invoice`,
   honor `allowed`, show `blockingReasons` verbatim, and confirm with the user
   before acting.

<!-- Layers 3–4 only: delete for a layer-1 skill (SPEC.md, "Artifact layers"). -->
5. Point at the pinned template in `references/` and instruct verbatim emission —
   populate the data, do not regenerate the structure.
6. Ask setup questions with explicit options; apply answers via a deterministic
   script in `scripts/`, not freehand edits.
7. Declare how the artifact refreshes at runtime (in-artifact MCP call /
   re-prompt / re-run the skill). This is the artifact's data refresh — a
   different thing from the skill's own freshness check below.
8. If the artifact calls MCP tools at runtime: the deploy script owns the tool
   list and generates BOTH the substituted tool-name map and the allowlist
   manifest from it; its input is a full tool name copied from the current
   session's tool list (server ids are session-variable and may be name-shaped —
   never validate them as UUID-only). SPEC.md, "Artifact MCP-tool binding".
<!-- End of the layers 3–4 block. -->

## Boundaries

- The writes this skill never makes without approval (issuing, sending, voiding,
  deleting), named one by one.
- If a tool is missing from the session or a call is refused, tell the user and
  stop. Never work around it inside Turnstile.
- Known limitations, stated plainly.

## Freshness check (non-blocking)

<!-- Optional since Skill Standard v0.26. Keep only if this skill is distributed
as a .skill upload; plugin installs update on their own. Delete otherwise. -->

At the start of a run, compare the frontmatter `version:` above to this skill's
newest published version: the latest release of `turnstileco/turnstile-plugin`
carries it as the asset `skill-name-v<version>.skill` (the release *tag* is the
plugin version, a different number). If a newer one exists, tell the user this
copy is stale and how to update — `/plugin marketplace update turnstile` in
Claude Code, or re-download the `.skill` bundle from the GitHub Release on
claude.ai — then proceed anyway. If the source is unreachable, skip silently.
