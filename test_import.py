#!/usr/bin/env python3
import sys
import os

# Configuration du chemin
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

print("=== Test d'import ===")
print(f"project_root: {project_root}")
print(f"sys.path: {sys.path[:3]}")

# Test 1: Import de ui
try:
    from ui import ImageSearchedContainer
    print("✅ Import ui.ImageSearchedContainer réussi")
except Exception as e:
    print(f"❌ Erreur import ui: {e}")

# Test 2: Import de AutoResearch
try:
    from ui.ImageSearchedContainer import AutoResearch
    print("✅ Import AutoResearch réussi")
    print(f"AutoResearch: {AutoResearch}")
except Exception as e:
    print(f"❌ Erreur import AutoResearch: {e}")
    import traceback
    traceback.print_exc()

# Test 3: Import direct
try:
    import ui.ImageSearchedContainer.autoResearch
    print("✅ Import direct réussi")
except Exception as e:
    print(f"❌ Erreur import direct: {e}")

# Test 4: Vérification du module
try:
    import importlib
    spec = importlib.util.find_spec("ui.ImageSearchedContainer.autoResearch")
    if spec:
        print(f"✅ Module trouvé: {spec.name}")
        print(f"  Origin: {spec.origin}")
    else:
        print("❌ Module non trouvé avec find_spec")
except Exception as e:
    print(f"❌ Erreur find_spec: {e}")
