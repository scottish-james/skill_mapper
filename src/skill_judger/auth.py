"""
This gets the JWT token before any analytics run.
The JWT tokens lasts for 25hrs.
It's currently assumed that not analytics run will take over 25hrs.
"""
import os


def _read_env_credentials () -> tuple[str, str]:
    """Fetch CyberArk Account Name and Password from enviroment"""
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
    """
    Get JWT token
    """
