from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.db.base import AsyncSessionLocal
from sqlalchemy import select
from sqlalchemy.sql import func
from app.db.models.user import UserInitial
from app.db.models.session import OnboardingSession

class PrefixValidationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Always allow browser preflight requests to pass through to CORSMiddleware
        if request.method == "OPTIONS":
            return await call_next(request)
            
        # We only apply this check for secure downstream paths
        if request.url.path.startswith(("/api/v1/upload", "/api/intent", "/api/upload", "/api/confirm-documents", "/api/finalize-documents")):
            auth_header = request.headers.get("Authorization")
            if not auth_header:
                return JSONResponse(status_code=401, content={"detail": "Missing Authorization header"})
            
            # Robust extraction, handle both "Bearer <token>" or raw "<token>" safely
            token = auth_header.replace("Bearer ", "").strip()
            
            try:
                # Fetch DB User using the verified valid ULID token directly, bypassing 30-min dev-TTL
                async with AsyncSessionLocal() as db:
                    result = await db.execute(select(UserInitial).where(UserInitial.id == token))
                    user_obj = result.scalar_one_or_none()
                    
                    if not user_obj:
                        return JSONResponse(status_code=401, content={"detail": "Invalid native user session token."})
                        
                    if not user_obj.phone.startswith("+91"):
                        return JSONResponse(status_code=403, content={"detail": "Only phone numbers starting with +91 are permitted."})
                
                # Attach user data to request state for downstream use
                request.state.user = {"phone_number": user_obj.phone, "uid": user_obj.id, "email": user_obj.email}
                
            except Exception as e:
                # Log the exception locally if needed
                return JSONResponse(status_code=401, content={"detail": "Invalid authentication credentials"})

        response = await call_next(request)
        return response
