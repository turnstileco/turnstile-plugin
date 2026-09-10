# Turnstile plugin

Turnstile runs quote-to-cash: quotes, subscriptions, invoices, customers,
catalog, reporting. This plugin connects an AI assistant to it — the hosted
Turnstile MCP server plus the skills that teach the assistant to use it well.

Once it's installed you can ask for revenue work in plain language:

> Which invoices are sitting in review, and what's holding them up?
>
> What's on this customer's subscription, and when does it renew?
>
> How much did we invoice last month, by product?
>
> Draft a quote for the terms we just agreed, and show me the invoice schedule
> before anything goes out.

## Install

**Claude Code**

```
/plugin marketplace add turnstileco/turnstile-plugin
/plugin install turnstile@turnstile
```

**Claude web, desktop and Cowork** — Customize → Plugins → add by URL, then
install `turnstile`.

Either way one step registers both halves: the hosted MCP server at
`https://mcp.app.turnstile.ai` and the skills. Your assistant opens a Turnstile
login the first time it needs one. No credentials live in this repo or in the
plugin — the connection runs as you, with the permissions your Turnstile
account already has.

On claude.ai you can also connect the MCP server as a custom connector and
upload individual skills as `.skill` files from [Releases](../../releases).

## Skills

| Skill | What it answers | Version |
|---|---|---|
| [`turnstile-start-here`](plugins/turnstile/skills/turnstile-start-here/) | What can I do with Turnstile from here, and how do I do it safely? Maps the connection module by module, with example prompts and a starting menu. | 1.0.0 |

Start with `turnstile-start-here`. It's the front door: it describes what the
connection can do in the same module language the Turnstile app uses, and it
covers taking a first write action without surprises.

More skills are published here as they're released.

## Reading and writing

The Turnstile connection exposes read tools and write tools. Reads are safe to
explore freely. Writes act on real records — issuing an invoice, publishing a
quote, updating a customer — and a few of them can't be undone.

Skills here are built to the same rule: ask before every write, and re-read the
record immediately before acting on it, so the assistant never acts on a stale
view. The details are in
[`write-safety.md`](plugins/turnstile/skills/turnstile-start-here/references/write-safety.md).

## Feedback

We aren't taking outside pull requests yet — the library is still being built
out. Your experience using these skills is what we want in the meantime:

- **A skill got something wrong?** [Open a bug report.](../../issues/new?template=bug-report.yml)
  Tell us which surface and which model, and what the assistant actually did —
  skills fail differently across both.
- **Want a skill that doesn't exist?** [Request one.](../../issues/new?template=skill-request.yml)

[SPEC.md](SPEC.md) is the standard every skill here is held to, and CI enforces
its mechanical half. Questions about Turnstile itself or about your own data
belong in your usual Turnstile support channel, not in an issue here.

## Repo layout

```
SPEC.md               the standard every skill here is held to
plugins/turnstile/    the install unit: MCP wiring + skills/
template/             scaffold for a new skill
scripts/              the validators and packager CI runs
```

Folders in git are the source of truth. The `.skill` bundles on each release
are build artifacts, packaged by CI from these folders.

## Versioning

Semver on everything a user sees: each skill in its `SKILL.md` frontmatter with
its own `CHANGELOG.md`, the plugin in `plugin.json`, and release tags matching
the plugin version. `1.0.0` is a skill's first released version.

## License

[Apache-2.0](LICENSE).
