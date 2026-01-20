from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.config import CONFIG

# auto_error=False allows us to handle the missing header manually if we want,
# or to support cases where auth is optional (e.g. if no key is set in config).
security = HTTPBearer(auto_error=False)

async def verify_api_key(credentials: HTTPAuthorizationCredentials = Security(security)):
    """
    Verifies the API key from the Authorization header (Bearer token).
    If 'api_key' is set in config.conf [Auth] section, it enforces authentication.
    If 'api_key' is empty or missing, it allows access without auth.
    """
    # Reload config to get the latest values (optional, but good if config changes)
    # For performance, we might rely on the global CONFIG, but let's use the one imported.
    # Note: CONFIG is loaded at module level in app.config. If we want hot-reload of config,
    # we might need to call load_config() again or rely on the app restart.
    # Assuming app restart for config changes for now.
    
    expected_api_key = CONFIG.get("Auth", "api_key", fallback="").strip()
    
    # If no API key is configured in the file, we assume authentication is disabled.
    if not expected_api_key:
        return True
        
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    if credentials.credentials != expected_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return True
