import random

from bio_mystery_synth.core import AnonymizationSpec


def anonymize(raw_ids: list[str], spec: AnonymizationSpec, rng: random.Random) -> dict[str, str]:
    public = [f"{spec.sample_prefix}_{index:0{spec.width}d}" for index in range(1, len(raw_ids) + 1)]
    if spec.shuffle:
        rng.shuffle(public)
    return dict(zip(raw_ids, public, strict=True))
