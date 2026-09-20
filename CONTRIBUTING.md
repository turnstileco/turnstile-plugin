# Contributing

## We aren't open for pull requests yet

The skill library is still being built out, and the review process for outside
skills isn't settled. A pull request opened here today will be closed, and
that's a waste of your time — so please don't start one.

That will change. Until it does, feedback is the contribution we want.

## Tell us a skill got something wrong

[Open a bug report.](../../issues/new?template=bug-report.yml) Three things
make the difference between a report we can act on and one we can't:

1. **Which surface** — Claude Code, claude.ai, desktop, Cowork.
2. **Which model.** Skills behave differently across models, and "it ignored
   the confirmation step" usually turns out to be model-specific.
3. **What the assistant actually did** — which tools it called, in what order,
   if you can see them.

Please keep customer data, invoice contents, and anything else out of the
issue. Describe the shape of the problem instead.

## Ask for a skill that doesn't exist

[Request one.](../../issues/new?template=skill-request.yml) A skill answers
one question, so the useful form of the request is the question you'd actually
ask, plus how you answer it today and what's slow about that.

## What a skill is held to

[SPEC.md](SPEC.md) is the standard — what a skill is, how it's built, and what
it has to clear before release. CI enforces the mechanical half of it
(`validate` and `scan`) on every pull request. It's public because the rules a
skill is judged by should be readable by the people the skill runs for.

---

## Maintainers

A pull request is untrusted content until it merges, and Claude Code loads
`.claude/skills/` and `.claude/agents/` from the working directory. So:

- **Never run `claude` inside a checkout of an untrusted PR.** Checking out
  someone else's branch into a workspace you have already trusted runs *their*
  project skills and subagents in your session. A PR that touches anything
  under `/.claude/**` is asking for code execution on a reviewer's machine.
- Read the diff with `gh pr diff <n>` (or on github.com), not from a local
  checkout with Claude open.
- To run tooling against PR content, use
  `python3 scripts/review_pr_security.py <pr>`: it runs the scanner from a
  **trusted** checkout of `origin/main` and treats the PR's files as data.
  Never `python3 <pr-checkout>/scripts/...` — a PR can edit the very script
  that is supposed to check it.
- Scrutinize any diff that widens a subagent's `tools:` list. `Read, Grep,
  Glob` is a review subagent; `Bash` is a shell. CI (`security-scan.yml`)
  flags this, from the base branch so a PR cannot disarm it.

`main` is protected: a pull request, an approving review from a code owner
(`.github/CODEOWNERS` names the maintainer team), and green `validate` and
`scan` checks.

Every skill-touching PR bumps that skill's version in `SKILL.md` frontmatter
and adds a dated `CHANGELOG.md` entry — CI enforces the changelog. Write the
changelog entry and the PR description as the same text. **The plugin version
bumps in the same PR that changes its content**, by the highest-severity change
among its skills. Organization-managed plugin distribution syncs when a pull
request carrying a plugin version bump merges, so a content change that lands
without one can reach `main` and never reach anyone who installed the plugin.

`standards/skill-frontmatter.schema.json` is maintained by Turnstile; schema
changes ride along with the skill that needs them.
