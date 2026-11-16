"""Schemas de catalogo.

Nota sobre dinero: se usa ``Decimal``. Pydantic v2 lo serializa como string en
JSON ("29.90") para no perder precision con floats. Si tu frontend necesita
numeros, convierte ahi; el backend nunca hace aritmetica monetaria con float.
"""

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class VariantCreate(BaseModel):
    size: str = Field(min_length=1, max_length=10)
    color: str = Field(min_length=1, max_length=40)
    sku: str = Field(min_length=3, max_length=64)
    stock: int = Field(default=0, ge=0)


class VariantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    size: str
    color: str
    sku: str
    stock: int


class ProductCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    slug: str | None = Field(default=None, max_length=140)
    description: str | None = Field(default=None, max_length=2000)
    category: str = Field(min_length=2, max_length=60)
    price: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    image_url: str | None = Field(default=None, max_length=500)
    variants: list[VariantCreate] = Field(min_length=1)


class ProductUpdate(BaseModel):
    """PATCH parcial: solo se aplican los campos enviados."""

    name: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    category: str | None = Field(default=None, min_length=2, max_length=60)
    price: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    image_url: str | None = Field(default=None, max_length=500)
    is_active: bool | None = None


class StockUpdate(BaseModel):
    stock: int = Field(ge=0)


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    slug: str
    description: str | None = None
    category: str
    price: Decimal
    currency: str
    image_url: str | None = None
    is_active: bool
    variants: list[VariantOut] = Field(default_factory=list)


class ProductPage(BaseModel):
    items: list[ProductOut]
    total: int
    page: int
    page_size: int
    pages: int
