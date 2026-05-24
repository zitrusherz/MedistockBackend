# API MEDISTOCK

## Base

- Base URL: `/api/`
- Formato: JSON
- Auth general: JWT Bearer en header `Authorization: Bearer <access>`
- Nota: los endpoints marcados como públicos no requieren JWT.

---

# Autenticación JWT

## Endpoints globales SimpleJWT

### Obtener token

- `POST /api/token/`
- Auth: pública

**Body:**

```json
{
  "username": "usuario@correo.com",
  "password": "tu_password"
}
```

**Respuesta:**

```json
{
  "refresh": "<refresh_token>",
  "access": "<access_token>"
}
```

---

### Refrescar token

- `POST /api/token/refresh/`
- Auth: pública

**Body:**

```json
{
  "refresh": "<refresh_token>"
}
```

**Respuesta:**

```json
{
  "access": "<nuevo_access_token>"
}
```

---

# Accounts (`/api/accounts/`)

## Login

### Iniciar sesión

- `POST /api/accounts/login/`
- Auth: pública

**Body:**

```json
{
  "username": "usuario@correo.com",
  "password": "tu_password"
}
```

**Respuesta:**

```json
{
  "refresh": "<refresh_token>",
  "access": "<access_token>"
}
```

El `access` incluye claims personalizados como:

```json
{
  "username": "usuario@correo.com",
  "email": "usuario@correo.com",
  "grupos": ["ClienteParticular"],
  "full_name": "Nombre Apellido"
}
```

---

### Refrescar login

- `POST /api/accounts/login/refresh/`
- Auth: pública

**Body:**

```json
{
  "refresh": "<refresh_token>"
}
```

---

### Cerrar sesión

- `POST /api/accounts/logout/`
- Auth: requerida

**Headers:**

```http
Authorization: Bearer <access_token>
Content-Type: application/json
```

**Body:**

```json
{
  "refresh": "<refresh_token>"
}
```

**Respuesta exitosa:**

- `205 RESET_CONTENT`

```json
{
  "detail": "Logout realizado correctamente."
}
```

---

## Registro

### Registrar trabajador

- `POST /api/accounts/registro/trabajador/`
- Auth: pública

**Body:**

```json
{
  "usuario": {
    "username": "trabajador@dominio.com",
    "email": "trabajador@dominio.com",
    "first_name": "Nombre",
    "last_name": "Apellido",
    "password": "Contraseña1",
    "password2": "Contraseña1"
  },
  "rut": "12345678-9",
  "telefono": "+56912345678",
  "direccion": "Av. Principal 123",
  "comuna": 1,
  "sucursal": 1,
  "cargo": "Operador Logístico"
}
```

**Validaciones principales:**

- `usuario.username` debe ser email valido.
- `usuario.password` y `usuario.password2` deben coincidir.
- `rut` no debe existir en perfiles de trabajador.

---

### Registrar cliente

- `POST /api/accounts/registro/cliente/`
- Auth: pública

**Descripción:** registra un usuario cliente, su perfil y su dirección de entrega inicial.

**Body para cliente particular:**

```json
{
  "usuario": {
    "username": "cliente@dominio.com",
    "email": "cliente@dominio.com",
    "first_name": "Nombre",
    "last_name": "Apellido",
    "password": "Contraseña1",
    "password2": "Contraseña1"
  },
  "rut": "12345678-9",
  "pasaporte": null,
  "tipo_cliente": "PARTICULAR",
  "telefono": "+56912345678",
  "institucion_id": null,
  "datos_institucion": null,
  "direccion_entrega": {
    "direccion": "Calle Falsa",
    "num_direccion": "123",
    "detalle_direccion": "Depto 201",
    "comuna": 485,
    "referencia": "Frente a una farmacia",
    "nombre_receptor": "Nombre Receptor",
    "telefono_receptor": "+56912345678",
    "es_principal": true
  }
}
```

**Reglas:**

