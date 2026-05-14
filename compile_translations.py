import os
import polib

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
po_file_path = os.path.join(BASE_DIR, 'locale', 'en', 'LC_MESSAGES', 'django.po')
mo_file_path = os.path.join(BASE_DIR, 'locale', 'en', 'LC_MESSAGES', 'django.mo')

try:
    po = polib.pofile(po_file_path)
    po.save_as_mofile(mo_file_path)
    print(f"Successfully compiled translations to {mo_file_path}")
except Exception as e:
    print(f"Error compiling translations: {e}")
