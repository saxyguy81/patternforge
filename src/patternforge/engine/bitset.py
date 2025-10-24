"""Integer bitset utilities."""
from __future__ import annotations

from collections.abc import Iterable


def make_bitset(indexes: Iterable[int]) -> int:
    value = 0
    for idx in indexes:
        value |= 1 << idx
    return value


def full_bitset(count: int) -> int:
    if count >= 63:
        return (1 << count) - 1
    return (1 << count) - 1


def count_bits(value: int) -> int:
    return value.bit_count()


def iter_indexes(value: int) -> Iterable[int]:
    index = 0
    while value:
        if value & 1:
            yield index
        value >>= 1
        index += 1


def mask_for_length(length: int) -> int:
    if length >= 63:
        return (1 << length) - 1
    return (1 << length) - 1


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
