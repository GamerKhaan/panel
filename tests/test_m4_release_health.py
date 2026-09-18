import asyncio

from app.routers.home import health


def test_health_exposes_managed_release_identity() -> None:
    assert asyncio.run(health()) == {
        "status": "ok",
        "managed_release": "v5.4.1-awg31-rc.4",
        "schema_head": "pgawg0003",
    }
