from fastapi import APIRouter, status
from fastapi.responses import HTMLResponse

from app.templates import render_template
from app.version import __distribution_version__, __version__
from config import dashboard_settings, template_settings

DASHBOARD_ROUTE = dashboard_settings.path.rstrip("/")
router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def base():
    return render_template(template_settings.home_page_template)


@router.get("/health", response_model=dict, status_code=status.HTTP_200_OK)
async def health():
    return {
        "status": "ok",
        "product_version": __version__,
        "managed_release": f"v{__distribution_version__}",
        "schema_head": "pgawg0003",
    }
