"""Tests for :mod:`patternforge.engine.bitset`."""

from patternforge.engine import bitset


def test_bitset_operations() -> None:
    base = bitset.make_bitset([0, 2, 4])
    assert bitset.count_bits(base) == 3
    indexes = list(bitset.iter_indexes(base))
    assert indexes == [0, 2, 4]

    mask = bitset.make_bitset([1, 3])
    combined = bitset.or_bits(base, mask)
    assert bitset.count_bits(combined) == 5

    cleared = bitset.clear_bits(combined, bitset.make_bitset([2]))
    assert list(bitset.iter_indexes(cleared)) == [0, 1, 3, 4]

    toggled = bitset.xor_bits(cleared, bitset.make_bitset([0, 4]))
    assert list(bitset.iter_indexes(toggled)) == [1, 3]

    assert bitset.and_bits(toggled, mask) == mask
    assert bitset.set_bits(0, mask) == mask
