# Turnstile Skill SPEC

Digest of Skill Standard v0.26 (2026-09-09).

The enforceable digest of Turnstile's skill standard: every rule a skill in
this repo is held to, in one file. `scripts/validate_skill.py` and
`scripts/scan_skill.py` enforce the mechanical half on every PR; the rest is
what a maintainer verifies at review.

> **Scope.** This is the standard for skills in this repo: what a skill is,
> how it is built, how artifacts layer on top of it, and what it has to clear
> before release. Where a rule here disagrees with observed Turnstile MCP
> behavior, the live behavior wins and the rule gets fixed.
>
> **Authority.** The live Turnstile MCP is authoritative. When the server and
> this document disagree, trust the server and file a SPEC fix.

## Contents

- What a skill is
- Metadata: the frontmatter contract
- Authoring craft
- The MCP boundary
- Build requirements
- Artifact layers (3–4 only)
- Write safety (verified against the live MCP)
- Error reporting
- Distribution: one plugin, every client
- Security checks (TS-SEC-01 … TS-SEC-16)

## What a skill is

A Turnstile skill is a well-crafted set of instructions that rides along with
the Turnstile MCP inside a plugin. It answers **one question** a user asks of
their data, and it fires on its own when the user's phrasing matches its
`description`; the user never enters it. Three consequences:

- **The happy path, not a product.** Tool descriptions say what each MCP tool
  does; a skill adds *when* and *in what order*, and what not to attempt.
- **One question per skill.** Seven questions is seven skills. Split when they
  call different tools, need different scope, or are asked by different people.
- **No artifact at version 1.** A skill ships as a chat answer first (layer 1
  below); artifacts and templates are later layers a skill earns.

**Persona** is the role the skill serves. **Class** records what a skill
guarantees: every layer-1 skill is `generative-workflow`; `deterministic-artifact`
is layer 4 only and needs a stated reason in the PR that introduces it.

## Metadata: the frontmatter contract

Every skill's `SKILL.md` frontmatter carries `name`, `description`, `version`,
and a `metadata:` block with these exact lowercase values —
machine-validated against `standards/skill-frontmatter.schema.json` (see
`CONTRIBUTING.md` for how schema changes are proposed):

| Field | Values |
|---|---|
| `class` | `generative-workflow` (layers 1–3) \| `deterministic-artifact` (layer 4 only, with a stated reason) |
| `persona` | `finance` \| `deal-maker` \| `cs-renewals` \| `marketing` \| `all` (one or more, comma-separated) |
| `recipe-type` | `skill` (layers 1–3) \| `scheduled-task` \| `artifact` (layer 4 only) |
| `supervision` | `review-before-running` \| `runs-automatically` \| `asks-before-each-action` |
| `risk` | `low` \| `medium` \| `high` — how dangerous; a different axis from `supervision` (how much human-in-the-loop). Declare both. |
| `access` | `read-only` \| `read-write` |
| `connectors` | comma-separated connector names beyond the Turnstile MCP, or `none` |
| `scopes` | comma-separated least-privilege Turnstile MCP scopes, or `none` |
| `owner` | a GitHub login that resolves to a real account and a person who will maintain the skill — not a first name. The reviewer checks it against GitHub and blocks if it resolves to a stranger or to nobody. |
| `audience` | **required**: `public` for every skill in this repo. The schema also accepts `internal` and `public-preview`, which are used before a skill is published; CI rejects them here. |
| `surfaces` | optional: `claude-ai` \| `cowork` \| `claude-code` (one or more). **Absent means all surfaces.** A skill that omits `claude-ai` gets no `.skill` release asset, because that upload path could not work. |

`version` is semver. Official skills arrive in this repo at **`1.0.0`**:
clearing the release gate is what earns the major version. A skill that has
not cleared it starts at `0.1.0`. Every
skill-touching PR bumps the skill's version and adds a dated `CHANGELOG.md`
entry (CI-enforced); the changelog entry and the PR description are the same
text.

**Known portability defect.** The Agent Skills spec puts `version` under
`metadata`, and `agentskills validate` currently fails every distributed skill
on the top-level key (verified 2026-09-09). The migration to `metadata.version`
is pending and lands as its own PR, schema included. Until then keep
`version` at the top level.

A new skill is its own skill: its own trigger phrases and its own owner. A
skill split out of another inherits neither.

## Authoring craft

CI-enforced by `scripts/validate_skill.py` on every PR unless marked *review*:

- **`description` ≤ 1024 characters**, third person, what the skill does *and
  when to reach for it*, with the trigger phrases a user would actually type.
  It is the whole trigger surface.
