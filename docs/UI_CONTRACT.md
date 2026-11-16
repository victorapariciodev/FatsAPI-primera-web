# Contrato UI ↔ API ↔ Base de datos

Regla del MVP: **ningún elemento visual existe si no tiene endpoint, tabla y campo que lo respalden.** Si algo no está aquí, no se diseña.

## Reglas globales

| Regla | Implementación |
|---|---|
| Sesión | Cookies `sb_access` / `sb_refresh`. En `/api/*` el 401 devuelve JSON, no redirect |
| Rol admin | `app_metadata.role == "admin"`. El 403 lo decide el backend, nunca el front |
| Dinero | Llega como string (`"29.90"`). Se formatea para mostrar. **Prohibido sumar precios en JS** |
| Errores de dominio | `{ "detail": "...", "code": "insufficient_stock" }` |
| Paginación | `page` (≥1) y `page_size` (1–100). Respuesta: `total`, `pages` |
| Carrito | Cada mutación devuelve el carrito completo. El badge sale de `total_items` |
| Imágenes | Un solo `image_url` por producto. Si es `null`, placeholder. No hay galería múltiple |

Códigos que la UI debe saber pintar: `401`, `403`, `404`, `409` (`insufficient_stock`, `invalid_operation`, `conflict`), `422`.

---

## 1. Catálogo — `/tienda`

**Datos:** `GET /api/products`

| Query param | Tipo | Uso en pantalla |
|---|---|---|
| `category` | string | Chips de categoría |
| `search` | string | Buscador. Busca en `products.name` **y** en `product_variants.sku` |
| `size` | string | Chips de talla (variantes con stock > 0) |
| `in_stock` | bool | Switch "Solo disponibles" |
| `sort` | `newest` \| `price_asc` \| `price_desc` | Selector de orden |
| `min_price` / `max_price` | number | Inputs de rango |
| `page` / `page_size` | int | Paginación |

**Respuesta por producto:** `id, name, slug, description, category, price, currency, image_url, is_active, variants[{id, size, color, sku, stock}]`

**Acciones**

| Elemento | Acción real |
|---|---|
| Chip de talla de la tarjeta | Navega a `/tienda/{slug}?size={size}` |
| CTA de la tarjeta | **"Elegir talla"** → PDP. NO puede agregar al carrito: falta `variant_id` |
| Badge "Agotado" | Se calcula: todas las variantes con `stock == 0` |
| Paginación | Cambia `page` en la URL |
| Buscador | Placeholder correcto: "Buscar prendas por nombre o SKU…" (no categoría: la categoría es un chip aparte) |

**Estados:** esqueleto de carga, vacío ("No encontramos prendas con esos filtros"), error con reintento.

---

## 2. Detalle de producto — `/tienda/{slug}`

**Datos:** `GET /api/products/by-slug/{slug}`

| Campo | Uso |
|---|---|
| `name`, `description`, `category`, `image_url` | Cabecera y galería |
| `price`, `currency` | Precio. `currency` siempre visible |
| `variants[].size` / `.color` | Selectores |
| `variants[].sku` | Texto técnico monoespaciado |
| `variants[].stock` | Máximo del stepper y estado del botón |

**Acciones**

| Elemento | Endpoint | Resultado |
|---|---|---|
| Seleccionar variante | — | Filtra combinaciones existentes. Las de `stock == 0` se muestran **deshabilitadas** |
| Stepper cantidad | — | `1 ≤ cantidad ≤ stock` de la variante elegida |
| **Agregar al carrito** | `POST /api/cart/items` `{variant_id, quantity}` | Devuelve `CartOut`; actualiza badge y muestra toast |
| Volver | — | `/tienda` |

**Errores:** `401` → "Inicia sesión para continuar" + link a `/login`; `409 insufficient_stock` → "Solo quedan N unidades"; `404` → producto no disponible.

**Prohibido:** reseñas, estrellas, "compra ahora", tallas inventadas, guía de tallas (no hay tabla), envío gratis prometido (solo aplica si supera el umbral real).

---

## 3. Carrito — `/carrito`

**Datos:** `GET /api/cart` → `id, items[], total_items, subtotal, shipping_cost, free_shipping_threshold, total`

Cada item: `id, variant_id, quantity, size, color, sku, product_id, product_name, image_url, stock_available, unit_price, line_total`

**Acciones**

| Elemento | Endpoint | Nota |
|---|---|---|
| Stepper | `PATCH /api/cart/items/{item_id}` `{quantity}` | Tope `stock_available`; `409` si se pasa |
| Quitar | `DELETE /api/cart/items/{item_id}` | `404` si el item no es del usuario |
| Vaciar carrito | `DELETE /api/cart` | Idempotente: devuelve `CartOut` vacío aunque no hubiera items |
| Resumen | — | `subtotal` + `shipping_cost` = `total`, **todos del servidor** |
| "Gratis desde" | `free_shipping_threshold` | Texto dinámico, no hardcodeado |
| **Continuar pedido** | — | Navega a `/pedido/confirmar` |