- Se requiere `rut` o `pasaporte`, pero no ambos.
- `direccion_entrega` es obligatoria.
- Para `tipo_cliente = "PARTICULAR"`, no se debe enviar `institucion_id` ni `datos_institucion`.
- Para `tipo_cliente = "INSTITUCIONAL"`, `rut` es obligatorio y se debe enviar `institucion_id` o `datos_institucion`, pero no ambos.
- El backend debe validar duplicados de `username`, `email`, `rut` y `pasaporte` para evitar errores 500 por restricciones únicas.

**Ejemplo de error controlado por correo duplicado:**

```json
{
  "usuario": {
    "username": "Ya existe un usuario registrado con este correo."
  }
}
```

---

## Perfil propio

### Obtener mi perfil

- `GET /api/accounts/perfil/me/`
- Auth: requerida

**Headers:**

```http
Authorization: Bearer <access_token>
```

**Respuesta si es cliente:**

```json
{
  "rol": "CLIENTE",
  "datos": {
    "id": 1,
    "rut": "12345678-9",
    "pasaporte": null,
    "telefono": "+56912345678",
    "email": "cliente@dominio.com",
    "first_name": "Nombre",
    "last_name": "Apellido",
    "institucion": null
  }
}
```

**Respuesta si es trabajador:**

```json
{
  "rol": "TRABAJADOR",
  "datos": {
    "id": 1,
    "usuario": {},
    "rut": "12345678-9",
    "telefono": "+56912345678",
    "direccion": "Av. Principal 123",
    "comuna": 1,
    "sucursal": 1,
    "cargo": "Operador Logístico",
    "activo": true
  }
}
```

---

### Actualizar mi perfil

- `PATCH /api/accounts/perfil/me/`
- Auth: requerida
- Rol esperado: cliente

**Campos editables:**

```json
{
  "rut": "12345678-9",
  "pasaporte": null,
  "telefono": "+56912345678",
  "email": "cliente@dominio.com",
  "first_name": "Nombre",
  "last_name": "Apellido"
}
```

**Validaciones:**

- No permite vaciar campos que ya estaban informados.
- `email`, `first_name` y `last_name` no pueden ir vacíos si se envían.

---

## Direcciones de entrega del cliente autenticado

### Listar mis direcciones

- `GET /api/accounts/mis-direcciones/`
- Auth: requerida
- Rol esperado: cliente autenticado

**Descripción:** retorna las direcciones de entrega activas asociadas al cliente autenticado. El backend filtra automáticamente por el usuario del token, por lo que no se debe enviar `cliente_id`.

**Headers:**

```http
Authorization: Bearer <access_token>
```

**Body:** no requiere.

**Respuesta `200 OK`:**

```json
[
  {
    "id": 1,
    "direccion": "Calle Falsa",
    "num_direccion": "123",
    "detalle_direccion": "Depto 201",
    "comuna": 485,
    "referencia": "Frente a una farmacia",
    "nombre_receptor": "Nombre Receptor",
    "telefono_receptor": "+56912345678",
    "es_principal": true
  }
]
```

**Si no tiene direcciones:**

```json
[]
```

---

### Crear una dirección de entrega

- `POST /api/accounts/mis-direcciones/`
- Auth: requerida
- Rol esperado: cliente autenticado

**Descripción:** crea una dirección para el cliente autenticado. El backend asigna automáticamente el cliente usando el token JWT.

**Body:**

```json
{
  "direccion": "Calle Falsa",
  "num_direccion": "123",
  "detalle_direccion": "Depto 404",
  "comuna": 485,
  "referencia": "Frente a una farmacia",
  "nombre_receptor": "Nombre Receptor",
  "telefono_receptor": "+56912345678",
  "es_principal": true
}
```

**Campos:**

| Campo | Tipo | Obligatorio | Descripción |
|---|---:|---:|---|
| `direccion` | string | Sí | Calle o dirección principal. |
| `num_direccion` | string | No | Número de la dirección. |
| `detalle_direccion` | string | No | Departamento, oficina, block u otro detalle. |
| `comuna` | integer | Sí | ID interno de la comuna. |
| `referencia` | string | No | Referencia para despacho. |
| `nombre_receptor` | string | No | Persona que recibirá el pedido. |
| `telefono_receptor` | string | No | Teléfono de contacto del receptor. |
| `es_principal` | boolean | No | Indica si es la dirección principal. |

