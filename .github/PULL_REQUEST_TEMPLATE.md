## What changed

<!-- Write this once and paste it into the CHANGELOG.md of any skill you
touched — the PR description and the changelog entry are the same text. -->

## Version bumps

- [ ] Each touched skill: semver bumped in SKILL.md frontmatter + a dated
      CHANGELOG.md entry (CI enforces the changelog)
- [ ] Breaking change → MAJOR bump, called out explicitly above

## Checks

- [ ] `python3 scripts/package_skill.py plugins/<plugin>/skills/<name>/ --check` passes locally
- [ ] `python3 scripts/validate_skill.py plugins/<plugin>/skills/<name>/` passes locally
- [ ] No secrets, account-specific values, or hardcoded server IDs
