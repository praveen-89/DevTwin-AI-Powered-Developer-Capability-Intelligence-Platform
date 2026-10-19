"""
DevTwin Mining Engine — Configuration Constants and Resource Budgets
"""

# Archive safety limits
DEFAULT_MAX_ARCHIVE_DOWNLOAD_BYTES = 50 * 1024 * 1024  # 50 MB
DEFAULT_MAX_ARCHIVE_MEMBERS = 10_000
DEFAULT_MAX_ARCHIVE_TOTAL_UNCOMPRESSED_BYTES = 250 * 1024 * 1024  # 250 MB
DEFAULT_MAX_ARCHIVE_SINGLE_FILE_BYTES = 10 * 1024 * 1024  # 10 MB

# File tree traversal budgets
MAX_FILES_INSPECTED = 5_000
MAX_TOTAL_SOURCE_BYTES = 50 * 1024 * 1024  # 50 MB
MAX_SINGLE_SOURCE_FILE_BYTES = 2 * 1024 * 1024  # 2 MB per file for AST parsing
MAX_MANIFEST_FILE_BYTES = 512 * 1024  # 512 KB per manifest
MAX_DEPENDENCIES_PER_MANIFEST = 300
MAX_AST_FILES_PARSED = 500

# Directory exclusion policy (case-insensitive segments)
EXCLUDED_DIRECTORIES = frozenset({
    # Version control
    ".git",
    ".svn",
    ".hg",
    # Dependencies
    "node_modules",
    "vendor",
    "bower_components",
    "packages",
    "pods",
    # Python virtual environments and caches
    "venv",
    ".venv",
    "env",
    ".env",
    "virtualenv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    ".nox",
    # Build outputs
    "dist",
    "build",
    "out",
    "target",
    "bin",
    "obj",
    ".next",
    ".nuxt",
    ".output",
    "bundle",
    "wheels",
    # IDEs and tooling
    ".idea",
    ".vscode",
    ".vs",
    ".settings",
    # Coverage and doc builds
    "coverage",
    "htmlcov",
    ".coverage",
    "site",
    "_build",
})

# Extension to language taxonomy mapping
EXTENSION_TO_LANGUAGE = {
    ".py": "Python",
    ".pyi": "Python",
    ".js": "JavaScript",
    ".mjs": "JavaScript",
    ".cjs": "JavaScript",
    ".jsx": "JavaScript (React)",
    ".ts": "TypeScript",
    ".mts": "TypeScript",
    ".cts": "TypeScript",
    ".tsx": "TypeScript (React)",
    ".rs": "Rust",
    ".go": "Go",
    ".java": "Java",
    ".c": "C",
    ".h": "C",
    ".cpp": "C++",
    ".hpp": "C++",
    ".cc": "C++",
    ".cxx": "C++",
    ".cs": "C#",
    ".rb": "Ruby",
    ".php": "PHP",
    ".swift": "Swift",
    ".kt": "Kotlin",
    ".kts": "Kotlin",
    ".scala": "Scala",
    ".html": "HTML",
    ".htm": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".sass": "Sass",
    ".less": "Less",
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".toml": "TOML",
    ".xml": "XML",
    ".md": "Markdown",
    ".markdown": "Markdown",
    ".sql": "SQL",
    ".sh": "Shell",
    ".bash": "Shell",
    ".zsh": "Shell",
    ".dockerfile": "Dockerfile",
}

# Special file names to language mapping (case-insensitive)
SPECIAL_FILENAMES = {
    "dockerfile": "Dockerfile",
    "makefile": "Makefile",
    "cmakelists.txt": "CMake",
    "gemfile": "Ruby",
    "rakefile": "Ruby",
}
