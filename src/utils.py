# src/utils.py
import re
import unicodedata

def slugify(value, allow_unicode=False):
    # ... (rest of the function code) ...
    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize('NFKC', value)
    else:
        value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = re.sub(r'[^\w\s-]', '', value.lower())
    value = re.sub(r'[-\s]+', '-', value).strip('-_')
    # Limit length for safety in file paths
    return value[:50] if value else "default-slug"