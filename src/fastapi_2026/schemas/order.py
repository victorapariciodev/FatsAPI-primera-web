"""Schemas de pedidos (creacion desde el carrito, historial, cancelacion).

El MVP no procesa pagos: no hay montos de cobro ni referencias de pasarela.
"""

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ShippingAddress(BaseModel):
    full_name: str = Field(min_length=3, max_length=120)
    phone: str = Field(min_length=7, max_length=30)
    address_line: str = Field(min_length=5, max_length=200)
    city: str = Field(min_length=2, max_length=80)
    state: str = Field(min_length=2, max_length=80)
    postal_code: str | None = Field(default=None, max_length=20)
    country: str = Field(default="VE", min_length=2, max_length=2)


class OrderCreate(BaseModel):
    shipping_address: ShippingAddress


class OrderItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    variant_id: str | None = None
    product_name: str
    size: str
    color: str
    unit_price: Decimal
    quantity: int
    line_total: Decimal


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: str
    subtotal: Decimal
    shipping_cost: Decimal
    total: Decimal
    currency: str
    shipping_address: dict
    created_at: str | None = None
    items: list[OrderItemOut] = Field(default_factory=list)


class OrderPage(BaseModel):
    items: list[OrderOut]
    total: int
