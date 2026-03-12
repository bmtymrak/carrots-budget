# ADR 0001: Recurring Purchases Architecture

- Status: Accepted
- Date: 2026-03-12

## Context

Carrots Budget needs a way to manage purchases that repeat over time, such as subscriptions, bills, and other predictable monthly expenses. The feature has two separate user needs:

1. Maintain a reusable set of recurring purchase templates.
2. Quickly turn those templates into real monthly `Purchase` records without duplicating data entry.

The implementation also needs to fit the existing application architecture:

- Django models and server-rendered templates
- HTMX-driven modal workflows
- Strict per-user data isolation
- Minimal JavaScript
- Existing `Purchase` model semantics (`source`, `location`, `category`, `notes`, etc.)

A key requirement that emerged during implementation was preventing the same recurring purchase from being added multiple times for the same month while still showing the user the actual purchase details that were created.

## Decision

We model recurring purchases as a separate template entity and connect created purchases back to that template.

### 1. Separate `RecurringPurchase` template model

A dedicated `RecurringPurchase` model is used to store reusable purchase defaults:

- `user`
- `name`
- `amount`
- `category`
- `source`
- `location`
- `notes`
- `is_active`
- timestamps

This model is not a scheduled transaction engine. It is a user-managed template library for creating real `Purchase` rows.

### 2. Real spending remains in `Purchase`

Monthly spending is still represented by normal `Purchase` records. When a user chooses recurring items in the monthly modal, the system creates standard `Purchase` objects rather than virtual or derived records.

This keeps reporting, category totals, editing, and existing purchase flows consistent because the rest of the application already expects actual spending to live in `Purchase`.

### 3. Link created purchases back to their template

`Purchase.recurring_purchase` is a nullable foreign key to `RecurringPurchase`.

This relationship is used to:

- determine whether a recurring purchase has already been added for a given month
- show the actual created purchase details in the modal once it exists
- preserve a traceable connection between the reusable template and the generated transaction

The relationship is nullable so normal one-off purchases remain unaffected.

### 4. HTMX modal workflows for management and quick add

Recurring purchase management and monthly quick-add are implemented as HTMX modal views:

- yearly budget detail opens a management modal for create/edit/delete
- monthly budget detail opens a quick-add modal for batch creation
- creating a recurring purchase re-renders the same modal so the list updates and the form resets

This follows the existing interaction style in the application and avoids adding a separate SPA-style client architecture.

### 5. User-editable values at creation time

The monthly quick-add modal pre-populates each recurring purchase but allows the user to adjust:

- date
- amount
- source
- location
- category
- notes

These edits affect the created `Purchase`, not the underlying recurring template.

### 6. Duplicate prevention based on the foreign key

To determine whether a recurring purchase has already been added for the selected month, the system checks for `Purchase` rows in that month with the corresponding `recurring_purchase` foreign key.

If a purchase already exists:

- the row is shown as already added
- fields are disabled
- the modal displays the actual created purchase values rather than the template defaults

## Consequences

### Positive

- Clear separation between reusable templates and actual spending records
- Existing purchase reports and summaries continue to work without architectural changes
- Duplicate prevention is reliable because it is based on an explicit relationship, not name matching
- Users can keep template defaults while still adjusting per-month transaction details
- The feature stays aligned with the project's Django + HTMX architecture

### Negative

- One recurring template currently maps to at most one purchase per month in the duplicate-prevention workflow
- Additional logic is required in the modal to merge template data with actual created purchase data
- The system does not currently support automated scheduling; users still trigger creation manually

## Alternatives Considered

### 1. Store recurring behavior directly on `Purchase`

Rejected because a single model would mix two concepts:

- reusable purchase defaults
- actual recorded spending

That would complicate reporting and blur the distinction between planned recurring items and completed transactions.

### 2. Detect duplicates by matching purchase fields

Rejected because matching by name, amount, or merchant/source is brittle and can produce false positives or false negatives. A foreign key gives an explicit and durable relationship.

### 3. Create purchases automatically each month

Rejected for now because the requested feature is a user-driven quick-add workflow, not a scheduler. Automatic creation would introduce additional product and operational questions such as timing, idempotency, backfilling, and user expectations.

### 4. Use a separate recurring purchase management page instead of modals

Rejected because the existing UI patterns already rely on HTMX modal flows, and this feature fits naturally into that interaction model.
