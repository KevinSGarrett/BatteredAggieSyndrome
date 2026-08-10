from __future__ import annotations

import importlib.util
import unittest

from aggie_analytics.entities.resolution import normalize_name


HYPOTHESIS_AVAILABLE = importlib.util.find_spec("hypothesis") is not None

if HYPOTHESIS_AVAILABLE:
    from hypothesis import given, settings, strategies as st


class OpenSourcePropertyTests(unittest.TestCase):
    if HYPOTHESIS_AVAILABLE:
        @settings(max_examples=250, deadline=None)
        @given(st.text(max_size=256))
        def test_alias_normalization_is_deterministic_ascii_and_idempotent(self, value: str) -> None:
            normalized = normalize_name(value)
            self.assertEqual(normalized, normalize_name(value))
            self.assertEqual(normalized, normalize_name(normalized))
            self.assertEqual(normalized, normalized.strip())
            self.assertTrue(normalized.isascii())

        @settings(max_examples=100, deadline=None)
        @given(
            st.lists(
                st.from_regex(r"[A-Za-z0-9]{1,12}", fullmatch=True),
                min_size=1,
                max_size=8,
            ),
            st.sampled_from((" ", "-", "_", ".", " / ", " & ")),
        )
        def test_non_alphanumeric_separators_cannot_change_token_identity(
            self, tokens: list[str], separator: str
        ) -> None:
            self.assertEqual(
                " ".join(token.lower() for token in tokens),
                normalize_name(separator.join(tokens)),
            )
    else:
        def test_hypothesis_is_an_explicit_optional_test_dependency(self) -> None:
            self.skipTest("install the 'test' optional dependency")


if __name__ == "__main__":
    unittest.main()
