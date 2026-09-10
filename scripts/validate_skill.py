#!/usr/bin/env python3
"""Validate skill folders against SPEC.md's frontmatter contract.

Usage:
    python3 scripts/validate_skill.py plugins/<plugin>/skills/<name>/ [more dirs...]
    python3 scripts/validate_skill.py plugins/*/skills/*/
    python3 scripts/validate_skill.py --scaffold template/skill-name/
    python3 scripts/validate_skill.py --tooling .claude/skills/*/

Two lanes, because a skills repo can hold two kinds of skill (SPEC.md).

DISTRIBUTED skills (`plugins/*/skills/*/`) are governed by the whole SPEC.
Enforces standards/skill-frontmatter.schema.json (the machine-readable form of
SPEC.md's metadata table) plus the layout rules the schema can't express:

  - SKILL.md frontmatter parses, including the nested `metadata:` block
    (package_skill.py's flat parser never sees the indented keys; this one does)
  - name/description/version present; version semver; name == folder name
  - metadata block complete with canonical values (class, persona, recipe-type,
    supervision, risk, access, connectors, scopes, owner, audience)
  - persona/connectors/scopes parse as comma-separated lists (`none` legal for
    connectors/scopes)
  - `audience` matches location (SPEC.md): every skill in this repo's plugin
    declares `public`. `internal` and `public-preview` are the values used
    before a skill is published, and the optional `ported-to` marker is valid
    only with `audience: internal`; neither appears here. The scaffold and
    tooling lanes are exempt.
    `scripts/test_validate_skill.py` exercises these pairings and runs as a
    validate.yml step.
  - `references/` (plural) — the singular `reference/` layout is off-spec
  - CHANGELOG.md rides along
  - the canonical `## What goes in, what comes out` section exists, and declares
    both inputs and outputs inside it (SPEC.md)
  - a non-blocking freshness check is OPTIONAL since Skill Standard v0.26
    (SPEC.md, Build requirements): organization-managed plugin sync keeps
    installed copies current, so its absence warns on stdout and no longer
    fails
  - the `turnstile-skill-*` name prefix is reserved for tooling skills and may
    not be used by anything under `plugins/` (SPEC.md)

TOOLING skills (`--tooling`, for `.claude/skills/*/`) are repo tooling, not a
distributed product: no metadata block, no version, no CHANGELOG, no freshness
check, never packaged into a `.skill`. They are held to the *craft* rules only.
This is not a thin flag over the distributed lane — that lane unconditionally
demands a metadata block, a version, a CHANGELOG and the canonical section,
none of which a tooling skill has (and it warns on a missing freshness check,
which a tooling skill never carries either). The craft rules both lanes share
live in the check_* helpers below.

AUTHORING CRAFT (SPEC.md) — enforced in both lanes:

  - `description` <= 1024 chars (the Agent Skills cap; Claude Code's listing
    truncates description + when_to_use at 1,536, so 1024 is the tighter bound)
  - `name` <= 64 chars, no `anthropic` / `claude` in it
  - SKILL.md body <= 500 lines
  - a contents list in any `references/**/*.md` over 100 lines — markdown only,
    since a table of contents in a pinned HTML artifact is absurd
  - reference reachability: every non-dotfile under `references/` is mentioned
    somewhere in SKILL.md's body, by basename or skill-relative path

This module also owns the SKILL.md body extractors (`extract_lede`,
`extract_section`). `CANONICAL_SECTION`, `declared_surfaces`, `extract_lede`,
`extract_section`, `normalize`, `parse_frontmatter` and `strip_frontmatter`
are a stable import contract: no renames, no signature changes, no import-time
side effects, no non-stdlib imports. `package_skill.py` imports from it.

`--scaffold` validates `template/skill-name/` itself: every rule above applies
except the metadata *values*, which are the scaffold's `a | b | c` placeholders.
The keys must still all be there. Without this the template silently drifts
behind the standard, which is exactly how it shipped without an inputs/outputs
section (and, while one was required, without a freshness check).

Reports every problem, never edits. Exit 0 = all pass. Dirs without a SKILL.md
are skipped. Dependency-free: stdlib only.
"""

