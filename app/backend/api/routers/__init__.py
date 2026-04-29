from app.backend.api.routers.auth import router as auth_router
from app.backend.api.routers.catalog import router as catalog_router
from app.backend.api.routers.root import router as root_router

routers = [root_router, catalog_router, auth_router]

__all__ = ["routers"]
