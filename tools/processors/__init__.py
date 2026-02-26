"""Processors module initialization."""
# Document processors for different source types
#
# Lazy imports to avoid pulling in heavy deps (pymupdf, bs4) on simple imports.


def __getattr__(name: str):
    _map = {
        "seed_from_yaml": ("tools.processors.yaml_seeder", "seed_from_yaml"),
        "seed_to_chromadb": ("tools.processors.yaml_seeder", "seed_to_chromadb"),
        "process_pdf": ("tools.processors.fsm", "process_pdf"),
        "process_directory": ("tools.processors.fsm", "process_directory"),
        "process_forum_file": ("tools.processors.forum", "process_forum_file"),
        "process_forum_directory": ("tools.processors.forum", "process_forum_directory"),
        "process_nhtsa": ("tools.processors.nhtsa", "process_nhtsa"),
        "process_parts": ("tools.processors.parts", "process_parts"),
        "process_web_articles": ("tools.processors.web_article", "process_web_articles"),
    }
    if name in _map:
        mod_name, attr = _map[name]
        import importlib
        mod = importlib.import_module(mod_name)
        return getattr(mod, attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "seed_from_yaml",
    "seed_to_chromadb",
    "process_pdf",
    "process_directory",
    "process_forum_file",
    "process_forum_directory",
    "process_nhtsa",
    "process_parts",
    "process_web_articles",
]
