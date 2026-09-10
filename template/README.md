# Skill template

Copy `skill-name/` into `plugins/<plugin>/skills/<your-skill-name>/`, rename
the folder, and fill in the skeletons. The folder name and the `SKILL.md`
frontmatter `name` must match — CI enforces it — and the name says which
question the skill answers ([SPEC.md](../SPEC.md)).

```
skill-name/
├── SKILL.md        # source of truth: frontmatter + lean instructions
├── CHANGELOG.md    # seeded at 0.1.0; one dated entry per version bump
├── references/     # background docs; pinned templates (layers 3–4)
├── scripts/        # deterministic helpers (layers 3–4 customize scripts)
└── assets/         # logos, images an artifact needs (layer 4)
```

Ground rules ([SPEC.md](../SPEC.md) has the full set):

- **One question, answered in chat first.** A skill answers one question; a
  body that answers seven is seven skills. Version 1 is a chat answer with
  no artifact (layer 1). State the question under `## The question this
  answers`, and ask whether you would show it to a new customer on the first
  or second call. Artifacts are later PRs on the same skill.
- **Live data, and a `## Boundaries` section.** Call the MCP at run time; never
  bake in a snapshot, never assert what the MCP can or cannot do. The
  `## Boundaries` section is required: the writes never made without
  approval, and the rule that a missing tool or a refused call is told to the
  user and stopped on — never worked around inside Turnstile. A constraint
  the MCP imposes is feedback to Turnstile, not a paragraph in the body.
- **Artifact rules apply from layer 3 up.** The template's `Instructions`
  carry them in a marked block: delete it for a layer-1 skill. From layer 3:
  reference the artifact, do not embed it (a pinned HTML template lives in
  `references/`; `SKILL.md` instructs verbatim emission); if the artifact
  calls MCP tools at runtime, the deploy script generates the tool-name map and
  the allowlist manifest from one list and takes a full observed tool name as
  input — never a UUID-only id pattern (server ids are session-variable and
  may be name-shaped). `class: deterministic-artifact` and
  `recipe-type: artifact` are layer 4 only, with a stated reason.
- **Lean SKILL.md** — under 500 lines; progressive disclosure via the
  ride-along folders.
- **No secrets, no account-specific values, no hardcoded server IDs.**
  Parameterize anything environment-specific.
- **Declare your audience.** `metadata.audience` is required, and `public` is
  the only valid value in this repo — CI enforces the pairing (SPEC.md).
- **`owner` is a GitHub login that resolves** to a real account and a person
  who will maintain the skill — not a first name. The reviewer checks it
  against GitHub.
- **Version from day one:** start at `0.1.0`; every later change bumps
  semver and adds a CHANGELOG entry (PATCH = fix, MINOR = new
  backward-compatible capability, MAJOR = breaking). Full rules:
  [SPEC.md](../SPEC.md).
- **Declare inputs and outputs in the body**, not the frontmatter — under the
  canonical `## What goes in, what comes out` heading, verbatim (SPEC.md).
  CI requires it. Write it, and the lede (the prose under the `#` heading),
  in plain language for a human reader, not just for Claude: the
  GitHub-rendered `SKILL.md` is this repo's provider-agnostic view of the
  skill.
- **The freshness check is optional** (SPEC.md, since Skill Standard v0.26).
  Plugin installs update on their own. Keep the short section only if the
  skill is distributed as a `.skill` upload; otherwise delete it.
- **No committed preview screenshots** — the artifact is its own preview.
- **No committed recipe file.** The provider-agnostic recipe is a *rendered
  view* of `SKILL.md` — here, the GitHub render of `SKILL.md` itself. Nothing
  to hand-maintain, nothing to drift.

Validate locally before opening a PR:

```
python3 scripts/package_skill.py plugins/<plugin>/skills/<your-skill-name>/ --check
python3 scripts/validate_skill.py plugins/<plugin>/skills/<your-skill-name>/
```

This scaffold is itself validated in CI (`validate_skill.py --scaffold`), so it
cannot drift behind the SPEC.
