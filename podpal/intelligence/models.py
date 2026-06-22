from dataclasses import dataclass, field

@dataclass
class SupportingSource:
    source: str
    title: str
    url: str
    score: float


@dataclass
class ConfidenceResult:
    score: float
    label: str
    corroboration_count: int
    sources: list[SupportingSource] = field(default_factory=list)