import json
import re
import sys
from pathlib import Path

# --------------------------------------------------------------- constants
# Repo-specific constants and doc references live HERE, at the top. Keep
# divergences confined to this block: everything below it is meant to stay
# portable, so a fix here is a mechanical port anywhere else this validator
# runs.

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = REPO_ROOT / "standards" / "skill-frontmatter.schema.json"

# The document problem messages cite.
STANDARD_REF = "SPEC.md"
PORT_REF = "SPEC.md"

# audience <-> location (SPEC.md): a distributed skill's metadata.audience
# must match the plugin it lives in. Plugins not named here take the default,
# which is exactly right for this repo's plugin.
PLUGIN_AUDIENCES = {
    "turnstile-internal": "internal",
    "turnstile-public-staging": "public-preview",
}
DEFAULT_AUDIENCE = "public"
# ------------------------------------------------------------ end constants

LIST_FIELDS = {"persona", "connectors", "scopes", "surfaces"}  # comma-separated
NONE_OK = {"connectors", "scopes"}  # 'none' is a legal single value

# Runtime surfaces (SPEC.md). `surfaces` is optional and ABSENT MEANS ALL:
# every skill written before the key existed supports every surface, so adding
# it to LIST_FIELDS cannot change what an older release means — normalize()
# only touches `LIST_FIELDS & set(meta)`, and an absent key is skipped.
SURFACES = ("claude-ai", "cowork", "claude-code")

INPUTS_RE = re.compile(r"(?im)^(?:#{1,6}\s.*\binputs?\b|(?:[-*]\s*)?\*\*inputs?\b)")
OUTPUTS_RE = re.compile(r"(?im)^(?:#{1,6}\s.*\boutputs?\b|(?:[-*]\s*)?\*\*outputs?\b)")
FRESHNESS_RE = re.compile(r"(?i)\bfreshness check\b|\bversion check\b")

CANONICAL_SECTION = "What goes in, what comes out"

FENCE_RE = re.compile(r"^\s*(?:```|~~~)")
HEADING_RE = re.compile(r"^(#{1,6})\s+(\S.*)$")
FRONTMATTER_RE = re.compile(r"\A---\s*\n.*?\n---\s*\n", re.DOTALL)

# Authoring craft (SPEC.md). The description cap is the Agent Skills
# spec's 1024, not Claude Code's 1,536 listing truncation — take the tighter one.
MAX_NAME_CHARS = 64
MAX_DESCRIPTION_CHARS = 1024
MAX_BODY_LINES = 500
TOC_REQUIRED_OVER_LINES = 100

# A skill name may not carry the vendor's name. Anthropic's own rule.
RESERVED_NAME_WORDS = ("anthropic", "claude")

# `turnstile-skill-*` names the skill library's own tooling: Tier 2, Claude Code
# only, never customer-facing, never packaged. A skill that does a job is named
# for the job (a skill that builds a calculator is named for the calculator).
TOOLING_NAME_PREFIX = "turnstile-skill-"

# A contents list is a heading titled "Contents" / "Table of contents" followed
# by at least two list items. Loose on purpose: this is a navigation aid for a
# partial reader, not a schema.
TOC_HEADING_RE = re.compile(r"(?i)^(?:table of )?contents$")
LIST_ITEM_RE = re.compile(r"^\s*[-*+]\s+\S")

# Frontmatter a tooling skill may carry. `disable-model-invocation` keeps a
# skill out of `available_skills` so it never collides with an upstream skill's
# deliberately pushy description; `allowed-tools` restricts it.
TOOLING_FRONTMATTER_KEYS = {
    "name",
    "description",
    "disable-model-invocation",
    "allowed-tools",
}
# Distribution-only keys. Their presence in a tooling skill means someone copied
# a Tier 1 skill and did not read the SPEC.
TOOLING_FORBIDDEN_KEYS = ("metadata", "version")


