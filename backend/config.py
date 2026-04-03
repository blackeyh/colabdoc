import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILES = ("env", ".env")


def load_project_env() -> None:
    for filename in ENV_FILES:
        env_path = PROJECT_ROOT / filename
        if env_path.is_file():
            load_dotenv(env_path, override=False)


def get_env(name: str, default: str | None = None) -> str | None:
    load_project_env()
    return os.getenv(name, default)


def require_env(name: str) -> str:
    value = get_env(name)
    if value:
        return value
    expected_files = ", ".join(str(PROJECT_ROOT / filename) for filename in ENV_FILES)
    raise RuntimeError(
        f"Missing required environment variable {name}. "
        f"Define it in one of: {expected_files}"
    )
