# Changelog: renewals-overview

Newest first. Semver per [SPEC.md](../../../../SPEC.md): PATCH = fix or
wording, MINOR = new backward-compatible capability, MAJOR = breaking. Every
PR that touches this skill adds an entry here; CI checks.

## 1.0.0, 2026-10-16

First public release.

- **Renewals in a window.** What renews in the next 30, 60 or 90 days, or in a
  calendar month or quarter, read live from your subscriptions with the window
  applied in the query rather than afterwards. A calendar period also lists what
  already lapsed earlier in that period.
- **The right renewal date.** The next auto-renewal date for an auto-renewing
  subscription, the expiration date otherwise, and the termination date when one
  is on record. The end of the current service term is never used as a renewal
  date.
- **Every subscription in exactly one group.** Terminating, at risk (not
  auto-renewing, no termination on record), renews without action, or
  classification unknown, each with its own total.
- **Money kept honest.** Current contract value, converted from minor units once
  at display, totalled per currency and never summed or ranked across
  currencies. Asked what a renewal will be worth, the skill says that is not a
  figure it reads, then gives current contract value as the labelled stand-in.
- **Churn risk ranked from the billing record alone.** Lapsed subscriptions
  first, each labelled by whether the customer has another agreement running or
  signed; then terminations on record; then renewals that will not renew on
  their own, nearest first. Payment standing breaks ties and is printed exactly
  as returned.
- **Answers that add up.** Bucket counts, group counts and any share are
  reconciled against the rows returned before the answer is sent, and an answer
  built on an incomplete response states no total.
- **Read-only.** The skill renews, amends, terminates and sends nothing, shows
  only a customer's name and payment standing, and stops when a tool is missing
  or a call is refused.

Versions before `1.0.0` were pre-release drafts and are not published here.
