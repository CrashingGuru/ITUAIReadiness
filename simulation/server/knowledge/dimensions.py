"""Load and access the 13 AI Readiness dimension definitions."""

import json
from functools import lru_cache
from pathlib import Path

from server.config import settings
from server.models import DimensionDefinition, Factor, MetricDefinition


@lru_cache(maxsize=1)
def load_dimensions() -> list[DimensionDefinition]:
    """Load all 13 dimension definitions from dimensions.json."""
    path = settings.framework_dir / "dimensions.json"
    with open(path) as f:
        data = json.load(f)

    dimensions = []
    for d in data["dimensions"]:
        metrics = [MetricDefinition(**m) for m in d["metrics"]]
        dim = DimensionDefinition(
            id=d["id"],
            name=d["name"],
            short_name=d["short_name"],
            description=d["description"],
            mapped_factors=[Factor(f) for f in d["mapped_factors"]],
            metrics=metrics,
        )
        dimensions.append(dim)
    return dimensions


def get_dimension(dim_id: int) -> DimensionDefinition:
    """Get a single dimension by ID (1-13)."""
    dims = load_dimensions()
    for d in dims:
        if d.id == dim_id:
            return d
    raise ValueError(f"Dimension {dim_id} not found (valid: 1-13)")


def get_dimensions_for_factor(factor: Factor) -> list[DimensionDefinition]:
    """Get all dimensions mapped to a given factor."""
    return [d for d in load_dimensions() if factor in d.mapped_factors]


def get_dimension_names() -> dict[int, str]:
    """Return {id: name} mapping for all 13 dimensions."""
    return {d.id: d.name for d in load_dimensions()}


def get_all_metrics_for_dimension(dim_id: int) -> list[MetricDefinition]:
    """Get all metrics for a dimension."""
    return get_dimension(dim_id).metrics
