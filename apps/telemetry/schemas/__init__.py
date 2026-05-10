import json
from pathlib import Path

SCHEMA_DIR = Path(__file__).parent
_cache = {}


def get_schema(version: str) -> dict:
    """
    Load and cache a JSON schema by version string.
    Version '1.0' maps to v1_0.json on disk.

    Usage:
        schema = get_schema('1.0')
        schema = get_schema('1.1')

    Raises:
        ValueError: if no schema file exists for that version
    """
    if version not in _cache:
        # '1.0' → 'v1_0.json'  (dots replaced with underscores for Windows-safe filenames)
        filename = f"v{version.replace('.', '_')}.json"
        path = SCHEMA_DIR / filename

        if not path.exists():
            raise ValueError(
                f"Unknown schema version {version!r} — "
                f"expected file at {path}"
            )

        with open(path, encoding='utf-8') as f:
            _cache[version] = json.load(f)

    return _cache[version]