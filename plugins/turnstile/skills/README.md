# Skills

One folder per skill, scaffolded from [`/template`](../../../template/):

```
skills/<skill-name>/
├── SKILL.md        # source of truth (frontmatter + instructions)
├── CHANGELOG.md    # dated entries, one per version bump
└── references/  scripts/  assets/   # ride-along files as needed
```

`SKILL.md` is the single source of truth. What the skill does, what it needs,
and what your assistant will do with it are all readable in the
GitHub-rendered `SKILL.md` itself; there is no separate recipe file to
maintain.

Rules of the road (see [SPEC.md](../../../SPEC.md) for the full set):

- `SKILL.md` frontmatter carries `name`, `description`, and a semver
  `version` — CI rejects a skill without them.
- A PR that touches a skill must also touch that skill's `CHANGELOG.md`.
- Reference the artifact, don't embed it: pinned templates live in the
  skill's own folder and `SKILL.md` points at them.
