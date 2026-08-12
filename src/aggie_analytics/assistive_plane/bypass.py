from __future__ import annotations

from pathlib import Path


ENDPOINT_OWNERS = {
    "api.openai.com": ("src/aggie_analytics/" + "openai" + "_assist/",),
    "api.openrouter.ai": ("src/aggie_analytics/assistive_plane/openrouter_backend.py", "tools/refresh_openrouter_model_catalog.py"),
    "api.cursor.com": ("src/aggie_analytics/assistive_plane/cursor_backend.py", "tools/refresh_cursor_catalog.py"),
    "localhost:11434": ("src/aggie_analytics/assistive_plane/ollama_backend.py",),
    "127.0.0.1:11434": ("src/aggie_analytics/assistive_plane/ollama_backend.py",),
}


def find_direct_endpoint_bypasses(root: Path) -> list[str]:
    findings: list[str] = []
    for path in sorted((root / "src").rglob("*.py")):
        relative = path.relative_to(root).as_posix()
        if relative == "src/aggie_analytics/assistive_plane/bypass.py":
            continue
        text = path.read_text(encoding="utf-8")
        for endpoint, owners in ENDPOINT_OWNERS.items():
            owned = relative in owners or any(relative.startswith(owner) for owner in owners if owner.endswith("/"))
            if endpoint in text and not owned:
                findings.append(f"DIRECT_PROVIDER_ENDPOINT_BYPASS:{relative}:{endpoint}")
    return findings
