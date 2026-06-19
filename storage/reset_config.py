import json
from pathlib import Path

CONFIG_PATH = Path("./storage/config_ui.json")

with CONFIG_PATH.open("r", encoding="utf-8") as f:
    config = json.load(f)

# Remise à zéro des paramètres personnels
config["import_image_folder"] = ""

config["current_search"]["query"] = "DEFAULT"
config["current_search"]["generation"] = 0
config["current_search"]["index"] = 0
config["current_search"]["threshold"] = 0.5

config["current_image"] = 0

with CONFIG_PATH.open("w", encoding="utf-8") as f:
    json.dump(config, f, indent=4, ensure_ascii=False)

print("config.json réinitialisé.")