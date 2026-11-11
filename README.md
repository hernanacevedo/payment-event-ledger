# Payment Event Ledger

A small operational journal for payment-provider event feeds. Python 3.12 and SQLite,
with no third-party runtime dependencies. All examples are fictional.

The journal stores immutable input envelopes, scopes identity by tenant and provider,
accepts late causal parents, and makes each batch atomic. Replays are idempotent;
conflicting payloads are rejected. Audit history records successful batches only.
It deliberately separates journal storage from money reconciliation: a count of
provider events is not an accounting balance.

## Commands

```sh
python -m ledger --db local.db ingest examples/events.jsonl
python -m ledger --db local.db events --tenant shop
python -m ledger --db local.db counts --tenant shop
python -m ledger --db local.db history
python -m unittest discover -s tests -v
```

## Input envelope

Each JSONL object has tenant, provider, event_id, payment_id, kind, amount and currency.
Kinds are capture, refund and reverse. Amount is a positive integer in minor units,
at most 10^12; currency is three uppercase ASCII letters. Capture has no parent;
refund and reverse require parent_id. Identifiers are nonempty trimmed strings.
References are scoped to the same tenant and provider. Ingestion validates syntax,
not causal semantics: a parent may be missing, invalid or arrive later. Canonically
identical event identities are duplicates; changing any envelope field is a conflict.
Unknown fields are rejected. No credentials or real financial records are required.

## Layout

model validates envelopes; storage owns SQLite transactions; service exposes the
application boundary; reports contains operational projections; __main__ is the CLI.
The standard-library regression suite covers identity, rollback, validation, replay,
persistence and asynchronous arrival. MIT licensed.
