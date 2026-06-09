from pathlib import Path


def pytest_ignore_collect(collection_path, config):
    """Prevent test fixtures from being collected as real tests."""
    fixture_root = Path(__file__).parent / "fixtures"
    try:
        collection_path.relative_to(fixture_root)
        return True
    except ValueError:
        return None
