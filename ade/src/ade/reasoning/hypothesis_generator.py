"""Template-based hypothesis generation for ADE reports."""

from __future__ import annotations

from dataclasses import dataclass

from ade.discovery.evidence_collector import ConceptEvidence


@dataclass(frozen=True)
class Hypothesis:
    """A cautious hypothesis for a candidate unknown concept."""

    concept_id: str
    text: str


class HypothesisGenerator:
    """Generate cautious, non-claiming hypotheses from evidence summaries."""

    def generate(self, evidence_items: list[ConceptEvidence]) -> list[Hypothesis]:
        """Return template-based hypotheses requiring human review."""

        hypotheses: list[Hypothesis] = []
        for item in evidence_items:
            text = (
                f"{item.concept_id} may represent a candidate unknown concept "
                f"because {item.example_count} supporting patch(es) show elevated "
                f"novelty relative to this dataset. This is a hypothesis for expert "
                f"review, not a validated discovery."
            )
            hypotheses.append(Hypothesis(concept_id=item.concept_id, text=text))
        return hypotheses
