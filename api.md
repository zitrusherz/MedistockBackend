# API

## Base
- Base URL: `/api/`
- Auth: JWT Bearer en header `Authorization: Bearer <access>`

## Autenticacion JWT

### Endpoints globales (SimpleJWT default)
- `POST /api/token/` (publico)
- `POST /api/token/refresh/` (publico)

### Endpoints de cuentas
- `POST /api/accounts/login/` (publico)
  - Body:
    ```json
    {
      "username": "usuario@correo.com",
      "password": "tu_password"
    }
    ```
  - Respuesta: `access`, `refresh` (el access incluye claims: `username`, `email`, `grupos`, `full_name`).

- `POST /api/accounts/login/refresh/` (publico)
  - Body:
    ```json
    {"refresh": "<refresh_token>"}
    ```

- `POST /api/accounts/logout/` (auth requerida)
  - Body:
    ```json
    {"refresh": "<refresh_token>"}
    ```
  - Respuesta: `205 RESET_CONTENT` si el refresh se invalida.

### Registro (publico)
- `POST /api/accounts/registro/trabajador/`
  - Body (ejemplo):
    ```json
    {
      "usuario": {
        "username": "correo@dominio.com",
        "email": "correo@dominio.com",
        "first_name": "Nombre",
        "last_name": "Apellido",
        "password": "...",
        "password2": "..."
      },
      "rut": "12345678-9",
      "telefono": "...",
      "direccion": "...",
      "comuna": 1,
      "sucursal": 1,
      "cargo": "..."
    }
    ```

- `POST /api/accounts/registro/cliente/` (publico)
  - Body (ejemplo):
    ```json
    {
      "usuario": {
        "username": "correo@dominio.com",
        "email": "correo@dominio.com",
        "first_name": "Nombre",
        "last_name": "Apellido",
        "password": "...",
        "password2": "..."
      },
      "rut": "12345678-9",
      "pasaporte": null,
      "tipo_cliente": "PARTICULAR",
      "telefono": "...",
      "institucion_id": null,
      "datos_institucion": null,
      "direccion_entrega": {
        "direccion": "Calle 123",
        "num_direccion": "10",
        "detalle_direccion": "Depto 201",
        "comuna": 5,
        "referencia": "...",
        "nombre_receptor": "...",
        "telefono_receptor": "...",
        "es_principal": true
      }
    }
    ```
  - Reglas:
    - Se requiere `rut` o `pasaporte` (no ambos).
    - `direccion_entrega` es obligatoria.
    - Para `tipo_cliente=INSTITUCIONAL`:
      - `rut` es obligatorio.
      - Debes enviar `institucion_id` o `datos_institucion` (no ambos).
    - Para `tipo_cliente=PARTICULAR`: no enviar `institucion_id` ni `datos_institucion`.

### CRUD perfiles (auth requerida)
- Trabajadores:
  - `GET/POST /api/accounts/trabajadores/`
  - `GET/PUT/PATCH/DELETE /api/accounts/trabajadores/<id>/`
  - Respuesta: `PerfilTrabajadorSerializer`

- Clientes:
  - `GET/POST /api/accounts/clientes/`
  - `GET/PUT/PATCH/DELETE /api/accounts/clientes/<id>/`
  - Respuesta: `PerfilClienteSerializer`

---

## Accounts (`/api/accounts/`)

### Perfil propio
- `GET /api/accounts/perfil/me/` (auth requerida)
  - Respuesta:
    ```json
    {
      "rol": "CLIENTE",
      "datos": { /* MiPerfilClienteSerializer */ }
    }
    ```
    o
    ```json
    {
      "rol": "TRABAJADOR",
      "datos": { /* PerfilTrabajadorSerializer */ }
    }
    ```

- `PATCH /api/accounts/perfil/me/` (auth requerida, solo clientes)
  - Campos editables (parciales): `rut`, `pasaporte`, `telefono`, `email`, `first_name`, `last_name`.
  - Validaciones:
    - No permite vaciar campos que ya estaban informados.
    - `email`, `first_name`, `last_name` no pueden ir vacios si se envian.

---

## Inventory (`/api/inventory/`)

### Publicos (sin auth)
- `GET /api/inventory/catalogo/`
  - Filtros: `marca_id`, `categoria_id`, `sucursal_id`
  - Respuesta (por item):
    ```json
    {
      "id": 1,
      "sku": "SKU123",
      "nombre": "Producto",
      "descripcion": "...",
      "valor_unitario": 1200,
      "marca": {"id": 2, "nombre": "Marca", "activo": true},
      "unidad_medida": "unidad",
      "largo_mm": 10,
      "ancho_mm": 10,
      "alto_mm": 10,
      "peso_mg": 100,
      "volumen_ml": 0,
      "requiere_control_vencimiento": true,
      "registro_sanitario": "ABC",
      "activo": true,
      "es_caja": false,
      "categorias": ["Cat1", "Cat2"],
      "stock_por_sucursal": [
        {"sucursal_id": 1, "sucursal_nombre": "Sucursal", "stock_neto": 10}
      ]
    }
    ```

- `GET /api/inventory/catalogo-cajas/`
  - Igual a `catalogo/`, pero `es_caja=true`.

- `GET /api/inventory/public/categorias/`
  - Respuesta: `{ "id", "nombre", "activo" }`

- `GET /api/inventory/public/marcas/`
  - Respuesta: `{ "id", "nombre", "activo" }`

- `GET /api/inventory/public/productos/<id>/`
  - Respuesta: `ProductoSerializer` (detalle de producto, sin stock por sucursal).

