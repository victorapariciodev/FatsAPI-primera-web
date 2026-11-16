"""Logica de catalogo: consultas publicas y administracion de productos."""

from __future__ import annotations

import math
import re
import unicodedata
from decimal import Decimal
from typing import Any

from supabase import Client

from fastapi_2026.core.exceptions import ConflictError, NotFoundError

PRODUCT_SELECT = "*, product_variants(*)"
_SIZE_ORDER = {"XS": 0, "S": 1, "M": 2, "L": 3, "XL": 4, "XXL": 5}


def _slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-") or "producto"


def _to_db_value(value: Any) -> Any:
    """postgrest-py serializa con json.dumps: Decimal no es serializable."""
    return str(value) if isinstance(value, Decimal) else value


def _sort_variants(variants: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        variants,
        key=lambda v: (
            _SIZE_ORDER.get(str(v.get("size", "")).upper(), 99),
            str(v.get("size", "")),
            str(v.get("color", "")),
        ),
    )


def _normalize_product(row: dict[str, Any]) -> dict[str, Any]:
    data = dict(row)
    data["variants"] = _sort_variants(data.get("product_variants") or [])
    data.pop("product_variants", None)
    return data


class ProductService:
    def __init__(self, db: Client) -> None:
        self.db = db

    @staticmethod
    def _order_for(sort: str) -> dict[str, Any]:
        """Traduce el parametro de ordenamiento a un order() de PostgREST.

        Lista blanca cerrada: el cliente nunca inyecta nombre de columna.
        """
        return {
            "price_asc": {"column": "price", "desc": False},
            "price_desc": {"column": "price", "desc": True},
            "newest": {"column": "created_at", "desc": True},
        }.get(sort, {"column": "created_at", "desc": True})

    # ------------------------------------------------------------------
    # Lecturas
    # ------------------------------------------------------------------
    def list_products(
        self,
        *,
        category: str | None = None,
        search: str | None = None,
        size: str | None = None,
        in_stock: bool = False,
        min_price: float | None = None,
        max_price: float | None = None,
        sort: str = "newest",
        page: int = 1,
        page_size: int = 20,
        include_inactive: bool = False,
    ) -> dict[str, Any]:
        query = self.db.table("products").select(PRODUCT_SELECT, count="exact")

        # El catalogo publico NUNCA muestra productos desactivados.
        # El panel admin si, para poder reactivarlos.
        if not include_inactive:
            query = query.eq("is_active", True)

        if category:
            query = query.eq("category", category)

        # Busqueda (nombre del producto o SKU de la variante), talla y
        # disponibilidad viven en product_variants: PostgREST no permite
        # filtrar el recurso padre por columnas del recurso embebido.
        # Se resuelven en dos pasos y se INTERSECTAN en memoria para aplicar
        # un solo .in_("id", ...). Aplicar dos veces el mismo filtro deja la
        # semantica en manos de como PostgREST deduplica parametros repetidos.
        # Trade-off asumido: se trae la lista de ids coincidentes, barato en un
        # catalogo de MVP. Si crece a decenas de miles, esto se mueve a un
        # indice trgm/GIN o a una RPC con SQL.
        allowed_ids: set[str] | None = None

        if search:
            term = f"%{search}%"
            name_rows = (
                self.db.table("products")
                .select("id")
                .ilike("name", term)
                .execute()
                .data
                or []
            )
            sku_rows = (
                self.db.table("product_variants")
                .select("product_id")
                .ilike("sku", term)
                .execute()
                .data
                or []
            )
            allowed_ids = {row["id"] for row in name_rows} | {
                row["product_id"] for row in sku_rows
            }

        if min_price is not None:
            query = query.gte("price", min_price)
        if max_price is not None:
            query = query.lte("price", max_price)

        if size or in_stock:
            variant_query = self.db.table("product_variants").select("product_id")
            if size:
                # El chip de talla solo ofrece tallas comprables: si la talla
                # existe pero esta agotada, el producto no debe aparecer al
                # filtrar por ella (seria un callejon sin salida para el
                # usuario: entra al detalle y no puede comprar).
                variant_query = variant_query.eq("size", size.upper()).gt("stock", 0)
            if in_stock:
                variant_query = variant_query.gt("stock", 0)

            variant_rows = variant_query.execute().data or []
            variant_ids = {row["product_id"] for row in variant_rows}
            allowed_ids = (
                variant_ids if allowed_ids is None else allowed_ids & variant_ids
            )

        if allowed_ids is not None:
            if not allowed_ids:
                return {
                    "items": [],
                    "total": 0,
                    "page": page,
                    "page_size": page_size,
                    "pages": 0,
                }
            query = query.in_("id", list(allowed_ids))

        start = (page - 1) * page_size
        response = query.order(**self._order_for(sort)).range(
            start, start + page_size - 1
        ).execute()
        total = response.count or 0

        return {
            "items": [_normalize_product(row) for row in response.data or []],
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": math.ceil(total / page_size) if total else 0,
        }

    def get_product(self, product_id: str, *, include_inactive: bool = False) -> dict[str, Any]:
        query = self.db.table("products").select(PRODUCT_SELECT).eq("id", product_id)
        if not include_inactive:
            query = query.eq("is_active", True)

        rows = query.limit(1).execute().data or []
        if not rows:
            raise NotFoundError("El producto no existe o no esta disponible.")
        return _normalize_product(rows[0])

    def get_product_by_slug(self, slug: str) -> dict[str, Any]:
        rows = (
            self.db.table("products")
            .select(PRODUCT_SELECT)
            .eq("slug", slug)
            .eq("is_active", True)
            .limit(1)
            .execute()
            .data
            or []
        )
        if not rows:
            raise NotFoundError("El producto no existe o no esta disponible.")
        return _normalize_product(rows[0])

    def list_categories(self) -> list[str]:
        rows = (
            self.db.table("products")
            .select("category")
            .eq("is_active", True)
            .execute()
            .data
            or []
        )
        return sorted({row["category"] for row in rows})

    def list_sizes(self) -> list[str]:
        """Tallas realmente comprables hoy en el catalogo publico.

        Solo cuentan variantes con stock > 0 de productos activos: ese es el
        mismo criterio que aplica el filtro ``size``. Pintar un chip de talla
        agotada manda al usuario a una pagina donde no puede comprar.
        """
        active_ids = [
            row["id"]
            for row in (
                self.db.table("products")
                .select("id")
                .eq("is_active", True)
                .execute()
                .data
                or []
            )
        ]
        if not active_ids:
            return []

        rows = (
            self.db.table("product_variants")
            .select("size")
            .gt("stock", 0)
            .in_("product_id", active_ids)
            .execute()
            .data
            or []
        )
        sizes = {str(row["size"]) for row in rows if row.get("size")}
        return sorted(sizes, key=lambda s: (_SIZE_ORDER.get(s.upper(), 99), s))

    def count_inactive(self) -> int:
        """Cuenta productos desactivados. Sirve al contador del panel admin."""
        response = (
            self.db.table("products")
            .select("id", count="exact")
            .eq("is_active", False)
            .execute()
        )
        return response.count or 0

    # ------------------------------------------------------------------
    # Escrituras (solo admin, el router valida el rol)
    # ------------------------------------------------------------------
    def create_product(self, data: dict[str, Any]) -> dict[str, Any]:
        variants = data.pop("variants")
        slug = data.get("slug") or _slugify(data["name"])

        payload = {key: _to_db_value(value) for key, value in data.items()}
        payload["slug"] = slug

        try:
            created = self.db.table("products").insert(payload).execute().data or []
        except Exception as exc:  # unique violation de slug
            if "duplicate key" in str(exc):
                raise ConflictError(f"Ya existe un producto con el slug '{slug}'.") from exc
            raise

        if not created:
            raise ConflictError("No se pudo crear el producto.")

        product = created[0]

        try:
            self.db.table("product_variants").insert(
                [{**variant, "product_id": product["id"]} for variant in variants]
            ).execute()
        except Exception:
            # Compensacion: el insert de variantes es atomico entre si, pero no
            # con el del producto. Sin transaccion multi-tabla en PostgREST,
            # limpiamos el producto huerfano.
            self.db.table("products").delete().eq("id", product["id"]).execute()
            raise

        return self.get_product(product["id"], include_inactive=True)

    def update_product(self, product_id: str, data: dict[str, Any]) -> dict[str, Any]:
        self.get_product(product_id, include_inactive=True)

        if not data:
            raise ConflictError("No enviaste ningun campo para actualizar.")

        payload = {key: _to_db_value(value) for key, value in data.items()}

        try:
            updated = (
                self.db.table("products")
                .update(payload)
                .eq("id", product_id)
                .execute()
                .data
                or []
            )
        except Exception as exc:
            if "duplicate key" in str(exc):
                raise ConflictError("El slug ya esta en uso por otro producto.") from exc
            raise

        if not updated:
            raise NotFoundError("El producto no existe.")
        return self.get_product(product_id, include_inactive=True)

    def update_variant_stock(self, product_id: str, variant_id: str, stock: int) -> dict[str, Any]:
        rows = (
            self.db.table("product_variants")
            .select("id")
            .eq("id", variant_id)
            .eq("product_id", product_id)
            .limit(1)
            .execute()
            .data
            or []
        )
        if not rows:
            raise NotFoundError("La variante no existe para ese producto.")

        (
            self.db.table("product_variants")
            .update({"stock": stock})
            .eq("id", variant_id)
            .execute()
        )

        updated = (
            self.db.table("product_variants")
            .select("*")
            .eq("id", variant_id)
            .limit(1)
            .execute()
            .data
            or []
        )
        return updated[0]

    def deactivate_product(self, product_id: str) -> None:
        self.get_product(product_id, include_inactive=True)
        (
            self.db.table("products")
            .update({"is_active": False})
            .eq("id", product_id)
            .execute()
        )
