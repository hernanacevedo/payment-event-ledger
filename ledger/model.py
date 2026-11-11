"""Immutable input envelopes and canonical event identity."""
from dataclasses import dataclass, asdict
import json

class ValidationError(ValueError):
    pass

class ConflictError(ValueError):
    pass

KINDS = frozenset({"capture", "refund", "reverse"})
FIELDS = frozenset({"tenant", "provider", "event_id", "payment_id", "kind", "amount", "currency", "parent_id"})

@dataclass(frozen=True)
class Event:
    tenant: str
    provider: str
    event_id: str
    payment_id: str
    kind: str
    amount: int
    currency: str
    parent_id: str | None = None

    @classmethod
    def parse(cls, value):
        if not isinstance(value, dict) or set(value) - FIELDS:
            raise ValidationError("event must be an object with documented fields only")
        try:
            result = cls(**value)
        except TypeError as exc:
            raise ValidationError("missing event fields") from exc
        for key in ("tenant", "provider", "event_id", "payment_id"):
            text = getattr(result, key)
            if not isinstance(text, str) or not text or text.strip() != text:
                raise ValidationError(key + " must be a nonempty trimmed string")
        if result.kind not in KINDS:
            raise ValidationError("unknown kind")
        if type(result.amount) is not int or not 0 < result.amount <= 10**12:
            raise ValidationError("amount must be positive integer minor units, at most 1000000000000")
        if not isinstance(result.currency, str) or len(result.currency) != 3 or not result.currency.isascii() or not result.currency.isalpha() or not result.currency.isupper():
            raise ValidationError("currency must be three uppercase ASCII letters")
        if result.kind == "capture":
            if result.parent_id is not None:
                raise ValidationError("capture cannot have a parent")
        elif not isinstance(result.parent_id, str) or not result.parent_id or result.parent_id.strip() != result.parent_id:
            raise ValidationError("refund and reverse require a parent_id")
        return result

    def payload(self):
        return asdict(self)

    def canonical(self):
        return json.dumps(self.payload(), sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    @property
    def key(self):
        return self.tenant, self.provider, self.event_id
