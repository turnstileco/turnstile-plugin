# Changelog: milestone-lapse-risk

Newest first. Semver per [SPEC.md](../../../../SPEC.md): PATCH = fix or
wording, MINOR = new backward-compatible capability, MAJOR = breaking. Every
PR that touches this skill adds an entry here; CI checks.

## 1.0.0, 2026-10-16

First public release.

- **Answers in chat which subscriptions are waiting on a milestone**, from one
  filtered subscriptions call, then reads each one's phases.
- **Works out each lapse deadline from the phase schedule**: the prior
  phase's start plus its term, or a walk from the service start date when no
  start date is recorded. Where a completed milestone could have shortened
  the walk, the date is reported as "no later than", never as an exact count.
- **Classifies by the dates, never by the subscription's status**, so a
  subscription past its deadline whose status never changed is still
  reported as lapsed.
- **Five groups, in the order someone acts on them**: already lapsed, with
  the amendment that recovers it; at risk inside the window; waiting with a
  later deadline; waiting with no deadline running; and needs a closer look,
  each with its reason.
- **Says what it checked.** The headline states what the counts are out of,
  and the answer never says "nothing" when the list was incomplete, the run
  was narrowed, or a subscription could not be read.
- **Money in minor units, one currency per total.**
- **Read-only.** It never amends, marks a milestone complete, notifies, or
  schedules anything.

Versions before `1.0.0` were pre-release drafts and are not published here.
