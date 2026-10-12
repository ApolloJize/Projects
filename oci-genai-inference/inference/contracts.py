import json
from dataclasses import asdict, dataclass
from decimal import Decimal

SERVICES = {"SCREENING", "IMMUNIZATION", "OUTREACH"}
OPERATIONS = {"total_visits", "visits_by_ward", "visits_by_service", "busiest_ward", "unsupported"}


class PlanError(ValueError):
    """The model did not return a supported query plan."""


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise PlanError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


@dataclass(frozen=True)
class QueryPlan:
    operation: str
    ward: int | None = None
    service: str | None = None

    def __post_init__(self):
        if not isinstance(self.operation, str) or self.operation not in OPERATIONS:
            raise PlanError("Unsupported operation")
        if self.ward is not None and (type(self.ward) is not int or not 1 <= self.ward <= 8):
            raise PlanError("ward must be null or an integer from 1 to 8")
        if self.service is not None and (not isinstance(self.service, str) or self.service not in SERVICES):
            raise PlanError("Unsupported service")
        if self.operation == "unsupported" and (self.ward is not None or self.service is not None):
            raise PlanError("An unsupported plan must have null filters")

    @classmethod
    def parse(cls, text):
        if not isinstance(text, str) or len(text) > 4096:
            raise PlanError("Model output must be a small JSON object")
        try:
            value = json.loads(text, object_pairs_hook=unique_object)
        except (json.JSONDecodeError, TypeError) as exc:
            raise PlanError("Model output was not valid JSON") from exc
        if not isinstance(value, dict) or set(value) != {"operation", "ward", "service"}:
            raise PlanError("Model output must contain exactly operation, ward, and service")
        try:
            return cls(**value)
        except (TypeError, ValueError) as exc:
            raise PlanError("Model output contains invalid plan values") from exc


def integer(value):
    if type(value) is int:
        return value
    if isinstance(value, Decimal) and value.is_finite() and value == value.to_integral_value():
        return int(value)
    raise ValueError("Aggregate fields must contain integers")


@dataclass(frozen=True)
class SummaryRow:
    ward: int
    service_type: str
    visits: int
    event_count: int

    def __post_init__(self):
        if type(self.ward) is not int or not 1 <= self.ward <= 8:
            raise ValueError("Invalid ward in data")
        if not isinstance(self.service_type, str) or self.service_type not in SERVICES:
            raise ValueError("Invalid service in data")
        if any(type(v) is not int or v < 0 for v in (self.visits, self.event_count)):
            raise ValueError("Counts must be nonnegative integers")

    @classmethod
    def from_record(cls, ward, service_type, visits, event_count):
        return cls(integer(ward), service_type, integer(visits), integer(event_count))

    @property
    def evidence_id(self):
        return f"ward-{self.ward}-{self.service_type.lower()}"

    def evidence(self):
        return {"id": self.evidence_id, **asdict(self)}


def validate_rows(rows):
    rows = list(rows)
    if len(rows) > 24:
        raise ValueError("Expected at most 8 wards × 3 services")
    if len({(r.ward, r.service_type) for r in rows}) != len(rows):
        raise ValueError("Duplicate ward/service aggregate")
    return sorted(rows, key=lambda r: (r.ward, r.service_type))
