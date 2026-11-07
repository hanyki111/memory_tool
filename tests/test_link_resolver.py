"""Wiki link targets resolve the way Obsidian reads them."""

import pytest

from memory_tool.core.connections import LinkResolver

MODULES = [
    "principles/core-principles",
    "principles/fp",
    "tools/core",
    "a/shared",
    "b/shared",
    "a/deep/topic",
    "게임 분석/니케",
]


@pytest.fixture
def resolver():
    return LinkResolver(MODULES)


@pytest.mark.parametrize(
    "target, source, expected",
    [
        ("tools/core", "principles/fp", "tools/core"),          # full path
        ("core-principles", "principles/fp", "principles/core-principles"),
        ("core", "principles/fp", "tools/core"),               # name, anywhere
        ("deep/topic", "tools/core", "a/deep/topic"),          # path suffix
        ("니케", "tools/core", "게임 분석/니케"),
        ("tools\core", "principles/fp", "tools/core"),        # either separator
        ("core-principles.md", "principles/fp", "principles/core-principles"),
        ("./core-principles", "principles/fp", "principles/core-principles"),
        ("../tools/core", "principles/fp", "tools/core"),
        ("shared", "a/deep/topic", "a/shared"),                # nearest wins
    ],
)
def test_resolves(resolver, target, source, expected):
    assert resolver.resolve(target, source) == expected


def test_a_name_two_modules_share_is_ambiguous_from_elsewhere(resolver):
    assert resolver.resolve("shared", "tools/core") is None
    assert resolver.candidates("shared", "tools/core") == ["a/shared", "b/shared"]


def test_a_partial_name_does_not_match(resolver):
    # "ore" is the end of "core" but not a whole path segment.
    assert resolver.candidates("ore", "principles/fp") == []


def test_a_missing_target_resolves_to_nothing(resolver):
    assert resolver.candidates("missing", "principles/fp") == []
