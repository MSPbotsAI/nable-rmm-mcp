from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    mcp_http_port: int = 8080
    mcp_http_host: str = "0.0.0.0"

    # N-able RMM (N-sight) has 11 regional servers; this default can be
    # overridden per deployment via env var, or per-request via the
    # X-Nable-Server header for gateways serving tenants across regions.
    nable_base_url: str = "https://www.am.remote.management"


def get_settings() -> Settings:
    return Settings()
