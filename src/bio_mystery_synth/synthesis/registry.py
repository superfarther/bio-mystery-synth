from bio_mystery_synth.synthesis.base import Intervention, ObservationSimulator


class SynthesisRegistry:
    def __init__(self) -> None:
        self._interventions: dict[str, Intervention] = {}
        self._observations: dict[str, ObservationSimulator] = {}

    def register_intervention(self, name: str, intervention: Intervention) -> None:
        if name in self._interventions:
            raise ValueError(f"duplicate intervention: {name}")
        self._interventions[name] = intervention

    def register_observation(self, name: str, observation: ObservationSimulator) -> None:
        if name in self._observations:
            raise ValueError(f"duplicate observation simulator: {name}")
        self._observations[name] = observation

    def intervention(self, name: str) -> Intervention:
        try:
            return self._interventions[name]
        except KeyError as exc:
            raise ValueError(f"unknown intervention: {name}") from exc

    def observation(self, name: str) -> ObservationSimulator:
        try:
            return self._observations[name]
        except KeyError as exc:
            raise ValueError(f"unknown observation simulator: {name}") from exc
