---
name: NightKids Store
description: Tienda de ropa del colectivo NightKids UNEFA. Estética terminal/cyber oscura, acento cian, tipografía Space Grotesk + JetBrains Mono.
colors:
  primary: "#dbfcff"
  primary-fixed: "#7df4ff"
  primary-container: "#00f0ff"
  on-primary: "#00363a"
  background: "#131319"
  surface: "#131319"
  surface-container-lowest: "#0e0e14"
  surface-container-low: "#1b1b22"
  surface-container: "#1f1f26"
  surface-container-high: "#2a2930"
  surface-container-highest: "#35343b"
  on-surface: "#e4e1eb"
  on-surface-variant: "#b9cacb"
  outline: "#849495"
  outline-variant: "#3b494b"
  secondary: "#ffb0cd"
  secondary-container: "#aa0266"
  on-secondary-container: "#ffbad3"
  tertiary: "#fff4df"
  tertiary-container: "#ffd546"
  on-tertiary: "#3c2f00"
  error: "#ffb4ab"
  on-error: "#690005"
  error-container: "#93000a"
  on-error-container: "#ffdad6"
typography:
  display-xl:
    fontFamily: Space Grotesk
    fontSize: 56px
    fontWeight: 700
    lineHeight: 64px
    letterSpacing: -0.03em
  headline-lg:
    fontFamily: Space Grotesk
    fontSize: 36px
    fontWeight: 600
    lineHeight: 44px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Space Grotesk
    fontSize: 24px
    fontWeight: 600
    lineHeight: 32px
    letterSpacing: -0.01em
  headline-sm:
    fontFamily: Space Grotesk
    fontSize: 20px
    fontWeight: 500
    lineHeight: 28px
  body-md:
    fontFamily: Space Grotesk
    fontSize: 15px
    fontWeight: 400
    lineHeight: 24px
  body-sm:
    fontFamily: Space Grotesk
    fontSize: 13px
    fontWeight: 400
    lineHeight: 20px
  label-caps:
    fontFamily: JetBrains Mono
    fontSize: 11px
    fontWeight: 600
    lineHeight: 16px
    letterSpacing: 0.12em
  code-md:
    fontFamily: JetBrains Mono
    fontSize: 13px
    fontWeight: 400
    lineHeight: 20px
  code-sm:
    fontFamily: JetBrains Mono
    fontSize: 11px
    fontWeight: 400
    lineHeight: 16px
rounded:
  sm: 2px
  md: 4px
  lg: 8px
  xl: 12px
spacing:
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 40px
  2xl: 64px
  gutter: 24px
  margin: 32px
components:
  button-primary:
    backgroundColor: "{colors.primary-container}"
    textColor: "{colors.on-primary}"
    typography: "{typography.label-caps}"
    rounded: "{rounded.md}"
    padding: "{spacing.sm}"
    height: 40px
  button-secondary:
    backgroundColor: "{colors.surface-container-high}"
    textColor: "{colors.primary-fixed}"
    typography: "{typography.label-caps}"
    rounded: "{rounded.md}"
    padding: "{spacing.sm}"
    height: 40px
  card-product:
    backgroundColor: "{colors.surface-container}"
    textColor: "{colors.on-surface}"
    rounded: "{rounded.lg}"
    padding: "{spacing.md}"
  input-field:
    backgroundColor: "{colors.surface-container-high}"
    textColor: "{colors.on-surface}"
    rounded: "{rounded.md}"
    padding: "{spacing.sm}"
    height: 44px
  badge-pending:
    backgroundColor: "{colors.tertiary-container}"
    textColor: "{colors.on-tertiary}"
    typography: "{typography.label-caps}"
    rounded: "{rounded.sm}"
    padding: "{spacing.xs}"
  badge-error:
    backgroundColor: "{colors.error}"
    textColor: "{colors.on-error}"
    typography: "{typography.label-caps}"
    rounded: "{rounded.sm}"
    padding: "{spacing.xs}"
  nav-bar:
    backgroundColor: "{colors.surface-container-lowest}"
    textColor: "{colors.on-surface-variant}"
  toast:
    backgroundColor: "{colors.surface-container-high}"
    textColor: "{colors.on-surface}"
    rounded: "{rounded.md}"
    padding: "{spacing.md}"
---

## Overview

Tienda de ropa del colectivo NightKids (UNEFA). Hereda la identidad del landing: terminal cyber, fondo casi negro con tinte violeta, cian eléctrico como único acento de acción y amarillo para estados de atención. El producto manda: la ropa se ve sobre superficies oscuras neutras, no sobre neones.

Reglas de atmósfera:
- El 80% de la pantalla vive en la familia `surface`. El cian se reserva para CTA, foco y telemetría de estado, nunca para decorar bloques enteros.
- Nada de blanco puro (`#fff`) ni negro puro (`#000`): siempre `on-surface` sobre `background` o `surface-container`.
- El brillo (glow) solo se permite en el botón primario y en indicadores de estado activo. Si todo brilla, nada brilla.
- Interfaz en español, tono directo y técnico, sin signos de admiración ni lenguaje de marketing agresivo.

Alcance del MVP: catálogo, carrito y pedido. **No existe pago en línea**: no se diseñan campos de tarjeta, pasarelas ni estados "pagado".

## Colors

