#!/usr/bin/env python3
"""Unit tests for validate_skill.py's audience <-> location enforcement.

Usage:
    python3 scripts/test_validate_skill.py

Runs as a blocking validate.yml step. Scope is deliberately the v0.19 rules —
`metadata.audience` required and matched to the plugin the skill lives in,
`ported-to` valid only with `audience: internal`, and the scaffold/tooling
exemptions — because those rules carry the internal/public split and a silent
regression there mis-labels what is allowed to reach a customer. The older
rules (schema values, layout, canonical section) are exercised incidentally by
the fully-conformant fixture. Since Skill Standard v0.26 the freshness check
is optional, and two tests pin that its absence warns without failing.
Dependency-free: stdlib only.
"""

import contextlib
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import validate_skill as vs  # noqa: E402

SCHEMA = json.loads(vs.SCHEMA_PATH.read_text(encoding="utf-8"))

SKILL_MD = """\
---
name: {name}
description: A test fixture skill that does one thing when the user asks for that one thing.
version: 0.1.0
metadata:
  class: generative-workflow
  persona: all
  recipe-type: skill
  supervision: review-before-running
  risk: low
  access: read-only
  connectors: none
  scopes: none
  owner: test-owner
{audience_lines}---

# {name}

A fixture skill for the validator's own tests.

## What goes in, what comes out

**Inputs:** none.

**Outputs:** a validation verdict.

## Freshness check (non-blocking)

Compare the frontmatter version: to the newest published version; warn and
proceed if stale, skip silently if unreachable.
"""


class AudienceLocationTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="validate-skill-test-"))
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)

    def write_skill(self, plugin, name, audience=None, extra_meta=""):
        """A fully conformant distributed skill, minus whatever the test omits."""
        skill_dir = self.root / "plugins" / plugin / "skills" / name
        skill_dir.mkdir(parents=True)
        audience_lines = ""
        if audience is not None:
            audience_lines += f"  audience: {audience}\n"
        if extra_meta:
            audience_lines += extra_meta
        (skill_dir / "SKILL.md").write_text(
            SKILL_MD.format(name=name, audience_lines=audience_lines),
            encoding="utf-8",
        )
        (skill_dir / "CHANGELOG.md").write_text(
            f"# Changelog — {name}\n\n## 0.1.0 — 2026-07-13\n\nFixture.\n",
            encoding="utf-8",
        )
        return skill_dir

    def problems(self, skill_dir):
        return vs.validate_distributed_skill(skill_dir, SCHEMA)

    # -- correct pairs pass -------------------------------------------------

    def test_internal_plugin_with_internal_audience_passes(self):
        d = self.write_skill("turnstile-internal", "fixture-skill", "internal")
        self.assertEqual(self.problems(d), [])

    def test_staging_plugin_with_public_preview_passes(self):
        d = self.write_skill("turnstile-public-staging", "fixture-skill", "public-preview")
        self.assertEqual(self.problems(d), [])

    def test_unknown_plugin_defaults_to_public(self):
        # The public repo's plugin is not in PLUGIN_AUDIENCES on purpose:
        # anything unmapped takes DEFAULT_AUDIENCE, so this file is identical
        # in both repos.
        d = self.write_skill("turnstile", "fixture-skill", "public")
        self.assertEqual(self.problems(d), [])

    # -- missing / mismatched audience fails --------------------------------

    def test_missing_audience_is_reported(self):
        d = self.write_skill("turnstile-internal", "fixture-skill", audience=None)
        self.assertTrue(
            any("audience: required field missing" in p for p in self.problems(d)),
            self.problems(d),
        )

    def test_wrong_location_internal_plugin(self):
        d = self.write_skill("turnstile-internal", "fixture-skill", "public-preview")
        self.assertTrue(
            any("must declare 'internal'" in p for p in self.problems(d)),
            self.problems(d),
        )

    def test_wrong_location_staging_plugin(self):
        d = self.write_skill("turnstile-public-staging", "fixture-skill", "internal")
        self.assertTrue(
            any("must declare 'public-preview'" in p for p in self.problems(d)),
            self.problems(d),
        )

    def test_wrong_location_default_public(self):
        d = self.write_skill("turnstile", "fixture-skill", "internal")
        self.assertTrue(
            any("must declare 'public'" in p for p in self.problems(d)),
            self.problems(d),
        )

    def test_invalid_audience_value_fails_the_enum(self):
        d = self.write_skill("turnstile-internal", "fixture-skill", "customers")
        self.assertTrue(
            any("metadata.audience" in p and "is not one of" in p
                for p in self.problems(d)),
            self.problems(d),
        )

    # -- ported-to pairing ---------------------------------------------------

    def test_ported_to_with_internal_audience_passes(self):
        d = self.write_skill(
            "turnstile-internal", "fixture-skill", "internal",
            extra_meta="  ported-to: https://github.com/turnstileco/turnstile-plugin/tree/main/plugins/turnstile/skills/fixture-skill\n",
        )
        self.assertEqual(self.problems(d), [])

    def test_ported_to_without_internal_audience_fails(self):
        d = self.write_skill(
            "turnstile-public-staging", "fixture-skill", "public-preview",
            extra_meta="  ported-to: https://github.com/turnstileco/turnstile-plugin/tree/main/plugins/turnstile/skills/fixture-skill\n",
        )
        self.assertTrue(
            any("only valid with audience: internal" in p for p in self.problems(d)),
            self.problems(d),
        )

    def test_ported_to_must_be_https(self):
        d = self.write_skill(
            "turnstile-internal", "fixture-skill", "internal",
            extra_meta="  ported-to: plugins/turnstile/skills/fixture-skill\n",
        )
        self.assertTrue(
            any("metadata.ported-to" in p and "does not match" in p
                for p in self.problems(d)),
            self.problems(d),
        )

    # -- freshness check is optional (Skill Standard v0.26) ------------------

    def test_missing_freshness_check_warns_but_passes(self):
        # Required v0.7–v0.25, optional since v0.26: organization-managed
        # plugin sync keeps installed copies current. Absence is a stdout
        # warning, never a problem.
        d = self.write_skill("turnstile", "fixture-skill", "public")
        md = d / "SKILL.md"
        text = md.read_text(encoding="utf-8")
        head, _, _ = text.partition("## Freshness check")
        md.write_text(head, encoding="utf-8")
        self.assertNotRegex(md.read_text(encoding="utf-8"), vs.FRESHNESS_RE)
        with contextlib.redirect_stdout(io.StringIO()) as out:
            problems = self.problems(d)
        self.assertEqual(problems, [])
        self.assertIn("no freshness check", out.getvalue())
        self.assertIn("optional since standard v0.26", out.getvalue())

    def test_present_freshness_check_is_silent(self):
        d = self.write_skill("turnstile", "fixture-skill", "public")
        with contextlib.redirect_stdout(io.StringIO()) as out:
            problems = self.problems(d)
        self.assertEqual(problems, [])
        self.assertNotIn("no freshness check", out.getvalue())

    # -- exemptions -----------------------------------------------------------

    def test_scaffold_lane_is_exempt(self):
        # The real template: placeholder metadata values (audience included)
        # are unchecked, and template/ is not under plugins/, so no
        # location check fires. This is the CI --scaffold lane in miniature.
        template = vs.REPO_ROOT / "template" / "skill-name"
        problems = vs.validate_distributed_skill(template, vs.scaffold_schema(SCHEMA))
        self.assertEqual(problems, [])

    def test_tooling_lane_is_exempt(self):
        # A tooling skill has no metadata block at all — audience never applies.
        skill_dir = self.root / ".claude" / "skills" / "turnstile-skill-fixture"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            "---\n"
            "name: turnstile-skill-fixture\n"
            "description: A tooling-lane fixture for the validator's own tests.\n"
            "---\n\n# turnstile-skill-fixture\n\nA fixture.\n",
            encoding="utf-8",
        )
        self.assertEqual(vs.validate_tooling_skill(skill_dir), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