**Respuesta `201 Created`:**

```json
{
  "id": 2,
  "direccion": "Calle Falsa",
  "num_direccion": "123",
  "detalle_direccion": "Depto 404",
  "comuna": 485,
  "referencia": "Frente a una farmacia",
  "nombre_receptor": "Nombre Receptor",
  "telefono_receptor": "+56912345678",
  "es_principal": true
}
```

---

### Ver, editar o eliminar una dirección específica

- `GET /api/accounts/mis-direcciones/<id>/`
- `PATCH /api/accounts/mis-direcciones/<id>/`
- `PUT /api/accounts/mis-direcciones/<id>/`
- `DELETE /api/accounts/mis-direcciones/<id>/`
- Auth: requerida
- Rol esperado: cliente autenticado

**Descripción:** opera solo sobre direcciones pertenecientes al cliente autenticado.

**Ejemplo `PATCH`:**

```json
{
  "referencia": "Casa color blanco",
  "telefono_receptor": "+56987654321"
}
```

---

### Obtener dirección principal

- `GET /api/accounts/mis-direcciones/principal/`
- Auth: requerida
- Rol esperado: cliente autenticado

**Respuesta `200 OK`:** retorna la dirección con `es_principal=true`.

**Respuesta `404 Not Found`:**

```json
{
  "detail": "El cliente no tiene una dirección principal registrada."
}
```

---

## CRUD perfiles

### Trabajadores

- `GET/POST /api/accounts/trabajadores/`
- `GET/PUT/PATCH/DELETE /api/accounts/trabajadores/<id>/`
- Auth: requerida
- Respuesta: `PerfilTrabajadorSerializer`

### Clientes

- `GET/POST /api/accounts/clientes/`
- `GET/PUT/PATCH/DELETE /api/accounts/clientes/<id>/`
- Auth: requerida
- Respuesta: `PerfilClienteSerializer`

---

# Inventory (`/api/inventory/`)

## Públicos

### Catálogo de productos

- `GET /api/inventory/catalogo/`
- Auth: pública
- Filtros opcionales: `marca_id`, `categoria_id`, `sucursal_id`

**Respuesta por producto:**

```json
{
  "id": 1,
  "sku": "SKU123",
  "nombre": "Producto",
  "descripcion": "...",
  "valor_unitario": 1200,
  "marca": {
    "id": 2,
    "nombre": "Marca",
    "activo": true
  },
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
    {
      "sucursal_id": 1,
      "sucursal_nombre": "Sucursal",
      "stock_neto": 10
    }
  ]
}
```

---

### Catálogo de cajas

- `GET /api/inventory/catalogo-cajas/`
- Auth: pública
- Descripción: igual a `catalogo/`, pero filtrando productos con `es_caja=true`.

---

### Categorías públicas

- `GET /api/inventory/public/categorias/`
- Auth: pública

**Respuesta:**

```json
[
  {
    "id": 1,
    "nombre": "Insumos clínicos",
    "activo": true
  }
]
```

---

### Marcas públicas

- `GET /api/inventory/public/marcas/`
- Auth: pública

**Respuesta:**

```json
[
  {
    "id": 1,
    "nombre": "Marca",
    "activo": true
  }
]
```

---

### Detalle público de producto

- `GET /api/inventory/public/productos/<id>/`
- Auth: pública
- Respuesta: `ProductoSerializer`

---

## Privados

Todos los siguientes endpoints requieren JWT.

### Categorías

- `GET/POST /api/inventory/categorias/`
- `GET/PUT/PATCH/DELETE /api/inventory/categorias/<id>/`

**Campos:**

- `nombre` (string, requerido)
- `activo` (boolean, opcional)

### Marcas

- `GET/POST /api/inventory/marcas/`
- `GET/PUT/PATCH/DELETE /api/inventory/marcas/<id>/`

**Campos:**

- `nombre` (string, requerido)
- `activo` (boolean, opcional)

### Productos

