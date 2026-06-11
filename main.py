"""
IntelliDesk - AI-Based IT Helpdesk Automation Platform
Main Application Entry Point

Tech Stack:
    - Backend: FastAPI (Python)
    - Frontend: Jinja2 + Bootstrap 5
    - Database: MySQL (SQLAlchemy ORM)
    - AI/NLP: HuggingFace Transformers (zero-shot classification)
    - Auth: JWT tokens with bcrypt password hashing

Run:
    uvicorn main:app --reload --port 8000
"""

from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from config import engine, Base
from routes import auth_routes, ticket_routes, chat_routes, admin_routes
from auth import get_current_user_optional
from models import User

# Create FastAPI app
app = FastAPI(
    title="IntelliDesk",
    description="AI-Based IT Helpdesk Automation Platform",
    version="1.0.0"
)

# Mount static files (CSS, JS, images)
app.mount("/static", StaticFiles(directory="static"), name="static")


# ================= FIX: NO-CACHE MIDDLEWARE LAYER =================
# Forces the browser to evaluate the authentication state on every tab switch
@app.middleware("http")
async def add_no_cache_headers(request: Request, call_next):
    response = await call_next(request)
    
    # Apply no-cache headers to dynamic pages so user/admin sessions don't bleed
    if not request.url.path.startswith("/static"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        
    return response
# =================================================================


# Create database tables on startup
@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    print("[IntelliDesk] Database tables created/verified.")
    print("[IntelliDesk] Server is running at http://localhost:8000")

# Include route modules
app.include_router(auth_routes.router)
app.include_router(ticket_routes.router)
app.include_router(chat_routes.router)
app.include_router(admin_routes.router)


# Home / welcome page
@app.get("/")
async def root(
    request: Request,
    current_user: User = Depends(get_current_user_optional)
):
    """Show a separate IntelliDesk welcome page instead of redirecting to dashboard."""
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)

    templates = Jinja2Templates(directory="templates")
    return templates.TemplateResponse(
        "home.html",
        {
            "request": request,
            "user": current_user
        }
    )


# Custom error handlers
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    templates = Jinja2Templates(directory="templates")
    return templates.TemplateResponse(
        "error.html",
        {
            "request": request,
            "code": 404,
            "message": "Page not found"
        },
        status_code=404
    )

@app.exception_handler(403)
async def forbidden_handler(request: Request, exc):
    templates = Jinja2Templates(directory="templates")
    return templates.TemplateResponse(
        "error.html",
        {
            "request": request,
            "code": 403,
            "message": "Access denied"
        },
        status_code=403
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

