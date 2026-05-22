from fastapi.security import HTTPBearer

http_bearer = HTTPBearer(auto_error=False, scheme_name="HTTPBearer")