### Privados (auth requerida)
- Categorias:
  - `GET/POST /api/inventory/categorias/`
  - `GET/PUT/PATCH/DELETE /api/inventory/categorias/<id>/`
  - Body/Response: `CategoriaSerializer`

- Marcas:
  - `GET/POST /api/inventory/marcas/`
  - `GET/PUT/PATCH/DELETE /api/inventory/marcas/<id>/`
  - Body/Response: `MarcaSerializer`

- Productos:
  - `GET/POST /api/inventory/productos/`
  - `GET/PUT/PATCH/DELETE /api/inventory/productos/<id>/`
  - Body/Response: `ProductoSerializer`
  - Nota: `marca_id` es write-only; `categorias` se lee via `categoriaproducto_set`.

- Lotes:
  - `GET/POST /api/inventory/lotes/`
  - `GET/PUT/PATCH/DELETE /api/inventory/lotes/<id>/`
  - Body/Response: `LoteSerializer`
  - Nota: `producto_id` es write-only; `producto` se entrega resumido.

- Inventarios:
  - `GET/POST /api/inventory/inventarios/`
  - `GET/PUT/PATCH/DELETE /api/inventory/inventarios/<id>/`
  - Body/Response: `InventarioSerializer`
  - Nota: `lote_id` es write-only; `lote` se entrega con detalle.

- Movimientos de inventario:
  - `GET/POST /api/inventory/movimientos/`
  - `GET /api/inventory/movimientos/<id>/`
  - Body: `MovimientoInventarioSerializer` (el `usuario` se toma del request)

- Traslados de inventario:
  - `GET/POST /api/inventory/traslados/`
  - `GET/PUT/PATCH/DELETE /api/inventory/traslados/<id>/`
  - Body/Response: `TrasladoInventarioSerializer`
  - Nota: crear requiere `detalles_write` (lista de `{lote_id, cantidad}`) y setea `solicitado_por` desde el usuario.

---

## Orders (`/api/orders/`) (auth requerida)

- `POST /api/orders/pedidos/`
  - Crea pedido desde usuario autenticado (cliente).
  - Body (ejemplo):
    ```json
    {
      "sucursal_origen_id": 1,
      "direccion_entrega_id": 3,
      "tipo_venta": "WEBPAY",
      "tipo_despacho": "NORMAL",
      "prioridad_medica": "NORMAL",
      "fecha_requerida_entrega": "2026-05-17T10:00:00Z",
      "observacion": "...",
      "detalles": [
        {"producto_id": 5, "cantidad": 2},
        {"producto_id": 8, "cantidad": 1, "lote_id": 12}
      ]
    }
    ```
  - Respuesta: `PedidoOutputSerializer`.

- `GET /api/orders/pedidos/<pedido_id>/`
  - Respuesta: `PedidoOutputSerializer`.
  - Permisos: cliente dueno del pedido o trabajador interno.

- `PATCH /api/orders/pedidos/<pedido_id>/`
  - Solo clientes (pedido en estado `PENDIENTE` o `APROBADO`).
  - Body: `PedidoClienteUpdateSerializer`.
  - Respuesta: `PedidoOutputSerializer`.

- `POST /api/orders/pedidos/<pedido_id>/aprobar/`
  - Solo ejecutivos (grupo `Ejecutivo`/`Administrador`) o `is_staff`.
  - Body:
    ```json
    {"accion": "APROBADO" | "RECHAZADO", "comentario": "..."}
    ```
  - Respuesta:
    ```json
    {"pedido_id": 1, "estado_pedido": "APROBADO", "comentario": "..."}
    ```

---

## Logistics (`/api/logistics/`) (publico actualmente)

- `POST /api/logistics/cotizar/`
  - Modos:
    1) Con pedido existente:
    ```json
    {"pedido_id": 42, "county_code_destino": "PROV"}
    ```
    2) Sin pedido (consulta libre):
    ```json
    {
      "sucursal_id": 1,
      "county_code_destino": "CONC",
      "productos": [
        {"peso_mg": 500000, "largo_mm": 200, "ancho_mm": 150, "alto_mm": 100, "cantidad": 3}
      ]
    }
    ```
  - Respuesta: `CotizacionOutputSerializer`.

- `POST /api/logistics/envios/`
  - Crea OT en Chilexpress para un pedido aprobado.
  - Body:
    ```json
    {
      "pedido_id": 42,
      "service_type_code": 3,
      "label_type": 2,
      "contacto_nombre": "...",
      "contacto_telefono": "...",
      "contacto_email": "..."
    }
    ```
  - Respuesta:
    ```json
    {
      "despacho": { /* DespachoSerializer */ },
      "numero_ot": 123,
      "num_cajas": 1,
      "etiqueta_disponible": true,
      "service_description": "..."
    }
    ```

- `GET /api/logistics/envios/<pedido_id>/tracking/`
  - Query param opcional: `?historial=true`
  - Respuesta: payload de Chilexpress (tracking).

---

## Locations (`/api/locations/`) (publico)

- `GET /api/locations/regions/`
  - Respuesta: `RegionSerializer`.

- `GET /api/locations/regions-with-comunas/`
  - Respuesta: `RegionWithComunasSerializer`.

- `GET /api/locations/comunas/`
  - Filtro opcional: `region_id`
  - Respuesta: `ComunaPublicSerializer` (incluye `chilexpress` cuando hay cobertura).

- `GET /api/locations/comunas-chilexpress/`
  - Filtros opcionales: `retorna_respuesta`, `comuna_id`
  - Respuesta: `ComunaChilexpressSerializer`.

- `GET /api/locations/sucursales/<id>/`
  - Respuesta: `SucursalPublicSerializer` (incluye `comuna` y `county_code`).