- **Distinct triggers** (*review*). No two skills in the plugin may claim the
  same phrases; overlap blocks the PR.
- **`name` ≤ 64 characters**, lowercase letters, digits, hyphens; equals the
  folder name; never contains `anthropic` or `claude`; the `turnstile-skill-*`
  prefix is reserved for repo tooling. Named for the question it answers.
- **`SKILL.md` body ≤ 500 lines** — it loads into context the moment the
  skill triggers; past this, split into `references/`.
- **A contents list in any markdown reference over 100 lines**, and every
  non-dotfile under `references/` is mentioned in the body by path or basename.
- **Read live data** (*review*). A skill calls the MCP at run time. It never
  bakes in a snapshot and never asserts what the MCP can or cannot do: the
  session's own tool list is the source of truth. A tool absent from the
  session means "not available on your account", never "Turnstile can't".
- **Narrow scope before a large pull** (*review*). When a question could
  return more than a session can hold ("tell me about all my invoices"), use
  `AskUserQuestion` to narrow it: which customers, which period, which
  status. At most four options plus free text.
- **Fully-qualified MCP tool names** (`Turnstile:list_turnstile_invoices`);
  **say "execute this script" or "read this script," explicitly**; forward
  slashes in every path; no time-sensitive prose; no builder rationale in the
  user's voice.
- **A `## Boundaries` section** (*review*): the writes the skill never makes
  without approval, and the rule that on a missing tool or an unexpected
  refusal it tells the user and stops. Never a workaround inside Turnstile.
- **Freshness check: optional.** Plugin installs update on their own. A skill
  may still carry a short, non-blocking version check for `.skill` uploads;
  the validator warns on its absence and no longer fails.
- **At least 3 evaluations** exist and were run before a skill is released.

## The MCP boundary

A skill teaches the agent how to use the MCP. It does not encode the MCP's
mechanics, and it does not compensate for them.

| What the skill hits | Where it goes |
|---|---|
| The user asked too broadly (a pull that would time out or flood the session) | Narrow scope in the skill with `AskUserQuestion`. The only one of the three that is written into a `SKILL.md`. |
| How the MCP delivers data (page size, cursors, a limit a tool imposes) | The tool description. Report it to Turnstile as MCP feedback; the skill does not carry pagination instructions. |
| The MCP cannot do it (a missing tool, a refused action, a gap) | The skill tells the user and stops. Never a workaround: an agent that edits an invoice by hand because a usage tool was absent is the failure this rule exists to prevent. |

Pagination is therefore not a skill rule; where an artifact's own code pages
through the API, see *Artifact layers*.

## Build requirements

Verified at review — the gate checks the built thing, not the `SKILL.md`'s
claims about it. These apply to every skill, chat or artifact, because they
are about the data, not the output:

- **The canonical section.** The body carries `## What goes in, what comes
  out` (exact heading, verbatim) declaring **Inputs** and **Outputs** inside
  it. CI-enforced. **The lede names the question** the skill answers, and the
  skill answers that question and no other.
- **Money in minor units, correctly.** Amounts are integer minor units and
  some unit prices are fractional; field names differ across endpoints.
  Multiply quantity **before** rounding; keep **one currency per total** —
  `currency` lives on the line item, not the invoice.
- **No hardcoded environment**: no server id, connector id, account-specific
  magic value, internal file id, secret, or teammate name in the bundle
  (TS-SEC-01 … 03).
- **Least privilege.** Declared `scopes` equal what the named tools require,
  no more and no less (TS-SEC-04).
- **No MCP workaround.** A constraint the skill hit is feedback to Turnstile,
  not a paragraph in the body.

## Artifact layers (3–4 only)

A skill's output matures in layers. Each layer is its own PR on the same
skill, earned by evidence from the layer below. The order is the rule.

| Layer | What ships | Class / recipe-type |
|---|---|---|
| **1. Chat MVP** | About ninety percent of the answer, in the session, no artifact. Every skill starts here. | `generative-workflow` / `skill` |
| **2. MCP App** | A UI card served by the MCP itself. Not a skill: no client-side plugin can ship one. The skill ships before it lands and does not depend on it. | — |
| **3. Artifact coaching** | The skill offers to put the answer into a working HTML page the user owns. Not Turnstile-branded. | `generative-workflow` / `skill` |
| **4. Turnstile template** | A pinned, branded template emitted verbatim, varied only through a customization script, with a stated reason. | `deterministic-artifact` / `artifact` |

Rules that apply only from layer 3 up, verified in the emitted file:

