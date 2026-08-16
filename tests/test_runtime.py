import pytest

from bio_mystery_synth.models import Backend, ExecutionSpec
from bio_mystery_synth.runtime import ProtoRuntime


@pytest.mark.parametrize("sequence_type", ["rna", "protein"])
def test_unconstrained_sequence_generation(sequence_type: str) -> None:
    pytest.importorskip("proto_language")
    runtime = ProtoRuntime(ExecutionSpec(backend=Backend.LOCAL, local_device="cpu"))
    sequences = runtime.generate_sequences(sequence_type, count=2, length=12, seed=7)
    assert len(sequences) == 2
    assert all(len(sequence) == 12 for sequence in sequences)