def strip_frontmatter(text: str) -> str:
    """The SKILL.md body: everything after the closing `---`, or the whole text
    when there is no frontmatter block."""
    m = FRONTMATTER_RE.match(text)
    return text[m.end():] if m else text


def headings(lines):
    """(index, level, title) for every ATX heading outside a fenced code block.

    Fence-aware on purpose: a SKILL.md can carry a ```css block, and a CSS
    comment or a `#141533` hex color at the start of a line must never be read
    as a heading boundary.
    """
    found, in_fence = [], False
    for i, line in enumerate(lines):
        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = HEADING_RE.match(line)
        if m:
            found.append((i, len(m.group(1)), m.group(2).strip()))
    return found


def extract_lede(body: str) -> str:
    """Prose between the H1 and the next heading of any level.

    `""` when there is no H1, or when a heading follows it immediately.
    """
    lines = body.splitlines()
    heads = headings(lines)
    h1 = next((h for h in heads if h[1] == 1), None)
    if h1 is None:
        return ""
    end = next((idx for idx, _, _ in heads if idx > h1[0]), len(lines))
    return "\n".join(lines[h1[0] + 1:end]).strip()


def extract_section(body: str, heading: str):
    """Body of the `## <heading>` section, heading line excluded, stopping at
    the next heading of the same or higher level.

    Returns None when no level-2 heading matches verbatim, `""` when the section
    exists but is empty. A renderer treats both as "emit nothing"; the
    validator distinguishes them.
    """
    lines = body.splitlines()
    heads = headings(lines)
    for pos, (idx, level, title) in enumerate(heads):
        if level == 2 and title == heading:
            end = next(
                (i for i, lv, _ in heads[pos + 1:] if lv <= 2), len(lines)
            )
            return "\n".join(lines[idx + 1:end]).strip()
    return None


