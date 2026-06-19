# i18n.py
import ast
from pathlib import Path
from typing import Dict, List
import json
import sys
import os

from ui import load_config, save_in_config

SOURCE_LANG = "fr"

_current_lang: str = SOURCE_LANG
_translations: dict[str, dict[str, str]] = {}


# ── Runtime ────────────────────────────────────────────────────────────────

def init_translations(lang: str) -> None:
    """Initialize the translation system on application startup.

    Args:
        lang (str): Target locale language code identifier (e.g., "en", "fr").

    """
    global _current_lang, _translations
    _current_lang = lang
    _translations_path : str = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),  load_config().get("translations", {}).get("path", ""))
    if _translations_path:
        with open(_translations_path, encoding="utf-8") as f:
            _translations = json.load(f)
    else:
        _translations = {}


def set_language(lang: str) -> None:
    """Change the current active runtime language code context.

    Note:
        Requires triggering a manual retranslate() call across active view widgets.

    Args:
        lang (str): The new target language locale identifier code.

    """
    global _current_lang
    _current_lang = lang


def tr(text: str) -> str:
    """Translate a given source text literal token into the active runtime locale.

    Args:
        text (str): Raw translation key identifier string.

    Returns:
        str: Translated value text map, or the original literal string as a fallback.

    """
    entry = _translations.get(text)
    if entry:
        translated = entry.get(_current_lang, "")
        if translated:
            return translated
    return text  # fallback : texte original


# ── Extraction ─────────────────────────────────────────────────────────────

def _extract_tr_calls(source: str) -> list[str]:
    """Parse python code using Abstract Syntax Trees to locate absolute tr() function arguments.

    Args:
        source (str): Raw file content text stream to scan.

    Returns:
        list[str]: Collection array tracking unique string literal arguments isolated within tr() calls.

    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    strings: list[str] = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "tr"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
            and node.args[0].value.strip()
        ):
            strings.append(node.args[0].value)
    return strings


def extract_translations(
    project_root: str,
    language_list: list[str],
) -> dict[str, dict[str, str]]:
    """Scan all project files, discover active tr() invocations, and synchronize the target mapping schema.

    Maintains safe synchronization behaviors:
    - Never overwrites pre-existing translation values.
    - Preserves orphan tracking keys discovered in previous extractions.

    Args:
        project_root (str): Bounding absolute base directory target to parse recursively.
        language_list (list[str]): Target translation locale tags array to update.

    Returns:
        dict[str, dict[str, str]]: The updated, fully integrated translation schema dictionary layout.

    """
    translations_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),  load_config().get("translations", {}).get("path", ""))
    with open(translations_path, encoding="utf-8") as f:
        translations = json.load(f)

    added: list[str] = []
    already_present: int = 0

    for file in sorted(Path(project_root).rglob("*.py")):
        try:
            source = file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            print(f"{e}")
            continue

        for text in _extract_tr_calls(source):
            if text in translations:
                for lang in language_list:
                    if lang not in translations[text]:
                        translations[text][lang] = text if lang == SOURCE_LANG else ""
                already_present += 1
            else:
                translations[text] = {
                    lang: (text if lang == SOURCE_LANG else "")
                    for lang in language_list
                }
                added.append(text)

    # Sauvegarder les traductions mises à jour
    with open(translations_path, "w", encoding="utf-8") as f:
        json.dump(translations, f, indent=4, ensure_ascii=False)

    # Rapport
    missing = [
        key for key, langs in translations.items()
        if any(v == "" for lang, v in langs.items() if lang != SOURCE_LANG)
    ]
    for key in added:
        print(f"  + {key!r}")
    for key in missing:
        print(f"  ? {key!r} → {translations[key]}")

    return translations