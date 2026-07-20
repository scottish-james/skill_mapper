"""
This gets the JWT token before any analytics run.
The JWT tokens lasts for 25hrs.
It's currently assumed that not analytics run will take over 25hrs.
"""
import os
from pathlib import Path

import requests
import yaml
from dotenv import load_dotenv

load_dotenv()

CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "model_config.yaml"


class AuthError(Exception):
    """raise when authentication fails or credentials are missing"""


def _read_jwt_url(config_path: Path = CONFIG_PATH) -> str:
    """Fetch the JWT auth URL: GENAI_GATEWAY_JWT env var (e.g. from .env) takes
    priority for fast local testing, falling back to model_config.yaml."""
    env_url = os.environ.get("GENAI_GATEWAY_JWT")
    if env_url:
        return env_url

    with open(config_path) as f:
        config = yaml.safe_load(f)

    jwt_url = config.get("auth", {}).get("jwt_url")
    if not jwt_url:
        raise AuthError(f"Missing auth.jwt_url in {config_path}")
    return jwt_url

def _read_env_credentials () -> tuple[str, str]:
    """Fetch CyberArk Acount Name and Password from enviroment"""
    service_account = os.environ.get("CYBERARK_SERVICE_ACCOUNT")
    password = os.environ.get("CYBERARK_PASSWORD")
    if not service_account or not password:
        raise AuthError(
            """
            Missing Credientials: Set CYBERARK_SERVICE_ACCOUNT and CYBERARK_PASSWORD
            in the eviroment (e.g. via a .env file).
            """
        )
    return service_account, password

def get_jwt(auth_url, service_account, password):
    """Get JWT token"""
    response = requests.post(auth_url, auth=(service_account, password))

    if response.status_code == 200:
        token = response.text.strip()
        return token

    raise AuthError(
        f"Failed to get JWT. Status {response.status_code}, response: {response.text}"
    )


def authenticate() -> str:
    """Run the full auth flow and return a JWT token"""
    auth_url = _read_jwt_url()
    service_account, password = _read_env_credentials()
    return get_jwt(auth_url, service_account, password)