- `GET/POST /api/inventory/productos/`
- `GET/PUT/PATCH/DELETE /api/inventory/productos/<id>/`
- Nota: `marca_id` es write-only; `categorias` se lee vía `categoriaproducto_set`.

**Campos principales (create/update):**

- `sku` (string)
- `nombre` (string, requerido)
- `descripcion` (string, opcional)
- `valor_unitario` (int, requerido, no negativo)
- `marca_id` (int, opcional)
- `unidad_medida` (string, opcional)
- `largo_mm`, `ancho_mm`, `alto_mm`, `peso_mg`, `volumen_ml` (int, opcional)
- `requiere_control_vencimiento` (boolean, opcional)
- `registro_sanitario` (string, opcional)
- `activo` (boolean, opcional)
- `es_caja` (boolean, opcional)

### Lotes

- `GET/POST /api/inventory/lotes/`
- `GET/PUT/PATCH/DELETE /api/inventory/lotes/<id>/`
- Nota: `producto_id` es write-only; `producto` se entrega resumido.

**Campos principales (create/update):**

- `producto_id` (int, requerido)
- `codigo_lote` (string)
- `fecha_elaboracion` (date, opcional)
- `fecha_vencimiento` (date, opcional, debe ser posterior a `fecha_elaboracion`)
- `activo` (boolean, opcional)

### Inventarios

- `GET/POST /api/inventory/inventarios/`
- `GET/PUT/PATCH/DELETE /api/inventory/inventarios/<id>/`
- Nota: `lote_id` es write-only; `lote` se entrega con detalle.

**Campos principales (create/update):**

- `lote_id` (int, requerido)
- `sucursal` (int, requerido)
- `cantidad_disponible` (int, requerido)
- `cantidad_reservada` (int, opcional)
- `stock_critico` (int, opcional)

**Validación:** `cantidad_reservada` no puede ser mayor a `cantidad_disponible`.

### Movimientos de inventario

- `GET/POST /api/inventory/movimientos/`
- `GET /api/inventory/movimientos/<id>/`
- Nota: el `usuario` se toma desde el request autenticado.

**Campos principales (create):**

- `inventario_id` (int, requerido)
- `pedido` (int, opcional)
- `compra_proveedor` (int, opcional)
- `traslado_inventario` (int, opcional)
- `tipo_movimiento` (string, requerido)
- `cantidad` (int, requerido, mayor a 0)
- `motivo` (string, opcional)
- `observacion` (string, opcional)

### Traslados de inventario

- `GET/POST /api/inventory/traslados/`
- `GET/PUT/PATCH/DELETE /api/inventory/traslados/<id>/`
- Nota: crear requiere `detalles_write`, lista de `{ "lote_id": 1, "cantidad": 2 }`, y setea `solicitado_por` desde el usuario autenticado.

**Campos principales (create):**

- `sucursal_origen` (int, requerido)
- `sucursal_destino` (int, requerido, debe ser distinta)
- `observacion` (string, opcional)
- `detalles_write` (lista, requerida)

**Validaciones:**

- `sucursal_origen` y `sucursal_destino` no pueden ser iguales.
- `detalles_write` debe incluir al menos un producto.

---

# Orders (`/api/orders/`)

Todos los endpoints de pedidos requieren JWT.

## Crear pedido

- `POST /api/orders/pedidos/`
- Auth: requerida
- Rol esperado: cliente

