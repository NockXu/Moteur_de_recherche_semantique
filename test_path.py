import os
import sys

# Test du chemin depuis ui/widgets/Export/
file_path = 'ui/widgets/Export/Export.py'
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(file_path))))
print('File path:', file_path)
print('Project root:', project_root)
print('Project root exists:', os.path.exists(project_root))

# Test si common est trouvable
common_path = os.path.join(project_root, 'common')
print('Common path:', common_path)
print('Common exists:', os.path.exists(common_path))

# Ajout au sys.path
if project_root not in sys.path:
    sys.path.insert(0, project_root)
    print('Added to sys.path')

try:
    from common.Image_Classes.Image import Image
    print('✅ Import successful!')
except ImportError as e:
    print('❌ Import failed:', e)
