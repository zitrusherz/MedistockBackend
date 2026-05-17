# API

## Base
- Base URL: `/api/`
- Auth: JWT (Bearer)

### Autenticacion JWT
- `POST /api/accounts/login/` (publico)
  - Body:
    ```json
    {
      "username": "usuario@correo.com",
      "password": "tu_password"
    }
    ```
  - Respuesta: `access`, `refresh`, y claims adicionales del token: `username`, `email`, `grupos`, `full_name`.

- `POST /api/accounts/login/refresh/` (publico)
  - Body:
    ```json
    {"refresh": "<refresh_token>"}
    ```

- `POST /api/token/` (publico, JWT default)
- `POST /api/token/refresh/` (publico, JWT default)

---

## Accounts (`/api/accounts/`)

### Perfil propio
- `GET /api/accounts/perfil/me/` (auth requerida)
  - Respuesta:
    ```json
    {
      "Rol": "CLIENTE",
      "datos": { /* PerfilClienteSerializer */ }
    }
    ```
    o
    ```json
    {
      "rol": "TRABAJADOR",
      "datos": { /* PerfilTrabajadorSerializer */ }
    }
    ```

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
      "institucion_id": null
    }
    ```

### CRUD perfiles (auth requerida)
- `GET/POST /api/accounts/trabajadores/`
- `GET/PUT/PATCH/DELETE /api/accounts/trabajadores/<id>/`
- `GET/POST /api/accounts/clientes/`
- `GET/PUT/PATCH/DELETE /api/accounts/clientes/<id>/`

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
- Marcas:
  - `GET/POST /api/inventory/marcas/`
  - `GET/PUT/PATCH/DELETE /api/inventory/marcas/<id>/`
- Productos:
  - `GET/POST /api/inventory/productos/`
  - `GET/PUT/PATCH/DELETE /api/inventory/productos/<id>/`
- Lotes:
  - `GET/POST /api/inventory/lotes/`
  - `GET/PUT/PATCH/DELETE /api/inventory/lotes/<id>/`
- Inventarios:
  - `GET/POST /api/inventory/inventarios/`
  - `GET/PUT/PATCH/DELETE /api/inventory/inventarios/<id>/`
- Movimientos:
  - `GET/POST /api/inventory/movimientos/`
  - `GET /api/inventory/movimientos/<id>/`
- Traslados:
  - `GET/POST /api/inventory/traslados/`
  - `GET/PUT/PATCH/DELETE /api/inventory/traslados/<id>/`

---

## Orders (`/api/orders/`) (auth requerida)
- `POST /api/orders/pedidos/`
  - Body (ejemplo):
    ```json
    {
      "sucursal_origen_id": 1,
      "direccion_entrega_id": 3,
      "tipo_venta": "WEBPAY",
      "detalles": [
        {"producto_id": 5, "cantidad": 2},
        {"producto_id": 8, "cantidad": 1, "lote_id": 12}
      ]
    }
    ```

- `GET /api/orders/pedidos/<pedido_id>/`
- `POST /api/orders/pedidos/<pedido_id>/aprobar/`
  - Body:
    ```json
    {"accion": "APROBADO" | "RECHAZADO", "comentario": "..."}
    ```

---

## Logistics (`/api/logistics/`) (publico actualmente)
- `POST /api/logistics/cotizar/`
  - Body:
    ```json
    {"pedido_id": 42, "county_code_destino": "PROV"}
    ```
    o
    ```json
    {
      "sucursal_id": 1,
      "county_code_destino": "CONC",
      "productos": [
        {"peso_mg": 500000, "largo_mm": 200, "ancho_mm": 150, "alto_mm": 100, "cantidad": 3}
      ]
    }
    ```

- `POST /api/logistics/envios/`
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

- `GET /api/logistics/envios/<pedido_id>/tracking/`
  - Query param opcional: `?historial=true`

---

## Locations (`/api/locations/`) (publico)
- `GET /api/locations/regions/`
- `GET /api/locations/regions-with-comunas/`
- `GET /api/locations/comunas/`
  - Filtro opcional: `region_id`
- `GET /api/locations/comunas-chilexpress/`
  - Filtros opcionales: `retorna_respuesta`, `comuna_id`
- `GET /api/locations/sucursales/<id>/`
