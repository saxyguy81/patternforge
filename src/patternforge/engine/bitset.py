"""Integer bitset utilities."""
from __future__ import annotations

import sys
from collections.abc import Iterable


def make_bitset(indexes: Iterable[int]) -> int:
    value = 0
    for idx in indexes:
        value |= 1 << idx
    return value


# Optimize bit counting based on Python version (cached at module load time)
if sys.version_info >= (3, 10):
    def count_bits(value: int) -> int:
        """Count the number of set bits using native int.bit_count() (Python 3.10+)."""
        return value.bit_count()
else:
    def count_bits(value: int) -> int:
        """Count the number of set bits using bin().count('1') (Python 3.9)."""
        return bin(value).count('1')


def iter_indexes(value: int) -> Iterable[int]:
    index = 0
    while value:
        if value & 1:
            yield index
        value >>= 1
        index += 1


def clear_bits(base: int, remove: int) -> int:
    return base & ~remove


def set_bits(base: int, add: int) -> int:
    return base | add


def and_bits(a: int, b: int) -> int:
    return a & b


def or_bits(a: int, b: int) -> int:
    return a | b


def xor_bits(a: int, b: int) -> int:
    return a ^ b
