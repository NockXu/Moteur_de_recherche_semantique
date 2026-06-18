import json
from pathlib import Path
from typing import Optional, Dict, Any

config_path = Path("./storage/config_ui.json")

# créer le dossier si absent
config_path.parent.mkdir(parents=True, exist_ok=True)

def load_config() -> dict[str, Any]:
    """Charge la config existante ou retourne un dict vide."""
    if not config_path.exists():
        return {}

    try:
        with open(config_path, encoding="utf-8") as f:
            return json.load(f)

    except Exception as e:
        print(f"Erreur lecture config: {e}")
        return {}

def load_from_config(key: str) -> Any | None:
    """Charge une valeur depuis la config."""
    config = load_config()
    return config.get(key)

def save_in_config(key: str, value: Any):
    """Sauvegarde une valeur dans la config."""
    config = load_config()
    config[key] = value
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)
