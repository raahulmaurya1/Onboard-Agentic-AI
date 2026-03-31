from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.middleware.prefix_validation import PrefixValidationMiddleware
from app.api.auth_routes import router as auth_router
from app.api.onboarding_routes import router as onboarding_router
from app.api.review_routes import router as review_router
from app.api.ops_routes import router as ops_router
from app.api.decision_routes import router as decision_router
from app.api.face_routes import router as face_router
from app.api.risk_review_routes import router as risk_review_router
app = FastAPI(title="Bank Onboarding System API", openapi_version="3.0.2")

app.add_middleware(PrefixValidationMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api")
app.include_router(onboarding_router, prefix="/api")
app.include_router(review_router, prefix="/api")
app.include_router(ops_router, prefix="/api")
app.include_router(decision_router, prefix="/api")
app.include_router(face_router, prefix="/api/v1/face", tags=["Face Verification"])
app.include_router(risk_review_router, prefix="/api", tags=["Risk Review"])


