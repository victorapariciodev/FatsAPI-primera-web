"""Fixtures compartidas: datos semilla, cliente falso y TestClient con auth."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from fastapi_2026.api.db import get_db
from fastapi_2026.api.deps import get_current_user, get_optional_user
from fastapi_2026.core.config import settings
from fastapi_2026.main import app

from .fakes import FakeDB

PRODUCTS = [
    {
        "id": "p1",
        "name": "Camisa Oxford Azul",
        "slug": "camisa-oxford-azul",
        "description": "Camisa de algodon.",
        "category": "camisas",
        "price": 29.90,
        "currency": "USD",
        "image_url": None,
        "is_active": True,
        "created_at": "2026-01-01T00:00:00Z",
    },
    {
        "id": "p2",
        "name": "Franela Negra",
        "slug": "franela-negra",
        "description": None,
        "category": "franelas",
        "price": 19.50,
        "currency": "USD",
        "image_url": None,
        "is_active": True,
        "created_at": "2026-01-02T00:00:00Z",
    },
    {
        "id": "p3",
        "name": "Pantalon Cargo",
        "slug": "pantalon-cargo",
        "description": None,
        "category": "pantalones",
        "price": 39.00,
        "currency": "USD",
        "image_url": None,
        "is_active": False,
        "created_at": "2026-01-03T00:00:00Z",
    },
    {
        "id": "p4",
        "name": "Chaqueta Impermeable",
        "slug": "chaqueta-impermeable",
        "description": None,
        "category": "chaquetas",
        "price": 60.00,
        "currency": "USD",
        "image_url": None,
        "is_active": True,
        "created_at": "2026-01-04T00:00:00Z",
    },
]

VARIANTS = [
    {"id": "v1", "product_id": "p1", "size": "M", "color": "azul", "sku": "CAM-OXF-AZ-M", "stock": 8, "created_at": "1"},
    {"id": "v2", "product_id": "p1", "size": "S", "color": "azul", "sku": "CAM-OXF-AZ-S", "stock": 0, "created_at": "2"},
    {"id": "v3", "product_id": "p2", "size": "L", "color": "negro", "sku": "FRA-NEG-L", "stock": 3, "created_at": "3"},
    {"id": "v4", "product_id": "p3", "size": "32", "color": "verde", "sku": "PAN-CAR-32", "stock": 5, "created_at": "4"},
    {"id": "v5", "product_id": "p4", "size": "XL", "color": "grafito", "sku": "CHA-IMP-XL", "stock": 2, "created_at": "5"},
]

VIDEOS = [
    {
        "id": "vid1",
        "slug": "charla-fastapi-en-capas",
        "title": "Charla: FastAPI en capas",
        "description": "Como separar schemas, servicios y rutas.",
        "categoria": "charla",
        "video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "poster_url": None,
        "duration_label": "18:42",
        "is_active": True,
        "published_at": "2026-03-01T10:00:00Z",
    },
    {
        "id": "vid2",
        "slug": "taller-tailwind",
        "title": "Taller: tokens de diseño",
        "description": None,
        "categoria": "taller",
        "video_url": (
            f"https://{settings.supabase_url.split('//')[1].split('/')[0]}"
            "/storage/v1/object/public/videos/taller.mp4"
        ),
        "poster_url": None,
        "duration_label": "07:15",
        "is_active": True,
        "published_at": "2026-04-02T10:00:00Z",
    },
    {
        "id": "vid3",
        "slug": "demo-inactivo",
        "title": "Demo retirada",
        "description": None,
        "categoria": "demo",
        "video_url": "https://youtu.be/abcdefghijk",
        "poster_url": None,
        "duration_label": None,
        "is_active": False,
        "published_at": "2026-05-03T10:00:00Z",
    },
]


ORDERS = [
    {
        "id": "o1",
        "user_id": "u1",
        "status": "pending",
        "subtotal": 29.90,
        "shipping_cost": 5.00,
        "total": 34.90,
        "currency": "USD",
        "shipping_address": {"full_name": "Alex Mercer", "city": "Caracas"},
        "created_at": "2026-02-01T00:00:00Z",
    },
    {
        "id": "o2",
        "user_id": "u2",
        "status": "pending",
        "subtotal": 19.50,
        "shipping_cost": 5.00,
        "total": 24.50,
        "currency": "USD",
        "shipping_address": {"full_name": "Otro", "city": "Maracaibo"},
        "created_at": "2026-02-02T00:00:00Z",
    },
]

ORDER_ITEMS = [
    {
        "id": "oi1",
        "order_id": "o1",
        "variant_id": "v1",
        "product_name": "Camisa Oxford Azul",
        "size": "M",
        "color": "azul",
        "unit_price": 29.90,
        "quantity": 1,
        "line_total": 29.90,
    }
]


def seed() -> dict[str, list[dict[str, Any]]]:
    return {
        "products": PRODUCTS,
        "product_variants": VARIANTS,
        "carts": [{"id": "c1", "user_id": "u1"}],
        "cart_items": [],
        "orders": ORDERS,
        "order_items": ORDER_ITEMS,
        "videos": VIDEOS,
    }


@pytest.fixture
def db() -> FakeDB:
    base = FakeDB(seed())
    # La landing registra una visita en cada GET /. Sin este handler el fake
    # lanzaria AssertionError y la portada se caeria en los tests.
    base.rpc_handlers["register_landing_visit"] = lambda params: 42
    return base


@pytest.fixture
def user() -> dict[str, Any]:
    return {"sub": "u1", "app_metadata": {"role": "user"}, "email": "u1@test.dev"}


@pytest.fixture
def admin() -> dict[str, Any]:
    return {"sub": "u9", "app_metadata": {"role": "admin"}, "email": "admin@test.dev"}


@pytest.fixture
def client(db: FakeDB, user: dict[str, Any]):
    """TestClient autenticado como `user` y con la DB falsa inyectada.

    Se sobreescribe tambien `get_optional_user` porque las paginas HTML lo
    usan en vez del guardian estricto.
    """
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_optional_user] = lambda: user
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def admin_client(db: FakeDB, admin: dict[str, Any]):
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: admin
    app.dependency_overrides[get_optional_user] = lambda: admin
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def anon_client(db: FakeDB):
    """Sin overrides de auth: ejercita el guardian real."""
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
