"""Schemas del carrito.

El cliente solo manda ``variant_id`` y ``quantity``. El precio y el total los
calcula el backend leyendo el catalogo: jamas se acepta un precio del cliente.
"""

from decimal import Decimal

from pydantic import BaseModel, Field


class CartItemCreate(BaseModel):
    variant_id: str = Field(min_length=1)
    quantity: int = Field(default=1, ge=1, le=20)


class CartItemUpdate(BaseModel):
    quantity: int = Field(ge=1, le=20)


class CartItemOut(BaseModel):
    id: str
    variant_id: str
    quantity: int
    size: str
    color: str
    sku: str
    product_id: str
    product_name: str
    image_url: str | None = None
    stock_available: int
    unit_price: Decimal
    line_total: Decimal


class CartOut(BaseModel):
    id: str | None = None
    items: list[CartItemOut] = Field(default_factory=list)
    total_items: int = 0
    subtotal: Decimal = Decimal("0.00")
    shipping_cost: Decimal = Decimal("0.00")
    free_shipping_threshold: Decimal = Decimal("0.00")
    total: Decimal = Decimal("0.00")