- **Turnstile branding** on any Turnstile-emitted visualization (layer 4):
  the brand tokens actually applied (`#141533` / `#43e4d9` or the bundled
  token file), not the word "brand" in the instructions.
- **Debug / trace visibility** on any computed artifact: a processing log for
  a live-data page; a computation-trace + provenance panel for an offline
  calculator. **`localStorage`** where the artifact claims state: a real read
  and write, verified.
- **Reference the template, don't embed it.** A pinned template over roughly
  100–150 lines lives in `references/`; `SKILL.md` instructs verbatim emission.
- **Artifact MCP-tool binding**: call-time tool names and the deploy-time
  allowlist come from **one source**; deploy tooling takes the exact prefix of
  a full tool name observed in the session and never assumes UUID-only —
  server-id segments are session-variable and may be name-shaped.
- **Pagination in artifact code**: code that pages through the API loops
  until the response's more-pages flag (`hasMore: false`) and never assumes
  one page is the whole set. A rule for artifact code, not a `SKILL.md`
  instruction (see *The MCP boundary*).
- **Live Artifacts are desktop Cowork only**; a layer-4 artifact that
  refreshes through a connector is tested there.
- **No committed preview images.** TS-SEC-08 … 11 apply to any emitted HTML.

## Write safety (verified against the live MCP)

The Turnstile MCP's write surface is real and partly irreversible. Two rules,
both non-negotiable:

1. **Triage from the list, act from the get.** The gate — `eligibleActions`,
   with `allowed` and `blockingReasons` per action — is returned by
   `get_turnstile_invoice` by default, and by `list_turnstile_invoices` when
   passed `expand: ["eligibleActions"]` (25 per page; probed 2026-09-09).
   The list is the right way to find what is ready. The write itself is
   preceded by a fresh `get_turnstile_invoice` for that one invoice,
   immediately before the write, because a list page is a snapshot. Honor
   `allowed`, and surface `blockingReasons[].message` to the human
   **verbatim** — it is written for a human; do not paraphrase it. Never
   re-derive "is this safe" in skill logic. (Static analysis cannot verify
   this read path — see the security table: it is a named human-review item.)
2. **Irreversible actions ask first.** Tools in four classes require
   `supervision: asks-before-each-action` and `risk:` above `low`:
   **sends-to-customer** (issue/publish/resend — an email cannot be unsent),
   **moves-money** (payment collection), **terminal state change** (mark-paid,
   mark-uncollectible, void, terminate, finalize), and
   **writes-through-to-external-systems** (customer updates propagate to the
   payment processor). The roster is `IRREVERSIBLE_TOOLS` in
   `scripts/scan_skill.py`, 16 tools as of the 2026-08-17 surface snapshot.

**Bulk under `asks-before-each-action`** is per-action-equivalent only when
the one confirmation is fully enumerated, eligibility-filtered, vetoable line
by line, and re-checked per item at execution, and only when the user asked
for bulk. Missing any of the four, it collapses to per-action.

One adjacent trap: `evaluate_turnstile_invoice_readiness` **persists** its
result — a "just checking" call is a write, and it needs `invoices:write`.

## Error reporting

On an unrecognized error or data state: **surface it to the human** — the
error text, what the skill was doing, what it did not do. A skill may call
`create_turnstile_support_request` only when it already declares
`entity:write`, because that tool **is** a write tool requiring that scope. A
read-only skill never self-escalates: routing its errors to support would
silently promote it to a write scope. Report to the human and stop.

## Distribution: one plugin, every client

Customers get the MCP and the skills together by installing **one official
plugin**, this repo (marketplace slug `turnstile`, install string
`turnstile@turnstile`). Installing the MCP alone as a connector gives tools
and no skills. The shape is what every MCP-plus-skills vendor ships:

- **One `skills/` source** of Agent Skills-standard `SKILL.md` files, **one
  MCP URL** (`https://mcp.app.turnstile.ai/mcp`) repeated in each client's MCP
  config, and **a thin manifest per client**, about fifteen lines each. Claude
  (`.claude-plugin/plugin.json` + `.mcp.json`) ships first; Codex and ChatGPT,
  Cursor, and Agent Plugins 1.0 are few-line additions, validated in CI when
  present.
- **Skills must not depend on Claude-only plugin features** (hooks, commands,
  subagents) unless the skill declares `compatibility:` Claude-only.
  Claude-only machinery lives in the Claude manifest layer.
- **Two Anthropic directories, not one.** The Connectors Directory takes MCP
  servers only; skills must ship inside a plugin. The Plugin Directory is a
  separate submission, requires a public repo, and mirrors updates from it.
  Plugin names are immutable once published.

