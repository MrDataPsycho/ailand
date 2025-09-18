from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from loguru import logger


DEFAULT_ENV_PATH = Path(".envs")
DEFAULT_ENV_FILE_CANDIDATES = [
    DEFAULT_ENV_PATH.joinpath("local.env"),
    DEFAULT_ENV_PATH.joinpath("dev.env"),
]


def find_env_file_if_exists() -> Path | None:
        """
        Check for the existence of environment files in the default locations.
        Returns the first found env file path or None if none exist.
        """
        for env_path in DEFAULT_ENV_FILE_CANDIDATES:
            if env_path.exists():
                logger.info(f"Found env file: {env_path}")
                return env_path
        logger.info("Loading settings from System Environment")
        return None


class ABCBaseSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=find_env_file_if_exists(),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    @classmethod
    def from_env_file(cls, env_path: str | Path) -> "ABCBaseSettings":
        """
        Load settings from a specific environment file.
        Raises FileNotFoundError if the file does not exist.
        Args:
            env_path: Path to the .env file to load settings from.
        """
        env_path = Path(env_path)
        if not env_path.exists():
            raise FileNotFoundError(f"Env file {env_path} does not exist.")

        class CustomSettings(cls):  # dynamically override model_config
            model_config = SettingsConfigDict(
                env_file=env_path,
                env_file_encoding="utf-8",
                extra="ignore",
                case_sensitive=False,
            )

        return CustomSettings()
    

if __name__ == "__main__":
    settings = ABCBaseSettings()