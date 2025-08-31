from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_ENV_FILE = Path(".envs").joinpath("dev.env")


class ABCBaseSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=DEFAULT_ENV_FILE if DEFAULT_ENV_FILE.exists() else None,
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    @classmethod
    def from_env_file(cls, env_path: str | Path) -> "ABCBaseSettings":
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