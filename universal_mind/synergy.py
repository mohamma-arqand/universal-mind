"""Synergy metrics for capability ensembles.

Measures the collective intelligence of a group of capabilities based on:
- Diversity: Shannon entropy over capability domains
- Discernment: Judgment accuracy (ability to select the right capability)
- Synergy: Product of diversity and discernment
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from math import log2
from typing import Any


@dataclass(frozen=True)
class DiversityResult:
    """Result of diversity calculation."""
    entropy: float  # Shannon entropy in bits
    domain_counts: dict[str, int]
    total_capabilities: int
    unique_domains: int


@dataclass(frozen=True)
class DiscernmentResult:
    """Result of discernment (judgment accuracy) calculation."""
    accuracy: float  # 0.0 to 1.0
    correct_selections: int
    total_selections: int
    confusion_matrix: dict[str, dict[str, int]]  # predicted -> actual counts


@dataclass(frozen=True)
class SynergyResult:
    """Result of synergy calculation."""
    diversity: DiversityResult
    discernment: DiscernmentResult
    synergy_score: float  # diversity.entropy * discernment.accuracy


def calculate_diversity(capabilities: list[Any], domain_extractor: Callable[[Any], str] = lambda c: c.get('domain', 'unknown')) -> DiversityResult:
    """Calculate Shannon entropy over capability domains.

    Args:
        capabilities: List of capability objects
        domain_extractor: Function to extract domain from a capability object

    Returns:
        DiversityResult with entropy and domain statistics
    """
    if not capabilities:
        return DiversityResult(
            entropy=0.0,
            domain_counts={},
            total_capabilities=0,
            unique_domains=0,
        )

    domains = [domain_extractor(c) for c in capabilities]
    counts = Counter(domains)
    total = len(capabilities)
    unique = len(counts)

    # Shannon entropy: H = -sum(p * log2(p))
    entropy = 0.0
    for count in counts.values():
        p = count / total
        if p > 0:
            entropy -= p * log2(p)

    return DiversityResult(
        entropy=entropy,
        domain_counts=dict(counts),
        total_capabilities=total,
        unique_domains=unique,
    )


def calculate_discernment(
    predictions: list[str],
    actuals: list[str],
    capability_names: list[str] | None = None
) -> DiscernmentResult:
    """Calculate judgment accuracy (discernment).

    Args:
        predictions: List of predicted capability names
        actuals: List of actual (ground truth) capability names
        capability_names: Optional list of all known capability names for confusion matrix

    Returns:
        DiscernmentResult with accuracy and confusion matrix
    """
    if len(predictions) != len(actuals):
        raise ValueError("predictions and actuals must have same length")

    if not predictions:
        return DiscernmentResult(
            accuracy=0.0,
            correct_selections=0,
            total_selections=0,
            confusion_matrix={},
        )

    correct = sum(1 for p, a in zip(predictions, actuals) if p == a)
    total = len(predictions)
    accuracy = correct / total

    # Build confusion matrix
    all_names = capability_names or sorted(set(predictions) | set(actuals))
    confusion = {name: {name: 0 for name in all_names} for name in all_names}

    for pred, act in zip(predictions, actuals):
        if pred in confusion and act in confusion[pred]:
            confusion[pred][act] += 1

    return DiscernmentResult(
        accuracy=accuracy,
        correct_selections=correct,
        total_selections=total,
        confusion_matrix=confusion,
    )


def calculate_synergy(
    capabilities: list[Any],
    predictions: list[str],
    actuals: list[str],
    domain_extractor: Callable[[Any], str] = lambda c: c.get('domain', 'unknown'),
    capability_names: list[str] | None = None
) -> SynergyResult:
    """Calculate full synergy metric: diversity * discernment.

    Args:
        capabilities: List of capability objects
        predictions: Predicted capability names
        actuals: Actual (ground truth) capability names
        domain_extractor: Function to extract domain from capability
        capability_names: Optional list of all capability names

    Returns:
        SynergyResult with diversity, discernment, and synergy score
    """
    diversity = calculate_diversity(capabilities, domain_extractor)
    discernment = calculate_discernment(predictions, actuals, capability_names)
    synergy_score = diversity.entropy * discernment.accuracy

    return SynergyResult(
        diversity=diversity,
        discernment=discernment,
        synergy_score=synergy_score,
    )