**Estados:** vacío con CTA a `/tienda`, advertencia si `quantity > stock_available`, error al mutar.

**Prohibido:** cupones, códigos promo, "calcular envío" por zona, pago.

---

## 4. Confirmar pedido — `/pedido/confirmar`

**Datos:** `GET /api/cart` (resumen de solo lectura).

**Formulario:** exactamente `ShippingAddress`:

| Campo | Validación backend |
|---|---|
| `full_name` | 3–120 |
| `phone` | 7–30 |
| `address_line` | 5–200 |
| `city` | 2–80 |
| `state` | 2–80 |
| `postal_code` | opcional, ≤20 |
| `country` | 2 letras, default `VE` |

**Acción:** `POST /api/orders` `{ "shipping_address": { ... } }` → `201 OrderOut`.

**Errores reales que la pantalla debe pintar**

| Caso | Respuesta | UI |
|---|---|---|
| Carrito vacío | `409 invalid_operation` | Volver al carrito |
| Stock cambió | `409 insufficient_stock` | "Un producto agotó su stock" + refrescar carrito |
| Producto desactivado | `409 invalid_operation` | Quitar del carrito y reintentar |
| Sin sesión | `401` | `/login` |

**Prohibido:** campos de tarjeta, CVV, dirección de facturación, cuotas, cupones, "pagar". Aviso obligatorio: "No se procesa pago en línea".

---

## 5. Mis pedidos — `/pedidos` y `/pedidos/{id}`

**Datos:** `GET /api/orders?page&page_size` (`items, total`) y `GET /api/orders/{order_id}`.

Campos: `id, status, subtotal, shipping_cost, total, currency, shipping_address, created_at, items[]`
Item: `id, variant_id, product_name, size, color, unit_price, quantity, line_total` (snapshot histórico)

**Estados válidos (CHECK en DB):** `pending`, `shipped`, `delivered`, `cancelled`. No existe "paid".

| Elemento | Acción real |
|---|---|
| Chip de estado | Solo lectura, mapea 1:1 con el CHECK |
| Ver detalle | `GET /api/orders/{order_id}` |
| Cancelar | `POST /api/orders/{order_id}/cancel` → devuelve stock. Solo si `status == "pending"` |
| Confirmación de cancelación | Modal obligatorio: la acción es irreversible |

`shipped` y `delivered` se actualizan por base de datos/administración; **no hay pantalla ni endpoint de despacho en este MVP** (no se diseña un botón para eso).

`GET /api/orders` **no acepta búsqueda ni filtro por estado**: solo `page` y `page_size`. Por eso la pantalla no lleva buscador ni chips de filtro.

---

## 6. Admin de productos — `/admin/productos`

**Datos:** `GET /api/admin/products` (incluye inactivos) con `category`, `search`, `page`, `page_size`.

**Acciones**

| Elemento | Endpoint |
|---|---|
| Crear producto + variantes | `POST /api/products` |
| Editar datos | `PATCH /api/products/{product_id}` |
| Activar / desactivar | `PATCH /api/products/{product_id}` `{is_active}` |
| Reponer stock | `PATCH /api/products/{product_id}/variants/{variant_id}/stock` `{stock}` |
| Ocultar del catálogo | `DELETE /api/products/{product_id}` → 204 (borrado lógico) |

**Stock total de la fila:** suma de `variants[].stock` calculada en cliente sobre la respuesta (no hay columna agregada en DB).

**Errores:** `403` sin rol admin, `409 conflict` por slug o SKU duplicado, `422` si falta al menos una variante o `price <= 0`.

**Prohibido:** gestión de pedidos, pagos, reportes de ventas (no hay tabla de pagos).

---

## 7. Mapa campo de UI → tabla.columna

| UI | Tabla.columna |
|---|---|
| Nombre de producto | `products.name` |
| Categoría / chip | `products.category` |
| Precio | `products.price` |
| Moneda | `products.currency` |
| Imagen | `products.image_url` |
| Activo / inactivo | `products.is_active` |
| Talla | `product_variants.size` |
| Color | `product_variants.color` |
| SKU | `product_variants.sku` |
| Stock | `product_variants.stock` |
| Cantidad en carrito | `cart_items.quantity` |
| Subtotal / envío / total | `orders.subtotal`, `orders.shipping_cost`, `orders.total` |
| Estado del pedido | `orders.status` (CHECK de 4 valores) |
| Dirección | `orders.shipping_address` (jsonb) |
| Nombre/talla/color/precio del item comprado | `order_items.*` (snapshot, no cambia si editas el producto) |

---

## 8. Fuera de alcance (no diseñar)

- Pagos, tarjetas, pasarelas, estado "pagado".
- Reseñas, calificaciones, favoritos, lista de deseos.
- Cupones y descuentos.
- Múltiples imágenes por producto.
- Búsqueda por categoría en el buscador (la categoría es un chip/filtro aparte).
- Direcciones guardadas por usuario (solo la del pedido).
- Despacho/envío con tracking.
- Notificaciones por correo.
