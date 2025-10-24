"""Tokenization tests."""

from codex.engine import tokens


def test_tokenize_classchange() -> None:
    sample = "abc123_DEF"
    result = tokens.tokenize(sample, splitmethod="classchange", min_token_len=2)
    assert [tok.value for tok in result] == ["abc", "123", "def"]
    assert [tok.index for tok in result] == [0, 1, 3]


def test_iter_tokens_sequence() -> None:
    items = ["alpha/beta", "gamma"]
    it = list(tokens.iter_tokens(items, splitmethod="classchange", min_token_len=3))
    assert it
    indexes = {idx for idx, _ in it}
    assert indexes == {0, 1}