- `primary` y `primary-fixed`: texto de acento y enlaces sobre superficie. No son color de fondo.
- `primary-container` (#00f0ff): acción principal y foco. Es el único color que puede llevar glow. Texto encima: `on-primary`.
- `background` / `surface`: base de la app. `surface-container-lowest` para header fijo, `surface-container` para tarjetas, `surface-container-high` para inputs y hover.
- `on-surface`: texto principal. `on-surface-variant`: texto secundario, metadatos y descripciones.
- `outline` / `outline-variant`: bordes de 1px. Los bordes separan, no compiten.
- `secondary` (#ffb0cd): acento de marca para destacados suaves (nuevo, drop, colección).
- `tertiary-container` (#ffd546): estado pendiente / advertencia suave. Texto `on-tertiary`.
- `error` sobre `error-container` para errores de stock y validación. Nunca rojo saturado como fondo de pantalla completa.

## Typography

- **Space Grotesk** para titulares y cuerpo: da el aire geométrico del colectivo sin caer en lo corporativo.
- **JetBrains Mono** para etiquetas en mayúsculas, precios, SKU, tallas, estados y todo dato "de sistema". Los precios y estados se sienten como telemetría, no como publicidad.
- Escala: `display-xl` solo en hero de catálogo; `headline-lg` títulos de página; `headline-md` nombre de producto en detalle; `headline-sm` nombre en tarjeta; `body-md` descripciones; `body-sm` metadatos.
- Etiquetas de sección y badges siempre `label-caps` con tracking amplio.
- Nunca bajar de 11px. Nunca usar más de dos familias en una misma pantalla.

## Layout

- Contenedor máximo 1280px (`max-w-7xl`) con gutter de 24px y márgenes laterales de 32px en desktop.
- Header fijo de 80px de alto, fondo `surface-container-lowest` al 85% con blur. El contenido arranca con 80px de padding superior.
- Catálogo: sidebar de filtros de 240px + grid de 3 columnas en desktop, 2 en tablet, 1 en móvil. Gap de 24px.
- Detalle: dos columnas 60/40 (galería / compra). En móvil, galería arriba y bloque de compra sticky abajo.
- Carrito: lista principal + resumen lateral sticky de 360px.
- Escala de espaciado 4/8/16/24/40/64. Todo múltiplo de 8 salvo detalles de 4px.
- Densidad media: una tarjeta debe respirar, pero el grid debe mostrar al menos 6 productos en el primer viewport de 1440px.

## Elevation & Depth

- La profundidad se construye con **capas de superficie + borde de 1px**, no con sombras grandes.
- Sombra permitida: `0 1px 8px rgba(0,0,0,0.4)` en header; glow cian `0 0 15px rgba(0,240,255,0.4)` solo en CTA primario.
- Elementos flotantes (toast, mini-carrito, dropdown de filtros) usan `surface-container-high` + borde `outline-variant` + la sombra del header.
- Sin glassmorphism decorativo fuera del header y del panel de resumen sticky.

## Shapes

- Esquinas contenidas: 2px para badges y chips, 4px para botones e inputs, 8px para tarjetas y paneles, 12px para contenedores grandes.
- Nada de píldoras gigantes ni radios de 24px+: la identidad es técnica, no juguetona.
- Imágenes de producto con radio 8px y relación 4:5, `object-fit: cover`.
- Chips de talla rectangulares con borde `outline-variant`; el seleccionado pasa a borde `primary-container` y texto `primary-container`.

## Components

- **Botón primario**: cian sobre `on-primary`, texto `label-caps`, alto 40px, glow suave. Un solo botón primario por vista. Deshabilitado: `surface-container-highest` con texto `outline`, sin glow.
- **Botón secundario**: superficie alta con texto cian, mismo alto. Para "Cancelar", "Seguir comprando", "Reponer stock".
- **Tarjeta de producto**: superficie `surface-container`, borde 1px `outline-variant`, imagen 4:5, nombre en `headline-sm`, precio en `code-md` color `primary-fixed`, chips de talla y badge "Agotado" cuando todas las variantes están en 0.
- **Inputs**: fondo `surface-container-high`, borde `outline-variant`, foco con borde y ring cian de 1px. Etiqueta en `label-caps` arriba. Error: borde `error` y mensaje `body-sm` en `error`.
- **Stepper de cantidad**: dos botones cuadrados de 32px con superficie alta y número en `code-md` al centro. Máximo limitado por stock.
- **Badges de estado de pedido**: `pending` en amarillo (`badge-pending`), `shipped` y `delivered` en cian suave, `cancelled` en `error` (`badge-error`). Siempre `label-caps` en mayúsculas.
- **Toast**: esquina inferior derecha, superficie alta, borde left de 2px cian (éxito) o `error` (fallo), auto-cierre a los 4s.
- **Estado vacío**: icono de línea en `outline`, titular `headline-sm`, una frase `body-sm` en `on-surface-variant` y un CTA secundario.
- **Skeleton de carga**: bloques `surface-container` con pulso lento; nunca spinner centrado en toda la página.

## Do's and Don'ts

- **Sí**: mostrar variantes agotadas deshabilitadas con su talla visible. El usuario necesita saber que existen.
- **Sí**: mantener el precio en JetBrains Mono y alineado a la derecha en listas y totales.
- **Sí**: reflejar el carrito completo que devuelve el backend; el contador del header sale de `total_items`.
- **Sí**: diseñar explícitamente los estados vacío, cargando, error y sin stock.
- **No**: incluir campos de tarjeta, logos de pasarelas, cuotas, descuentos de pago ni el estado "pagado". Este MVP no cobra.
- **No**: calcular totales en el cliente ni mostrar precios que no vengan del backend.
- **No**: usar blanco puro como fondo, gradientes de arcoíris ni sombras difusas grandes.
- **No**: ocultar productos agotados del catálogo; se muestran con su badge.
- **No**: poner más de un CTA primario cian en la misma pantalla.
