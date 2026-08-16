def fasta(records: list[tuple[str, str]]) -> str:
    return "".join(f">{name}\n{sequence}\n" for name, sequence in records)