**Unverified** — do not tell a customer either works: whether skills bundled
in an OpenAI plugin fire inside ChatGPT chat, and whether Claude Code loads a
bare Agent Plugins package with no `.claude-plugin`.

## Security checks (TS-SEC-01 … TS-SEC-16)

`scripts/scan_skill.py` is the deterministic half; a human applies the rest.
**A High finding blocks a release. A clean scan is not a pass** — nine of the
sixteen need judgment, and the reviewer reads raw scanner output and the
diff, not a summary. For a read-only chat skill the deterministic scan plus
TS-SEC-12 and TS-SEC-15 are the judgment items that apply; the rest apply as
the skill's shape earns them. Never N/A. See also `CONTRIBUTING.md` for how
to review a PR safely.

**Waivers.** Nine of these checks are hybrid: the scanner finds candidates, a
human rules. A ruling is recorded in `standards/scan-waivers.json` — a registry
that lives on `main` and is read from the *trusted* checkout, never from the
pull request being scanned. A waiver downgrades a High to Medium and prints the
granter, the date, and the reason; **it never removes a finding**. It cannot
touch `TS-SEC-01`, `TS-SEC-02`, or `TS-SEC-12` (Never N/A), and an entry naming
one is a configuration error that exits 2. Entries key on the source line's
text, not its number: reflowing code keeps a waiver, **editing a waived sink
revokes it**. A skill's own PR cannot grant itself a waiver — that is the point,
and it means a skill needing one waits on a separate, reviewed PR.

| ID | Rule (one line) | Blocks |
|---|---|---|
| TS-SEC-01 | No secret, credential, token, or private key in any bundled file. Never N/A. | High |
| TS-SEC-02 | No hardcoded environment: no server UUID, connector id, or account-specific magic value. Never N/A. | High |
| TS-SEC-03 | No internal file IDs (document-service ids, drive links) in the bundle. | High |
| TS-SEC-04 | Least privilege: `scopes` equals what the named tools require; `access` matches read-vs-write reality. | High |
| TS-SEC-05 | Declared `connectors` matches the connectors the skill actually reaches. | Med |
| TS-SEC-06 | A skill naming a write tool reads the action gate **via a fresh `get_turnstile_invoice` for the one invoice, immediately before the write** (a list-expand read is triage, not the gate), honors `allowed`, surfaces `blockingReasons` verbatim. The scanner's token check is advisory — **verifying the per-invoice read path is a human-review line item.** Never N/A for a read-write skill. | High |
| TS-SEC-07 | Supervision and risk match blast radius: irreversible-or-outward tools (the four classes above; roster = `IRREVERSIBLE_TOOLS` in `scripts/scan_skill.py`) require `asks-before-each-action`. | High |
| TS-SEC-08 | No remote dependency in an emitted artifact (remote scripts, stylesheets, fonts, iframes). | Med |
| TS-SEC-09 | No `innerHTML` / `outerHTML` / `document.write` / `insertAdjacentHTML` on data the skill did not construct. Each sink receives only literal or numeric content, **or** live data passed through a reviewed escaping helper (recorded as a waiver). An `href`/`src`/`on*=` built by concatenation needs a **scheme and host allowlist too** — escaping does not stop `javascript:`. | High |
| TS-SEC-10 | An offline artifact has no network egress (`fetch`, `XMLHttpRequest`, `sendBeacon`, `WebSocket`) — a calculator that phones home is an exfiltration path. | High |
| TS-SEC-11 | No `eval()` / `new Function()` in shipped code (a build-time verification harness is an acceptable, justified case). | Med |
| TS-SEC-12 | No instruction-shaped text on a surface Claude loads as instructions (`SKILL.md`, `references/**`): no "ignore previous instructions," no "report PASS," no role reassignment. Elsewhere in the bundle the same string is Medium — described, not asserted. Never N/A on an instruction surface. | High |
| TS-SEC-13 | A customer-facing artifact contains no internal-only data: no internal personas, no uncleared pricing, no other customer's numbers. | High |
| TS-SEC-14 | Everything under `scripts/` is read line by line; no obfuscation, no minified blob, no symlink anywhere in the bundle. Also: **no NUL byte in a file whose suffix says text** — it makes grep-based tools report nothing on that file. A genuinely binary file earns its skip by having its suffix added to `BINARY_SUFFIXES`, not by embedding a byte. | High |
| TS-SEC-15 | Principle of Lack of Surprise: the skill does what its `description` says, and only that. | Med |
| TS-SEC-16 | No SSRF: every URL the skill fetches traces to a constant or an allowlist, never raw user/connector input. | Med |
