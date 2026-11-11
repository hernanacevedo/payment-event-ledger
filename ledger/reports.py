"""Operational journal counts; money reconciliation is a separate projection."""
def journal_counts(events):
    result = {"capture": 0, "refund": 0, "reverse": 0}
    for event in events:
        result[event["kind"]] += 1
    return result
