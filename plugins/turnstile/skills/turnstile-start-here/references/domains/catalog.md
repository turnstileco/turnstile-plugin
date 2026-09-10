# Catalog

The catalog is where your pricing lives. Through the MCP it has three objects you can
read and change, and one you can only see the name of:

- **Products** — the things you sell. Read and write, including archive.
- **Metrics** — the usage you meter: API calls, seats, gigabytes, whatever drives your
  bill. Read and write.
- **Units** — how that usage is counted and labeled on quotes and invoices. Read and
  create.
- **Plans** — how products are packaged and priced. **No MCP tool lists, reads, or
  edits plans.** A plan's name appears on the subscriptions that use it (the
  `planName` field) and nowhere else. Plans are managed in the Turnstile app.

Everything else in Turnstile builds on the catalog: quotes quote catalog products,
subscriptions bill against them, and invoices price usage through your metrics.

## What you can ask today

- "List my products."
- "Do we have a product called Premium Support?"
- "What usage metrics do we meter?"
- "Which units do we bill in?"
- "Create a product called Onboarding Services."

## What these tools tell you

- `Turnstile:list_turnstile_products` — your active products, newest first, with a
  name filter for partial matches. `Turnstile:get_turnstile_product` for one product
  in full.
- `Turnstile:create_turnstile_product` and `Turnstile:update_turnstile_product` — add
  or edit a product. Products are archived rather than deleted; if your session carries
  archive and unarchive tools, treat archiving as reversible (Tier 1 in
  `../write-safety.md`).
- `Turnstile:list_turnstile_metrics`, `Turnstile:get_turnstile_metric`,
  `Turnstile:get_turnstile_metric_values`, `Turnstile:get_turnstile_metric_breakdown`
  — the metrics you meter and the values they have recorded. Create, update, and delete
  exist too (`Turnstile:create_turnstile_metric`, `Turnstile:update_turnstile_metric`,
  `Turnstile:delete_turnstile_metric`); deleting a metric is a Tier 2 action, because
  it takes the metric out of use and restoring it is not something the assistant can do from
  here.
- `Turnstile:list_turnstile_units` and `Turnstile:create_turnstile_unit` — the units
  usage is counted in.

## "What plans do I have?"

This question does not have a direct answer through the MCP, and the product list is
not it. When someone asks about plans:

1. Say plainly that plans are not something the MCP can list; they live in the app.
2. Offer the two things that are available: the product list, and the distinct plan
   names on active subscriptions (`Turnstile:list_turnstile_subscriptions` with
   `status: ACTIVE`, reading `planName` off each record).
3. Ask which of those they meant before running either.

Never answer a plan question with the product list unlabeled. A user who asked for
plans and got products will take the products for plans.

## Good to know

- **Catalog changes are real changes.** Creating or editing a product, metric, or unit
  is Tier 1 in `../write-safety.md`: say what will change, wait for a yes. Before
  any create, run the name-filtered list first; a record by that name may already
  exist, and then the right move is to say so, not to create a twin. A product
  that a quote or subscription already uses should be edited with care, because
  the change shows up downstream.
- **Billable metrics are a separate object from metrics.** Your session may carry
  billable-metric tools (list, get, create). Those can be created and read but not
  updated or deleted, so a mistake in a billable metric is corrected in the app, not
  through the MCP. Treat creation as Tier 1 and confirm the definition before running
  it.

Your session may include additional catalog tools beyond those named here — Turnstile
ships new MCP capabilities continuously, and your account's tool list is the source of
truth. If you see a tool here that your session lacks, it may not be available on your
plan yet; that is an account/rollout question for Turnstile support, not a product gap.

## Verify this area works

Ask: **"List my products."**

A good result: the assistant uses `Turnstile:list_turnstile_products` and returns product names
you recognize from the Turnstile app, with no confirmation prompt because reading is
always safe. Empty results where you know products exist, or an error, means the
connection needs attention.
