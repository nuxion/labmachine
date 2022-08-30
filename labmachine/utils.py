from nanoid import generate
from labmachine.defaults import NANO_ID_ALPHABET


def generate_random(size=10, strategy="nanoid", alphabet=NANO_ID_ALPHABET) -> str:
    """Default URLSafe id"""
    if strategy == "nanoid":
        return generate(alphabet=alphabet, size=size)
    raise NotImplementedError("Strategy %s not implemented", strategy)
