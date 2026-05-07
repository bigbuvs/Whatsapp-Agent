from pathlib import Path

KNOWLEDGE_DIR = Path(__file__).parent.parent / "knowledge"
SUPPORTED_EXTENSIONS = {".txt", ".md", ".csv"}
MAX_CHARS_PER_FILE = 8000
MAX_TOTAL_CHARS = 24000


def load_knowledge() -> str:
    if not KNOWLEDGE_DIR.exists():
        return ""

    files = sorted(KNOWLEDGE_DIR.glob("*"))
    chunks = []
    total = 0

    for file in files:
        if file.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        if not file.is_file():
            continue

        try:
            content = file.read_text(encoding="utf-8", errors="ignore").strip()
            if not content:
                continue

            if len(content) > MAX_CHARS_PER_FILE:
                content = content[:MAX_CHARS_PER_FILE] + "\n[... archivo truncado ...]"

            chunks.append(f"### {file.name}\n{content}")
            total += len(content)

            if total >= MAX_TOTAL_CHARS:
                chunks.append("[Base de conocimiento truncada por límite de contexto]")
                break

        except Exception:
            continue

    return "\n\n".join(chunks)
