import asyncio

from app.routers.home import health
from app.version import __distribution_version__, __version__


def test_health_exposes_owned_distribution_identity() -> None:
    assert __version__ == "5.4.1-awg31.1"
    assert __distribution_version__ == "1.0.4"
    assert asyncio.run(health()) == {
        "status": "ok",
        "product_version": "5.4.1-awg31.1",
        "managed_release": "v1.0.4",
        "schema_head": "pgawg0003",
    }