**Body:**

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
    {
      "producto_id": 5,
      "cantidad": 2
    },
    {
      "producto_id": 8,
      "cantidad": 1,
      "lote_id": 12
    }
  ]
}
```

**Respuesta:** `PedidoOutputSerializer`.

**Validaciones clave:**

- El usuario autenticado debe tener perfil de cliente.
- `direccion_entrega_id` debe pertenecer al cliente autenticado.
- Si se envia `lote_id`, debe existir en la sucursal indicada y tener stock.
- Si no se envia `lote_id`, el backend elige lote FEFO con stock.

---

## Obtener detalle de pedido

- `GET /api/orders/pedidos/<pedido_id>/`
- Auth: requerida
- Permisos: cliente dueño del pedido o trabajador interno.

---

## Editar pedido

- `PATCH /api/orders/pedidos/<pedido_id>/`
- Auth: requerida
- Rol esperado: cliente
- Condición: pedido en estado `PENDIENTE` o `APROBADO`.
- Body: `PedidoClienteUpdateSerializer`
- Respuesta: `PedidoOutputSerializer`

---

## Aprobar o rechazar pedido

- `POST /api/orders/pedidos/<pedido_id>/aprobar/`
- Auth: requerida
- Rol esperado: `Ejecutivo`, `Administrador` o `is_staff`

**Body:**

```json
{
  "accion": "APROBADO",
  "comentario": "Pedido aprobado para preparación."
}
```

También permite:

```json
{
  "accion": "RECHAZADO",
  "comentario": "Stock insuficiente."
}
```

**Respuesta:**

```json
{
  "pedido_id": 1,
  "estado_pedido": "APROBADO",
  "comentario": "Pedido aprobado para preparación."
}
```

---

## Mis pedidos

- `GET /api/orders/pedidos/mis-pedidos/`
- Auth: requerida
- Rol esperado: cliente

**Respuesta:** lista de `PedidoOutputSerializer`.

---

## Listar todos los pedidos

- `GET /api/orders/pedidos/todos/`
- Auth: requerida
- Rol esperado: `Ejecutivo`, `Administrador` o `is_staff`

**Respuesta:** lista de `PedidoOutputSerializer`.

---

# Payments (`/api/payments/`)

## Flujo Webpay Plus

El flujo general es:

```txt
Cliente crea pedido
↓
Cliente inicia pago Webpay
↓
Backend crea transacción local en TransaccionPago
↓
Backend crea transacción en Webpay
↓
Frontend redirige al usuario a Webpay
↓
Webpay retorna al backend con token_ws
↓
Backend confirma la transacción con Webpay
↓
Backend actualiza TransaccionPago como CONFIRMADO o RECHAZADO
↓
Backend redirige al frontend a la página de resultado
```

---

## Iniciar pago Webpay

- `POST /api/payments/webpay/iniciar/`
- Auth: requerida
- Rol esperado: cliente autenticado

**Descripción:** inicia una transacción Webpay para un pedido del cliente autenticado. El frontend solo debe enviar el `pedido_id`; el monto se obtiene desde el pedido en backend para evitar manipulación del total.

**Headers:**

```http
Authorization: Bearer <access_token>
Content-Type: application/json
```

**Body:**

```json
{
  "pedido_id": 2
}
```

**Validaciones principales:**

- El pedido debe existir.
- El pedido debe pertenecer al cliente autenticado.
- El usuario autenticado debe tener perfil de cliente.
- El total del pedido debe ser mayor a cero.
- Si ya existe una transacción Webpay activa para el pedido, puede retornar la transacción existente.

**Respuesta `201 Created`:**

```json
{
  "transaccion_pago_id": 1,
  "pedido_id": 2,
  "buy_order": "PED-2",
  "session_id": "USER-5-PED-2",
  "amount": 2147652,
  "token": "<token_ws>",
  "url": "https://webpay3gint.transbank.cl/webpayserver/initTransaction",
  "redirect_url": "https://webpay3gint.transbank.cl/webpayserver/initTransaction?token_ws=<token_ws>"
}
```

**Uso en frontend:**

```js
window.location.href = response.data.redirect_url;
```

**Errores posibles:**

```json
{
  "detail": "No existe un pedido con el ID indicado."
}
```

```json
{
  "detail": "No puedes pagar un pedido que no pertenece a tu cuenta."
}
```

```json
{
  "pedido_id": "El pedido no tiene un total válido para pagar."
}
```

---

## Confirmar pago Webpay

- `GET /api/payments/webpay/commit/?token_ws=<token_ws>`
- `POST /api/payments/webpay/commit/`
- Auth: pública

**Descripción:** endpoint de retorno usado por Webpay después de que el usuario finaliza el flujo de pago. No requiere JWT porque el usuario vuelve redirigido desde Transbank.

**GET con query param:**

```http
GET /api/payments/webpay/commit/?token_ws=<token_ws>
```

**POST opcional:**

```json
{
  "token_ws": "<token_ws>"
}
```

**Proceso interno:**

- Recibe `token_ws`.
- Llama a Webpay para confirmar la transacción.
- Busca la transacción local por `token_ws`.
- Valida que `buy_order` coincida con la transacción local.
- Valida que el monto devuelto por Webpay coincida con el monto local.
- Si Webpay aprueba, actualiza `estado_pago = "CONFIRMADO"`.
- Si Webpay rechaza, actualiza `estado_pago = "RECHAZADO"`.
- Guarda datos como `authorization_code`, `response_code`, `webpay_status`, `payment_type_code`, `installments_number`, últimos dígitos de tarjeta y `raw_response`.

**Errores posibles:**

- `404`: no existe transacción local para el `token_ws`.
- `400`: `buy_order` o `amount` devueltos por Webpay no coinciden con la transacción local.

**Si existe `FRONTEND_BASE_URL`, redirige a:**

```http
http://localhost:5173/resultado-pago?pedido_id=2&transaccion_id=1&estado=CONFIRMADO
```

**Respuesta JSON alternativa si no se redirige:**

```json
{
  "transaccion_pago_id": 1,
  "pedido_id": 2,
  "aprobada": true,
  "estado_pago": "CONFIRMADO",
  "webpay": {
    "token_ws": "<token_ws>",
    "response_code": 0,
    "status": "AUTHORIZED",
    "buy_order": "PED-2",
    "session_id": "USER-5-PED-2",
    "amount": 2147652,
    "authorization_code": "123456",
    "payment_type_code": "VD",
    "installments_number": 0,
    "card_detail": {
      "card_number": "6623"
    },
    "transaction_date": "2026-05-17T23:30:00Z",
    "aprobada": true
  }
}
```

---

## Consultar estado Webpay

- `GET /api/payments/webpay/estado/<token_ws>/`
- Auth: requerida

**Descripción:** consulta el estado de una transacción Webpay ya iniciada.

**Permisos:** si el usuario es cliente, solo puede consultar transacciones propias.

**Headers:**

```http
Authorization: Bearer <access_token>
```

**Respuesta:**

```json
{
  "transaccion_pago": {
    "id": 1,
    "pedido": 2,
    "pedido_id": 2,
    "pedido_total": 2147652,
    "metodo_pago": "WEBPAY",
    "estado_pago": "CONFIRMADO",
    "monto_confirmado": 2147652,
    "buy_order": "PED-2",
    "session_id": "USER-5-PED-2",
    "token_ws": "<token_ws>",
    "authorization_code": "123456",
    "response_code": 0,
    "payment_type_code": "VD",
    "installments_number": 0,
    "card_last_digits": "6623",
    "webpay_status": "AUTHORIZED",
    "transaction_date": "2026-05-17T23:30:00Z",
    "fecha_creacion": "2026-05-17T23:25:00Z",
    "fecha_confirmacion": "2026-05-17T23:31:00Z",
    "observacion": "Pago confirmado correctamente por Webpay."
  },
  "webpay": {
    "status": "AUTHORIZED",
    "response_code": 0,
    "aprobada": true
  }
}
```

---

## Listar mis pagos

- `GET /api/payments/mis-pagos/`
- Auth: requerida
- Rol esperado: cliente autenticado

**Descripción:** lista las transacciones de pago asociadas a los pedidos del cliente autenticado.

**Headers:**

```http
Authorization: Bearer <access_token>
```

**Respuesta:**

```json
[
  {
    "id": 1,
    "pedido": 2,
    "pedido_id": 2,
    "pedido_total": 2147652,
    "metodo_pago": "WEBPAY",
    "estado_pago": "CONFIRMADO",
    "monto_confirmado": 2147652,
    "buy_order": "PED-2",
    "session_id": "USER-5-PED-2",
    "token_ws": "<token_ws>",
    "id_transaccion_externa": "<token_ws>",
    "authorization_code": "123456",
    "response_code": 0,
    "payment_type_code": "VD",
    "installments_number": 0,
    "card_last_digits": "6623",
    "webpay_status": "AUTHORIZED",
    "transaction_date": "2026-05-17T23:30:00Z",
    "raw_response": {},
    "fecha_creacion": "2026-05-17T23:25:00Z",
    "fecha_confirmacion": "2026-05-17T23:31:00Z",
    "observacion": "Pago confirmado correctamente por Webpay."
  }
]
```

---

## Modelo de datos esperado para `TransaccionPago`

Para soportar Webpay correctamente, la tabla `transaccion_pago` debe tener campos como:

```txt
pedido
metodo_pago
estado_pago
monto_confirmado
buy_order
session_id
token_ws
id_transaccion_externa
authorization_code
response_code
payment_type_code
installments_number
card_last_digits
webpay_status
transaction_date
raw_response
fecha_creacion
fecha_confirmacion
observacion
```

Estados recomendados para `estado_pago`:

```txt
PENDIENTE
INICIADO
AUTORIZADO
CONFIRMADO
RECHAZADO
ANULADO
REEMBOLSADO
ERROR
```

---

# Logistics (`/api/logistics/`)

Todos los endpoints requieren JWT (IsAuthenticated).

## Cotizar envío

- `POST /api/logistics/cotizar/`
- Auth: requerida

### Modo 1: cotizar con pedido existente

**Body:**

```json
{
  "pedido_id": 42,
  "county_code_destino": "PROV"
}
```

### Modo 2: consulta libre sin pedido

**Body:**

```json
{
  "sucursal_id": 1,
  "county_code_destino": "CONC",
  "productos": [
    {
      "peso_mg": 500000,
      "largo_mm": 200,
      "ancho_mm": 150,
      "alto_mm": 100,
      "cantidad": 3
    }
  ]
}
```

**Respuesta:** `CotizacionOutputSerializer`.

**Validaciones clave:**

- Si no se indica `pedido_id`, se requiere `sucursal_id` y `productos`.
- `county_code_destino` debe existir en `ComunaChilexpress` con `retorna_respuesta=true`.
- Se usan cajas disponibles (`es_caja=true`) para calcular dimensiones reales.

---

## Crear envío / Orden de Transporte

- `POST /api/logistics/envios/`
- Auth: requerida
- Descripción: crea OT en Chilexpress para un pedido aprobado.

**Body:**

```json
{
  "pedido_id": 42,
  "service_type_code": 3,
  "label_type": 2,
  "contacto_nombre": "Nombre Cliente",
  "contacto_telefono": "+56912345678",
  "contacto_email": "cliente@dominio.com"
}
```

**Respuesta:**

```json
{
  "despacho": {},
  "numero_ot": 123,
  "num_cajas": 1,
  "etiqueta_disponible": true,
  "service_description": "..."
}
```

**Validaciones clave:**

- El pedido debe estar en estado `APROBADO` o `EN_PICKING`.
- No debe existir un despacho previo para el pedido.
- La sucursal y la dirección de entrega deben tener cobertura Chilexpress.

---

## Tracking de envío

- `GET /api/logistics/envios/<pedido_id>/tracking/`
- Auth: requerida
- Query param opcional: `historial=true`

**Ejemplo:**

```http
GET /api/logistics/envios/42/tracking/?historial=true
```

**Respuesta:** payload de tracking de Chilexpress.

---

# Locations (`/api/locations/`)

Endpoints públicos.

## Listar regiones

- `GET /api/locations/regions/`
- Auth: pública

**Respuesta:**

```json
[
  {
    "id": 13,
    "nombre": "METROPOLITANA",
    "chilexpress_region_id": "RM"
  }
]
```

---

## Listar regiones con comunas

- `GET /api/locations/regions-with-comunas/`
- Auth: pública

**Descripción:** devuelve regiones con sus comunas embebidas. Las comunas incluidas tienen cobertura Chilexpress con `retorna_respuesta=true`.

**Respuesta:**

```json
[
  {
    "id": 13,
    "nombre": "METROPOLITANA",
    "chilexpress_region_id": "RM",
    "comunas": [
      {
        "id": 485,
        "nombre": "SANTIAGO",
        "region": {
          "id": 13,
          "nombre": "METROPOLITANA",
          "chilexpress_region_id": "RM"
        },
        "chilexpress": {
          "county_code": "STGO",
          "county_name": "SANTIAGO",
          "coverage_name": "SANTIAGO",
          "retorna_respuesta": true
        }
      }
    ]
  }
]
```

---

## Listar comunas con cobertura Chilexpress

- `GET /api/locations/comunas/`
- Auth: pública
- Filtro opcional: `region_id`

**Ejemplo sin filtro:**

```http
GET /api/locations/comunas/
```

**Ejemplo con filtro:**

```http
GET /api/locations/comunas/?region_id=13
```

**Respuesta:**

```json
[
  {
    "id": 485,
    "nombre": "SANTIAGO",
    "region": {
      "id": 13,
      "nombre": "METROPOLITANA",
      "chilexpress_region_id": "RM"
    },
    "chilexpress": {
      "county_code": "STGO",
      "county_name": "SANTIAGO",
      "coverage_name": "SANTIAGO",
      "retorna_respuesta": true
    }
  }
]
```

**Nota importante:** `region_id` debe ser numérico. El frontend no debe enviar `region_id=undefined` ni `region_id=null` como texto.

**Error controlado recomendado:**

```json
{
  "region_id": "El parámetro region_id debe ser un número válido."
}
```

---

## Listar comunas Chilexpress

- `GET /api/locations/comunas-chilexpress/`
- Auth: pública
- Filtros opcionales:
  - `retorna_respuesta=true`
  - `retorna_respuesta=false`
  - `comuna_id=<id>`

**Ejemplos:**

```http
GET /api/locations/comunas-chilexpress/?retorna_respuesta=true
GET /api/locations/comunas-chilexpress/?comuna_id=485
```

**Respuesta:**

```json
[
  {
    "county_code": "STGO",
    "county_name": "SANTIAGO",
    "coverage_name": "SANTIAGO",
    "retorna_respuesta": true
  }
]
```

---

## Detalle público de sucursal

- `GET /api/locations/sucursales/<id>/`
- Auth: pública

**Descripción:** devuelve datos de una sucursal, incluyendo comuna y `county_code` Chilexpress si existe.

**Respuesta:**

```json
{
  "id": 1,
  "nombre": "Sucursal principal providencia",
  "direccion": "Av. Principal",
  "num_direccion": "123",
  "telefono": "+56212345678",
  "comuna": {
    "id": 485,
    "nombre": "SANTIAGO"
  },
  "county_code": "STGO",
  "activo": true
}
```

---

# Errores comunes

## 401 Unauthorized

Ocurre cuando un endpoint requiere JWT y no se envía token o el token es inválido/expirado.

```json
{
  "detail": "Las credenciales de autenticación no se proveyeron."
}
```

---

## 403 Forbidden

Ocurre cuando el usuario está autenticado, pero no tiene permisos para operar el recurso.

```json
{
  "detail": "No tienes permiso para realizar esta acción."
}
```

---

## 404 Not Found

Ocurre cuando no se encuentra el recurso solicitado.

```json
{
  "detail": "No encontrado."
}
```

---

## 400 Bad Request

Ocurre por datos inválidos de entrada.

```json
{
  "campo": "Mensaje de validación."
}
```

---

# Notas de integración

## Webpay

- Ambiente de integración: `https://webpay3gint.transbank.cl`
- Ambiente de producción: `https://webpay3g.transbank.cl`
- En ambiente de integración se usan credenciales de prueba.
- Al confirmar el pago, se debe validar que el `buy_order` y el `amount` devueltos por Webpay coincidan con la transacción local.
- El comercio debe mostrar una página de resultado o comprobante al usuario.

## Chilexpress

- Para cotizar envío se usa principalmente el `county_code` de la comuna destino.
- El endpoint recomendado para obtener comunas con `county_code` es:

```http
GET /api/locations/comunas/?region_id=<id_region>
```

- También puede usarse:

```http
GET /api/locations/regions-with-comunas/
```

para cargar regiones y comunas en una sola llamada inicial.
