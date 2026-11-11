"""Application boundary shared by the command line and integrations."""
from .model import Event
from .storage import Store
from .reports import journal_counts

class Ledger:
    def __init__(self, path):
        self.store = Store(path)

    def ingest(self, values):
        # Parse before opening a write transaction, so invalid batches leave no trace.
        events = [Event.parse(value) for value in values]
        return self.store.append(events)

    def events(self, tenant):
        return self.store.read(tenant)

    def counts(self, tenant):
        return journal_counts(self.events(tenant))

    def history(self):
        return self.store.history()

    def close(self):
        self.store.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
