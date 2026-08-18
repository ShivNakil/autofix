from pathlib import Path


IGNORED_DIRECTORIES = {
    ".git", ".venv", "venv", "__pycache__", ".pytest_cache",
    "node_modules", ".mypy_cache", ".ruff_cache", "dist", "build",
    ".next", "coverage"
}

SOURCE_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".go", ".rs",
    ".cpp", ".c", ".h", ".hpp", ".cs", ".rb", ".php"
}

IMPORTANT_FILES = {
    "README.md", "README.rst", "pyproject.toml", "requirements.txt",
    "setup.py", "package.json", "pom.xml", "build.gradle",
    "go.mod", "Cargo.toml"
}


def list_files(repository_path: str) -> list[str]:
    root = Path(repository_path)
    files = []

    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in IGNORED_DIRECTORIES for part in path.parts):
            continue
        files.append(str(path.relative_to(root)).replace("\\", "/"))

    return sorted(files)


def get_repository_structure(repository_path: str, max_files: int = 800) -> str:
    files = list_files(repository_path)

    if len(files) > max_files:
        files = files[:max_files]

    return "\n".join(files)


def candidate_source_files(repository_path: str) -> list[str]:
    root = Path(repository_path)
    result = []

    for relative in list_files(repository_path):
        path = root / relative
        if path.name in IMPORTANT_FILES or path.suffix.lower() in SOURCE_EXTENSIONS:
            result.append(relative)

    return result


def search_repository(
    repository_path: str,
    terms: list[str],
    max_matches: int = 80,
) -> list[str]:
    root = Path(repository_path)
    matches = []

    normalized_terms = [t.lower() for t in terms if t.strip()]

    for relative in candidate_source_files(repository_path):
        if len(matches) >= max_matches:
            break

        path = root / relative

        try:
            text = path.read_text(
                encoding="utf-8",
                errors="ignore",
            )
        except OSError:
            continue

        lines = text.splitlines()

        for line_number, line in enumerate(lines, 1):
            lowered = line.lower()
            if any(term in lowered for term in normalized_terms):
                matches.append(
                    f"{relative}:{line_number}: {line[:240]}"
                )
                if len(matches) >= max_matches:
                    break

    return matches
