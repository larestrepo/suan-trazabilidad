from fastapi import APIRouter

from .endpoints import sandbox

api_router = APIRouter()
# api_router.include_router(kobo_projects.router, prefix="/kobo", tags=["Kobo"])
# api_router.include_router(db_data.router, prefix="/data", tags=["Data"])
# api_router.include_router(projects.router, prefix="/projects", tags=["Projects"])
api_router.include_router(sandbox.router, prefix="/sandbox", tags=["Sandbox"])
# api_router.include_router(qrdb.router, prefix="/qrdb", tags=["QRDB"])