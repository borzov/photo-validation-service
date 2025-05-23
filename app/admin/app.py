"""
Administrative application for photo validation system management.
"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import os

# Create separate admin application
admin_app = FastAPI(
    title="Photo Validation Admin",
    description="Administrative panel for photo validation system management",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Mount static files if they exist
static_dir = "app/admin/static"
if os.path.exists(static_dir):
    admin_app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Import routes after app creation
from app.admin import routes

# Redirect from admin root to main admin page
@admin_app.get("/", include_in_schema=False)
async def admin_root():
    """Redirect to main admin page"""
    return RedirectResponse(url="/admin/", status_code=302) 