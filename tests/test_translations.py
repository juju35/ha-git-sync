"""Every translation has exactly the keys and placeholders of the English one."""

from __future__ import annotations

import json
import re
import string
from pathlib import Path

import pytest

TRANSLATIONS = Path(__file__).parent.parent / "custom_components" / "git_sync" / "translations"
LANGUAGES = ["de", "es", "fr", "it", "nl", "pl", "pt", "pt-BR", "sr", "sr-Latn"]


def _flatten(data: dict, prefix: str = "") -> dict[str, str]:
    flat: dict[str, str] = {}
    for key, value in data.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            flat.update(_flatten(value, path))
        else:
            flat[path] = value
    return flat


def _load(language: str) -> dict[str, str]:
    return _flatten(json.loads((TRANSLATIONS / f"{language}.json").read_text(encoding="utf-8")))


def _placeholders(text: str) -> set[str]:
    return {name for _, name, _, _ in string.Formatter().parse(text) if name is not None}


def test_all_languages_are_tested():
    """A new translations/*.json file is added to LANGUAGES."""
    assert sorted(p.stem for p in TRANSLATIONS.glob("*.json")) == sorted(["en", *LANGUAGES])


@pytest.mark.parametrize("language", LANGUAGES)
def test_translation_parity(language: str):
    """Same keys as en.json, same placeholders in each string, nothing empty."""
    english, other = _load("en"), _load(language)
    assert sorted(other) == sorted(english)
    for key, text in english.items():
        assert other[key].strip(), key
        assert _placeholders(other[key]) == _placeholders(text), key


@pytest.mark.parametrize("language", ["en", *LANGUAGES])
def test_single_repository_actions_say_so(language: str):
    """generate_ssh_key and generate_message use the first repository without config_entry_id, not all of them."""
    strings = _load(language)
    field = "services.{}.fields.config_entry_id.description"
    assert strings[field.format("generate_ssh_key")] == strings[field.format("generate_message")]


# Serbian Cyrillic letter by letter, then its Latin spelling (љ, њ and џ take two letters).
_SERBIAN = "аaбbвvгgдdђđеeжžзzиiјjкkлlљljмmнnњnjоoпpрrсsтtћćуuфfхhцcчčџdžшš"
_TO_LATIN = dict(re.findall(r"([а-џ])([^а-џ]+)", _SERBIAN))
_TO_LATIN |= {c.upper(): lat.capitalize() for c, lat in _TO_LATIN.items()}


def test_serbian_scripts_match():
    """sr-Latn is sr written in Latin script, letter for letter, with no Cyrillic left."""
    cyrillic, latin = _load("sr"), _load("sr-Latn")
    for key, text in cyrillic.items():
        assert "".join(_TO_LATIN.get(ch, ch) for ch in text) == latin[key], key
        assert not re.search(r"[\u0400-\u04ff]", latin[key]), key


def test_serbian_cyrillic_keeps_latin_for_names_only():
    """The Latin words left in sr (Git, commit, push, JSON, Home Assistant…) are names and terms taken from en.json."""
    english = " ".join(_load("en").values()).lower()
    for key, text in _load("sr").items():
        for word in re.findall(r"[A-Za-z]+", text):
            assert word.lower() in english, f"{key}: {word}"