def parse_frontmatter(text: str):
    """Parse the SKILL.md YAML frontmatter, including one nested block level.

    Returns (fields, errors). Handles the subset of YAML the SPEC uses:
    top-level `key: value` lines plus a `metadata:` block of two-space-indented
    `key: value` lines. Quoted values are unquoted.
    """
    m = re.match(r"\A---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not m:
        return None, ["no YAML frontmatter block (--- ... ---) at top of file"]
    fields, errors = {}, []
    current_block = None
    for raw in m.group(1).splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indented = raw.startswith((" ", "\t"))
        kv = re.match(r"^\s*([A-Za-z_][\w-]*):\s*(.*)$", raw)
        if not kv:
            errors.append(f"unparseable frontmatter line: {raw!r}")
            continue
        key, value = kv.group(1), kv.group(2).strip().strip("\"'")
        if not indented:
            if value == "":
                fields[key] = {}
                current_block = key
            else:
                fields[key] = value
                current_block = None
        else:
            if current_block is None:
                errors.append(f"indented line outside a block: {raw!r}")
            else:
                fields[current_block][key] = value
    return fields, errors


def split_list(value: str):
    return [item.strip() for item in value.split(",") if item.strip()]


def normalize(fields: dict) -> dict:
    """Comma-separated list fields become arrays, matching the schema."""
    meta = fields.get("metadata")
    if isinstance(meta, dict):
        for key in LIST_FIELDS & set(meta):
            meta[key] = split_list(meta[key])
    return fields


def declared_surfaces(meta) -> list:
    """The runtime surfaces a skill declares. Absent means all of them.

    Tolerates both shapes of the value: the raw comma-separated string that
    `parse_frontmatter` produces, and the list that `normalize` leaves behind.
    Callers include `package_skill.py`, which skips packaging a skill that
    does not run on `claude-ai`, because that download could not work.

    An older release tag has no `surfaces:` key at all, and gets every surface —
    which is the historically correct answer and keeps old-tag renders identical.
    """
    if not isinstance(meta, dict):
        return list(SURFACES)
    value = meta.get("surfaces")
    if value is None or value == "" or value == []:
        return list(SURFACES)
    if isinstance(value, list):
        return [str(s).strip() for s in value if str(s).strip()]
    return split_list(str(value))


def scaffold_schema(schema: dict) -> dict:
    """Same schema, minus the metadata *value* rules.

    The scaffold carries `class: deterministic-artifact | generative-workflow`
    and friends: placeholders that force the builder to choose, and that no enum
    will ever accept. Every metadata key must still be present; only what it
    holds goes unchecked.
    """
    relaxed = json.loads(json.dumps(schema))  # deep copy, stdlib only
    relaxed["properties"]["metadata"].pop("properties", None)
    return relaxed


def has_toc(text: str) -> bool:
    """True when the markdown carries a `Contents` heading followed by a list.

    Fence-aware via `headings()`, so a `# Contents` line inside a fenced block
    is not a table of contents.
    """
    lines = text.splitlines()
    heads = headings(lines)
    for pos, (idx, level, title) in enumerate(heads):
        if not TOC_HEADING_RE.match(title.strip()):
            continue
        end = next((i for i, lv, _ in heads[pos + 1:] if lv <= level), len(lines))
        items = [ln for ln in lines[idx + 1:end] if LIST_ITEM_RE.match(ln)]
        if len(items) >= 2:
            return True
    return False


def under_plugins(skill_dir: Path) -> bool:
    """True for `.../plugins/<plugin>/skills/<name>`, i.e. a distributed skill.

    Decides the `turnstile-skill-*` prefix rule without a mode flag: the
    `template/skill-name/` scaffold and `.claude/skills/<name>/` both answer
    False, which is exactly right — neither ships in a plugin.
    """
    parts = skill_dir.resolve().parts
    return len(parts) >= 4 and parts[-4] == "plugins" and parts[-2] == "skills"


def check_audience(skill_dir: Path, meta, problems) -> None:
    """audience <-> location (SPEC.md): the folder decides the value.

    A distributed skill's `metadata.audience` must match the plugin it lives in
    (PLUGIN_AUDIENCES; anything else — i.e. the public repo's plugin — takes
    DEFAULT_AUDIENCE). The scaffold and tooling lanes are exempt by shape:
    neither lives under `plugins/`, and a tooling skill has no metadata block.
    A missing `audience` is the schema's job to report; this checks the pairing.

    `ported-to` is the case-B marker: the internal original of a skill ported
    to the public repo. It is only coherent on an internal-audience skill —
    a staged draft is deleted at promotion, and a public skill IS the port.
    """
    if not isinstance(meta, dict):
        return
    label = skill_dir.name
    audience = str(meta.get("audience", "") or "").strip()
    ported = str(meta.get("ported-to", "") or "").strip()
    if ported and audience != "internal":
        problems.append(
            f"{label}.metadata.ported-to: only valid with audience: internal — "
            "a staged draft is deleted at promotion and a public skill IS the "
            f"port, so neither has a ported-to ({PORT_REF})"
        )
    if not under_plugins(skill_dir):
        return
    plugin = skill_dir.resolve().parts[-3]
    expected = PLUGIN_AUDIENCES.get(plugin, DEFAULT_AUDIENCE)
    if audience and audience != expected:
        problems.append(
            f"{label}.metadata.audience: {audience!r}, but a skill under "
            f"plugins/{plugin}/ must declare {expected!r} — audience matches "
            f"location ({PORT_REF})"
        )


def check_name(name, skill_dir: Path, problems) -> None:
    """Craft rules on the skill name. The charset and the folder-name match are
    the schema's job for distributed skills; length, reserved words and the
    tooling prefix apply to every lane."""
    label = skill_dir.name
    if not isinstance(name, str) or not name:
        return  # a missing name is already reported by the caller
    if len(name) > MAX_NAME_CHARS:
        problems.append(
            f"{label}.name: {len(name)} chars, over the {MAX_NAME_CHARS}-char cap "
            f"({STANDARD_REF}, Authoring craft)"
        )
    for word in RESERVED_NAME_WORDS:
        if word in name.lower():
            problems.append(
                f"{label}.name: contains the reserved word {word!r} — a skill "
                f"name may not carry the vendor's name ({STANDARD_REF})"
            )
    if under_plugins(skill_dir) and name.startswith(TOOLING_NAME_PREFIX):
        problems.append(
            f"{label}.name: the {TOOLING_NAME_PREFIX!r} prefix is reserved for "
            "Tier 2 repo tooling, which lives in .claude/skills/ and is never "
            "packaged or published. Name a distributed skill for the job it "
            f"does ({STANDARD_REF}, Authoring craft)"
        )


def check_description(description, label, problems) -> None:
    if not isinstance(description, str):
        return  # a missing description is already reported by the caller
    if len(description) > MAX_DESCRIPTION_CHARS:
        problems.append(
            f"{label}.description: {len(description)} chars, over the "
            f"{MAX_DESCRIPTION_CHARS}-char cap ({STANDARD_REF})"
        )
    if re.search(r"<[a-zA-Z/][^>]*>", description):
        problems.append(
            f"{label}.description: contains an angle-bracket tag "
            "(breaks the claude.ai skill uploader)"
        )


def check_body_size(body: str, label, problems) -> None:
    n = len(body.splitlines())
    if n > MAX_BODY_LINES:
        problems.append(
            f"{label}: SKILL.md body is {n} lines, over the {MAX_BODY_LINES}-line "
            f"cap — move detail into references/ ({STANDARD_REF})"
        )


def check_references(skill_dir: Path, body: str, problems) -> None:
    """Reference reachability, and a contents list in the long markdown ones.

    Reachability is a *mention*, not a link: skills routinely write paths in
    backticks rather than markdown links, so a link-graph check would match
    almost nothing.
    A basename match is loose (a `tokens.css` inside a fenced block false-passes)
    but this is an orphan heuristic, not a security control.

    Dotfiles are skipped, and that exclusion is load-bearing: the scaffold's
    `template/skill-name/references/` holds only a `.gitkeep`.
    """
    refs = skill_dir / "references"
    if not refs.is_dir():
        return
    label = skill_dir.name
    for path in sorted(refs.rglob("*")):
        if not path.is_file():
            continue
        rel_to_refs = path.relative_to(refs)
        if any(part.startswith(".") for part in rel_to_refs.parts):
            continue
        rel = path.relative_to(skill_dir).as_posix()
        if rel not in body and path.name not in body:
            problems.append(
                f"{label}: references/{rel_to_refs.as_posix()} is never mentioned "
                "in the SKILL.md body — an orphaned reference is one Claude will "
                f"never open ({STANDARD_REF}, reference reachability)"
            )
        if path.suffix.lower() != ".md":
            continue  # a table of contents in a pinned HTML artifact is absurd
        text = path.read_text(encoding="utf-8")
        n = len(text.splitlines())
        if n > TOC_REQUIRED_OVER_LINES and not has_toc(text):
            problems.append(
                f"{label}: references/{rel_to_refs.as_posix()} is {n} lines and "
                f"has no contents list — required over {TOC_REQUIRED_OVER_LINES} "
                "lines, because Claude reads a long reference partially "
                f"({STANDARD_REF}, Authoring craft)"
            )


def check_schema(value, schema, path, problems):
    """Validate `value` against the JSON Schema subset this repo uses:
    type (object/array/string), required, properties, enum, pattern,
    minLength, minItems, items."""
    stype = schema.get("type")
    if "enum" in schema:
        if value not in schema["enum"]:
            allowed = " | ".join(schema["enum"])
            problems.append(f"{path}: {value!r} is not one of: {allowed}")
        return
    if stype == "object":
        if not isinstance(value, dict):
            problems.append(f"{path}: expected a block, got {value!r}")
            return
        for req in schema.get("required", []):
            if req not in value or value[req] in ("", [], {}):
                problems.append(f"{path}.{req}: required field missing or empty")
        for key, subschema in schema.get("properties", {}).items():
            if key in value:
                check_schema(value[key], subschema, f"{path}.{key}", problems)
    elif stype == "array":
        if not isinstance(value, list):
            problems.append(f"{path}: expected a comma-separated list, got {value!r}")
            return
        if len(value) < schema.get("minItems", 0):
            problems.append(f"{path}: list is empty")
        for i, item in enumerate(value):
            check_schema(item, schema.get("items", {}), f"{path}[{i}]", problems)
    elif stype == "string":
        if not isinstance(value, str):
            problems.append(f"{path}: expected a string, got {value!r}")
            return
        if len(value) < schema.get("minLength", 0):
            problems.append(
                f"{path}: too short (min {schema['minLength']} chars): {value!r}"
            )
        pattern = schema.get("pattern")
        if pattern and not re.search(pattern, value):
            problems.append(f"{path}: {value!r} does not match {pattern}")


def validate_tooling_skill(skill_dir: Path):
    """Tier 2 repo tooling in `.claude/skills/<name>/`: craft rules only.

    No metadata block, no version, no CHANGELOG, no canonical section, no
    freshness check. A tooling skill is not distributed, so it has no
    independently stale copy to check against and nothing to publish.
    Freshness here is git-checkout freshness, handled by pull/rebase.
    """
    problems = []
    label = skill_dir.name
    text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")

    fields, parse_errors = parse_frontmatter(text)
    problems.extend(parse_errors)
    if fields is None:
        return problems

    for key in ("name", "description"):
        if not fields.get(key):
            problems.append(f"{label}.{key}: required field missing or empty")
    for key in TOOLING_FORBIDDEN_KEYS:
        if key in fields:
            problems.append(
                f"{label}: carries a {key!r} key, which belongs to a distributed "
                "skill. Tier 2 tooling is not packaged, versioned, or published "
                f"— it carries name + description only ({STANDARD_REF})"
            )
    for key in sorted(set(fields) - TOOLING_FRONTMATTER_KEYS - set(TOOLING_FORBIDDEN_KEYS)):
        problems.append(
            f"{label}: unexpected frontmatter key {key!r} (allowed: "
            f"{', '.join(sorted(TOOLING_FRONTMATTER_KEYS))})"
        )

    name = fields.get("name")
    if isinstance(name, str) and name and name != label:
        problems.append(f"{label}: frontmatter name {name!r} != folder name")
    check_name(name, skill_dir, problems)
    check_description(fields.get("description"), label, problems)

    if (skill_dir / "reference").is_dir():
        problems.append(
            f"{label}: uses 'reference/' (singular) — the SPEC's in-skill "
            "layout is 'references/'"
        )

    body = strip_frontmatter(text)
    check_body_size(body, label, problems)
    check_references(skill_dir, body, problems)
    return problems


def validate_distributed_skill(skill_dir: Path, schema: dict):
    """Tier 1: a skill under `plugins/*/skills/`, governed by the whole SPEC.

    Returns a list of problems; empty means the skill conforms.
    """
    problems = []
    skill_md = skill_dir / "SKILL.md"
    text = skill_md.read_text(encoding="utf-8")

    fields, parse_errors = parse_frontmatter(text)
    problems.extend(parse_errors)
    if fields is None:
        return problems

    # 'none' is legal for connectors/scopes; expand before schema-normalizing
    meta = fields.get("metadata")
    if isinstance(meta, dict):
        for key in NONE_OK & set(meta):
            if meta[key].strip().lower() == "none":
                meta[key] = "none"

    normalize(fields)
    check_schema(fields, schema, skill_dir.name, problems)
    check_audience(skill_dir, fields.get("metadata"), problems)

    if isinstance(fields.get("name"), str) and fields["name"] != skill_dir.name:
        problems.append(
            f"{skill_dir.name}: frontmatter name {fields['name']!r} != folder name"
        )
    check_name(fields.get("name"), skill_dir, problems)
    check_description(fields.get("description"), skill_dir.name, problems)

    # Layout rules
    if (skill_dir / "reference").is_dir():
        problems.append(
            f"{skill_dir.name}: uses 'reference/' (singular) — the SPEC's "
            "in-skill layout is 'references/'"
        )
    for ride_along in ("CHANGELOG.md",):
        if not (skill_dir / ride_along).is_file():
            problems.append(f"{skill_dir.name}: {ride_along} missing")

    # Body rules
    body = strip_frontmatter(text)
    check_body_size(body, skill_dir.name, problems)
    check_references(skill_dir, body, problems)

    # Inputs/outputs are declared in the canonical section, not the frontmatter
    # and not wherever the author felt like putting them (SPEC.md). The section
    # is the skill's provider-agnostic contract, read by humans as well as CI.
    section = extract_section(body, CANONICAL_SECTION)
    if section is None:
        problems.append(
            f"{skill_dir.name}: missing the canonical '## {CANONICAL_SECTION}' "
            "section in the SKILL.md body (exact heading, verbatim — see "
            f"{STANDARD_REF})"
        )
        section = ""  # report the inputs/outputs misses against it too
    if not INPUTS_RE.search(section):
        problems.append(
            f"{skill_dir.name}: inputs not declared in the "
            f"'{CANONICAL_SECTION}' section (a '**Inputs:**' line or an Inputs "
            f"heading — see {STANDARD_REF})"
        )
    if not OUTPUTS_RE.search(section):
        problems.append(
            f"{skill_dir.name}: outputs not declared in the "
            f"'{CANONICAL_SECTION}' section (an '**Outputs:**' line or an "
            f"Outputs heading — see {STANDARD_REF})"
        )

    # A non-blocking freshness check is OPTIONAL since Skill Standard v0.26
    # (SPEC.md, Build requirements): organization-managed plugin sync keeps
    # installed copies current, so the check only earns its lines in a skill
    # that also ships as a `.skill` upload. Required v0.7–v0.25; now a stdout
    # warning. The --scaffold lane shares this function and inherits the same
    # non-failure.
    if not FRESHNESS_RE.search(body):
        print(f"warn: {skill_dir.name}: no freshness check in the SKILL.md "
              "body — optional since standard v0.26 (organization-managed "
              "plugin sync keeps installed copies current); keep one only for "
              ".skill uploads")
    return problems


# The name earlier callers knew. Kept as a thin
# alias rather than renamed: this module's import surface is a stable contract.
validate_skill = validate_distributed_skill


def main() -> None:
    args = sys.argv[1:]
    if not args or "-h" in args or "--help" in args:
        print(__doc__)
        sys.exit(0 if args else 2)

    scaffold = "--scaffold" in args
    tooling = "--tooling" in args
    args = [a for a in args if a not in ("--scaffold", "--tooling")]
    if scaffold and tooling:
        print("ERROR: --scaffold and --tooling are different lanes", file=sys.stderr)
        sys.exit(2)
    if not args:
        flag = "--tooling" if tooling else "--scaffold"
        print(f"ERROR: {flag} needs a directory to check", file=sys.stderr)
        sys.exit(2)

    schema = None
    if not tooling:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        if scaffold:
            schema = scaffold_schema(schema)
    checked, failed = 0, 0
    for arg in args:
        skill_dir = Path(arg).resolve()
        if not skill_dir.is_dir():
            print(f"ERROR: {arg}: not a directory", file=sys.stderr)
            failed += 1
            continue
        if not (skill_dir / "SKILL.md").is_file():
            print(f"skip: {arg} (no SKILL.md)")
            continue
        checked += 1
        if tooling:
            problems = validate_tooling_skill(skill_dir)
        else:
            problems = validate_distributed_skill(skill_dir, schema)
        if problems:
            failed += 1
            print(f"FAIL: {skill_dir.name}", file=sys.stderr)
            for p in problems:
                print(f"  - {p}", file=sys.stderr)
        elif tooling:
            print(f"ok: {skill_dir.name} conforms to the tooling-skill rules")
        elif scaffold:
            print(f"ok: {skill_dir.name} scaffold conforms (metadata values unchecked)")
        else:
            print(f"ok: {skill_dir.name} conforms to the frontmatter schema")
    print(f"{checked} skill(s) checked, {failed} failing")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
