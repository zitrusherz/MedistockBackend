# Documentacion API Medistock

## Convenciones generales

- **Base URL:** `<tu_host>/api`
- **Autenticacion:** JWT. Enviar en cada request como `Authorization: Bearer <token>`
- **Formato de fechas:** ISO 8601 (UTC). Ej: `"2025-07-10T14:32:00Z"`
- **Formato de fechas (date):** `YYYY-MM-DD`
- **Moneda:** Enteros en CLP (pesos chilenos). `50000` = $50.000
- **IVA:** 19%. `precio_con_iva` incluye IVA, `valor_unitario` es neto.
- **Paginacion:** Listados siguen el formato DRF `{ count, next, previous, results }` si hay paginacion configurada.
- **Errores de validacion:** JSON con clave por campo y arreglo de mensajes.

## Errores comunes

| Codigo | Cuando ocurre |
|--------|---------------|
| `200`  | OK - consulta exitosa |
| `201`  | Created - recurso creado |
| `205`  | Reset Content - logout exitoso |
| `400`  | Validacion fallida (campos incorrectos) |
| `401`  | Token ausente, expirado o invalido |
| `403`  | Sin permisos para esta accion |
| `404`  | Recurso no existe |
| `409`  | Conflicto de estado (stock / race condition) |
| `502`  | Error al comunicarse con servicio externo |

---

# Autenticacion

---

### POST Login JWT (custom)

Obtiene tokens JWT (access/refresh) con datos extra en el token.

**URL:** `POST /api/accounts/login/`
**Autenticacion:** No requerida
**Permisos:** Publico

#### Headers requeridos

| Header          | Valor              |
|-----------------|--------------------|
| `Content-Type`  | `application/json` |

#### Body (Request)

```json
{
  "username": "cliente@medistock.cl",
  "password": "TuPassword123"
}
```

**Descripcion de campos:**

| Campo      | Tipo     | Requerido | Default | Descripcion |
|------------|----------|-----------|---------|-------------|
| `username` | `string` | Si        | -       | Email/username del usuario |
| `password` | `string` | Si        | -       | Password del usuario |

#### Parametros de URL / Query params

No aplica.

#### Respuestas

**`200 OK`**

```json
{
  "refresh": "<refresh_token>",
  "access": "<access_token>"
}
```

**`401 Unauthorized`**

```json
{
  "detail": "No active account found with the given credentials"
}
```

#### Ejemplo completo

```javascript
const res = await fetch('/api/accounts/login/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ username: 'cliente@medistock.cl', password: 'TuPassword123' })
});
const data = await res.json();
```

---

### POST Refresh JWT (custom)

Renueva el access token usando refresh.

**URL:** `POST /api/accounts/login/refresh/`
**Autenticacion:** No requerida
**Permisos:** Publico

#### Headers requeridos

| Header          | Valor              |
|-----------------|--------------------|
| `Content-Type`  | `application/json` |

#### Body (Request)

```json
{
  "refresh": "<refresh_token>"
}
```

**Descripcion de campos:**

| Campo     | Tipo     | Requerido | Default | Descripcion |
|-----------|----------|-----------|---------|-------------|
| `refresh` | `string` | Si        | -       | Refresh token |

#### Parametros de URL / Query params

No aplica.

#### Respuestas

**`200 OK`**

```json
{
  "access": "<access_token>"
}
```

**`401 Unauthorized`**

```json
{
  "detail": "Token is invalid or expired"
}
```

#### Ejemplo completo

```javascript
const res = await fetch('/api/accounts/login/refresh/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ refresh: refreshToken })
});
const data = await res.json();
```

---

### POST Logout

Invalida un refresh token (blacklist).

**URL:** `POST /api/accounts/logout/`
**Autenticacion:** Requerida (JWT)
**Permisos:** Usuario autenticado

#### Headers requeridos

| Header          | Valor              |
|-----------------|--------------------|
| `Authorization` | `Bearer <token>`   |
| `Content-Type`  | `application/json` |

#### Body (Request)

```json
{
  "refresh": "<refresh_token>"
}
```

**Descripcion de campos:**

| Campo     | Tipo     | Requerido | Default | Descripcion |
|-----------|----------|-----------|---------|-------------|
| `refresh` | `string` | Si        | -       | Refresh token a invalidar |

#### Parametros de URL / Query params

No aplica.

#### Respuestas

**`205 Reset Content`**

```json
{
  "detail": "Logout realizado correctamente."
}
```

**`400 Bad Request`**

```json
{
  "error": "Debes enviar el refresh token."
}
```

**`401 Unauthorized`**

```json
{
  "detail": "Authentication credentials were not provided."
}
```

#### Ejemplo completo

```javascript
const res = await fetch('/api/accounts/logout/', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({ refresh: refreshToken })
});
const data = await res.json();
```

---

### POST Login JWT (simplejwt)

Alternativa directa a simplejwt.

**URL:** `POST /api/token/`
**Autenticacion:** No requerida
**Permisos:** Publico

#### Headers requeridos

| Header          | Valor              |
|-----------------|--------------------|
| `Content-Type`  | `application/json` |

#### Body (Request)

```json
{
  "username": "cliente@medistock.cl",
  "password": "TuPassword123"
}
```

#### Parametros de URL / Query params

No aplica.

#### Respuestas

**`200 OK`**

```json
{
  "refresh": "<refresh_token>",
  "access": "<access_token>"
}
```

#### Ejemplo completo

```javascript
const res = await fetch('/api/token/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ username, password })
});
const data = await res.json();
```

---

### POST Refresh JWT (simplejwt)

**URL:** `POST /api/token/refresh/`
**Autenticacion:** No requerida
**Permisos:** Publico

#### Headers requeridos

| Header          | Valor              |
|-----------------|--------------------|
| `Content-Type`  | `application/json` |

#### Body (Request)

```json
{
  "refresh": "<refresh_token>"
}
```

#### Parametros de URL / Query params

No aplica.

#### Respuestas

**`200 OK`**

```json
{
  "access": "<access_token>"
}
```

#### Ejemplo completo

```javascript
const res = await fetch('/api/token/refresh/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ refresh: refreshToken })
});
const data = await res.json();
```

---

# Cuentas

---

### GET Mi perfil

Retorna el perfil del usuario autenticado (cliente o trabajador).

**URL:** `GET /api/accounts/perfil/me/`
**Autenticacion:** Requerida (JWT)
**Permisos:** Usuario autenticado

#### Headers requeridos

| Header          | Valor            |
|-----------------|------------------|
| `Authorization` | `Bearer <token>` |

#### Body (Request)

No aplica.

#### Parametros de URL / Query params

No aplica.

#### Respuestas

**`200 OK`**

```json
{
  "rol": "CLIENTE",
  "datos": {
    "id": 7,
    "rut": "12345678-9",
    "pasaporte": null,
    "telefono": "987654321",
    "email": "cliente@medistock.cl",
    "first_name": "Juan",
    "last_name": "Perez",
    "institucion": 2,
    "direccion_principal": {
      "id": 3,
      "direccion": "Av. Siempre Viva",
      "num_direccion": "742",
      "detalle_direccion": "",
      "comuna": 10,
      "comuna_detalle": {"id": 10, "nombre": "Providencia"},
      "region": {"id": 1, "nombre": "Metropolitana"},
      "referencia": "",
      "nombre_receptor": "",
      "telefono_receptor": "",
      "es_principal": true
    }
  }
}
```

**`404 Not Found`**

```json
{
  "detail": "El usuario no tiene un perfil asociado."
}
```

#### Ejemplo completo

```javascript
const res = await fetch('/api/accounts/perfil/me/', {
  headers: { 'Authorization': `Bearer ${token}` }
});
const data = await res.json();
```

---

### PATCH Mi perfil (solo cliente)

Actualiza datos del perfil del cliente autenticado.

**URL:** `PATCH /api/accounts/perfil/me/`
**Autenticacion:** Requerida (JWT)
**Permisos:** Solo clientes

#### Headers requeridos

| Header          | Valor              |
|-----------------|--------------------|
| `Authorization` | `Bearer <token>`   |
| `Content-Type`  | `application/json` |

#### Body (Request)

```json
{
  "telefono": "987654321",
  "email": "nuevo@medistock.cl",
  "first_name": "Juan",
  "last_name": "Perez",
  "direccion": "Av. Siempre Viva",
  "num_direccion": "742",
  "detalle_direccion": "",
  "comuna": 10
}
```

**Descripcion de campos:**

| Campo               | Tipo      | Requerido | Default | Descripcion |
|---------------------|-----------|-----------|---------|-------------|
| `telefono`          | `string`  | No        | -       | Telefono cliente |
| `email`             | `string`  | No        | -       | Email usuario (tambien username) |
| `first_name`        | `string`  | No        | -       | Nombre usuario |
| `last_name`         | `string`  | No        | -       | Apellido usuario |
| `direccion`         | `string`  | No        | -       | Direccion principal |
| `num_direccion`     | `string`  | No        | -       | Numero direccion |
| `detalle_direccion` | `string`  | No        | -       | Detalle/Complemento |
| `comuna`            | `integer` | No        | -       | ID comuna |

#### Parametros de URL / Query params

No aplica.

#### Respuestas

**`200 OK`**

```json
{
  "rol": "CLIENTE",
  "datos": {
    "id": 7,
    "rut": "12345678-9",
    "pasaporte": null,
    "telefono": "987654321",
    "email": "nuevo@medistock.cl",
    "first_name": "Juan",
    "last_name": "Perez",
    "institucion": 2,
    "direccion_principal": {
      "id": 3,
      "direccion": "Av. Siempre Viva",
      "num_direccion": "742",
      "detalle_direccion": "",
      "comuna": 10,
      "comuna_detalle": {"id": 10, "nombre": "Providencia"},
      "region": {"id": 1, "nombre": "Metropolitana"},
      "referencia": "",
      "nombre_receptor": "",
      "telefono_receptor": "",
      "es_principal": true
    }
  }
}
```

**`403 Forbidden`**

```json
{
  "detail": "Solo los clientes pueden editar su perfil desde este endpoint."
}
```

#### Ejemplo completo

```javascript
const res = await fetch('/api/accounts/perfil/me/', {
  method: 'PATCH',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({ telefono: '987654321' })
});
const data = await res.json();
```

---

### POST Registro trabajador

Crea un usuario y perfil de trabajador.

**URL:** `POST /api/accounts/registro/trabajador/`
**Autenticacion:** No requerida
**Permisos:** Publico

#### Headers requeridos

| Header          | Valor              |
|-----------------|--------------------|
| `Content-Type`  | `application/json` |

#### Body (Request)

```json
{
  "usuario": {
    "username": "trabajador@medistock.cl",
    "email": "trabajador@medistock.cl",
    "first_name": "Maria",
    "last_name": "Gomez",
    "password": "Password123!",
    "password2": "Password123!"
  },
  "rut": "12345678-9",
  "telefono": "987654321",
  "direccion": "Calle 1",
  "comuna": 10,
  "sucursal": 2,
  "cargo": "Bodega"
}
```

**Descripcion de campos:**

| Campo           | Tipo      | Requerido | Default | Descripcion |
|-----------------|-----------|-----------|---------|-------------|
| `usuario`       | `object`  | Si        | -       | Datos de usuario (ver subtabla) |
| `rut`           | `string`  | Si        | -       | RUT trabajador |
| `telefono`      | `string`  | No        | -       | Telefono |
| `direccion`     | `string`  | No        | -       | Direccion |
| `comuna`        | `integer` | No        | -       | ID comuna |
| `sucursal`      | `integer` | No        | -       | ID sucursal |
| `cargo`         | `string`  | No        | -       | Cargo |

**Campos de `usuario`:**

| Campo        | Tipo     | Requerido | Default | Descripcion |
|--------------|----------|-----------|---------|-------------|
| `username`   | `string` | Si        | -       | Email/username |
| `email`      | `string` | Si        | -       | Email |
| `first_name` | `string` | Si        | -       | Nombre |
| `last_name`  | `string` | Si        | -       | Apellido |
| `password`   | `string` | Si        | -       | Password |
| `password2`  | `string` | Si        | -       | Confirmacion |

#### Parametros de URL / Query params

No aplica.

#### Respuestas

**`201 Created`**

```json
{
  "id": 10,
  "usuario": {
    "id": 33,
    "username": "trabajador@medistock.cl",
    "email": "trabajador@medistock.cl",
    "first_name": "Maria",
    "last_name": "Gomez"
  },
  "rut": "12345678-9",
  "telefono": "987654321",
  "direccion": "Calle 1",
  "comuna": 10,
  "sucursal": 2,
  "cargo": "Bodega",
  "activo": true
}
```

#### Ejemplo completo

```javascript
const res = await fetch('/api/accounts/registro/trabajador/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ usuario: { username, email, first_name, last_name, password, password2 }, rut })
});
const data = await res.json();
```

---

### POST Registro cliente

Crea usuario, perfil cliente e inserta direccion de entrega.

**URL:** `POST /api/accounts/registro/cliente/`
**Autenticacion:** No requerida
**Permisos:** Publico

#### Headers requeridos

| Header          | Valor              |
|-----------------|--------------------|
| `Content-Type`  | `application/json` |

#### Body (Request)

```json
{
  "usuario": {
    "username": "cliente@medistock.cl",
    "email": "cliente@medistock.cl",
    "first_name": "Juan",
    "last_name": "Perez",
    "password": "Password123!",
    "password2": "Password123!"
  },
  "rut": "12345678-9",
  "pasaporte": null,
  "tipo_cliente": "PARTICULAR",
  "telefono": "987654321",
  "institucion_id": null,
  "datos_institucion": null,
  "direccion_entrega": {
    "direccion": "Av. Siempre Viva",
    "num_direccion": "742",
    "detalle_direccion": "",
    "comuna": 10,
    "referencia": "",
    "nombre_receptor": "Juan Perez",
    "telefono_receptor": "987654321",
    "es_principal": true
  }
}
```

**Descripcion de campos:**

| Campo               | Tipo      | Requerido | Default | Descripcion |
|---------------------|-----------|-----------|---------|-------------|
| `usuario`           | `object`  | Si        | -       | Datos usuario (ver arriba) |
| `rut`               | `string`  | Cond.     | -       | Requerido si tipo INSTITUCIONAL |
| `pasaporte`         | `string`  | Cond.     | -       | Requerido si no hay RUT |
| `tipo_cliente`      | `string`  | Si        | -       | `PARTICULAR` o `INSTITUCIONAL` |
| `telefono`          | `string`  | No        | -       | Telefono |
| `institucion_id`    | `integer` | Cond.     | -       | ID institucion si existe |
| `datos_institucion` | `object`  | Cond.     | -       | Datos institucion nueva |
| `direccion_entrega` | `object`  | Si        | -       | Direccion inicial |

#### Parametros de URL / Query params

No aplica.

#### Respuestas

**`201 Created`**

```json
{
  "id": 7,
  "usuario": {
    "id": 55,
    "username": "cliente@medistock.cl",
    "email": "cliente@medistock.cl",
    "first_name": "Juan",
    "last_name": "Perez"
  },
  "rut": "12345678-9",
  "pasaporte": null,
  "tipo_cliente": "PARTICULAR",
  "telefono": "987654321",
  "institucion": null,
  "activo": true,
  "mensaje": "Cliente registrado correctamente."
}
```

#### Ejemplo completo

```javascript
const res = await fetch('/api/accounts/registro/cliente/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(payload)
});
const data = await res.json();
```

---

### GET Trabajadores

Lista trabajadores.

**URL:** `GET /api/accounts/trabajadores/`
**Autenticacion:** Requerida (JWT)
**Permisos:** Usuario autenticado

#### Headers requeridos

| Header          | Valor            |
|-----------------|------------------|
| `Authorization` | `Bearer <token>` |

#### Body (Request)

No aplica.

#### Parametros de URL / Query params

No aplica.

#### Respuestas

**`200 OK`**

```json
[
  {
    "id": 10,
    "usuario": {
      "id": 33,
      "username": "trabajador@medistock.cl",
      "email": "trabajador@medistock.cl",
      "first_name": "Maria",
      "last_name": "Gomez",
      "rut": "12345678-9",
      "grupos": [{"id": 2, "name": "Trabajadores"}],
      "is_active": true,
      "is_staff": false,
      "date_joined": "2025-07-10T14:32:00Z"
    },
    "rut": "12345678-9",
    "telefono": "987654321",
    "direccion": "Calle 1",
    "comuna": 10,
    "sucursal": 2,
    "cargo": "Bodega",
    "activo": true
  }
]
```

#### Ejemplo completo

```javascript
const res = await fetch('/api/accounts/trabajadores/', {
  headers: { 'Authorization': `Bearer ${token}` }
});
const data = await res.json();
```

---

### POST Trabajadores

Crea un trabajador (mismo payload del registro de trabajador).

**URL:** `POST /api/accounts/trabajadores/`
**Autenticacion:** Requerida (JWT)
**Permisos:** Usuario autenticado

#### Headers requeridos

| Header          | Valor              |
|-----------------|--------------------|
| `Authorization` | `Bearer <token>`   |
| `Content-Type`  | `application/json` |

#### Body (Request)

Ver endpoint `Registro trabajador`.

#### Parametros de URL / Query params

No aplica.

#### Respuestas

**`201 Created`** (ver ejemplo en registro de trabajador)

#### Ejemplo completo

```javascript
const res = await fetch('/api/accounts/trabajadores/', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify(payload)
});
const data = await res.json();
```

---

### GET Trabajador (detalle)

**URL:** `GET /api/accounts/trabajadores/{id}/`
**Autenticacion:** Requerida (JWT)
**Permisos:** Usuario autenticado

#### Headers requeridos

| Header          | Valor            |
|-----------------|------------------|
| `Authorization` | `Bearer <token>` |

#### Body (Request)

No aplica.

#### Parametros de URL / Query params

| Parametro | Tipo      | Descripcion |
|----------|-----------|-------------|
| `id`     | `integer` | ID del trabajador |

#### Respuestas

**`200 OK`**

```json
{
  "id": 10,
  "usuario": {
    "id": 33,
    "username": "trabajador@medistock.cl",
    "email": "trabajador@medistock.cl",
    "first_name": "Maria",
    "last_name": "Gomez",
    "rut": "12345678-9",
    "grupos": [{"id": 2, "name": "Trabajadores"}],
    "is_active": true,
    "is_staff": false,
    "date_joined": "2025-07-10T14:32:00Z"
  },
  "rut": "12345678-9",
  "telefono": "987654321",
  "direccion": "Calle 1",
  "comuna": 10,
  "sucursal": 2,
  "cargo": "Bodega",
  "activo": true
}
```

**`404 Not Found`**

```json
{
  "detail": "Not found."
}
```

#### Ejemplo completo

```javascript
const res = await fetch('/api/accounts/trabajadores/10/', {
  headers: { 'Authorization': `Bearer ${token}` }
});
const data = await res.json();
```

---

### PATCH/PUT Trabajador (editar)

**URL:** `PATCH /api/accounts/trabajadores/{id}/`
**Autenticacion:** Requerida (JWT)
**Permisos:** Usuario autenticado

#### Headers requeridos

| Header          | Valor              |
|-----------------|--------------------|
| `Authorization` | `Bearer <token>`   |
| `Content-Type`  | `application/json` |

#### Body (Request)

Campos del serializer `PerfilTrabajadorSerializer`:

| Campo       | Tipo      | Requerido | Default | Descripcion |
|-------------|-----------|-----------|---------|-------------|
| `rut`       | `string`  | No        | -       | RUT trabajador |
| `telefono`  | `string`  | No        | -       | Telefono |
| `direccion` | `string`  | No        | -       | Direccion |
| `comuna`    | `integer` | No        | -       | ID comuna |
| `sucursal`  | `integer` | No        | -       | ID sucursal |
| `cargo`     | `string`  | No        | -       | Cargo |
| `activo`    | `boolean` | No        | -       | Activo |

#### Parametros de URL / Query params

| Parametro | Tipo      | Descripcion |
|----------|-----------|-------------|
| `id`     | `integer` | ID del trabajador |

#### Respuestas

**`200 OK`**

```json
{
  "id": 10,
  "usuario": {
    "id": 33,
    "username": "trabajador@medistock.cl",
    "email": "trabajador@medistock.cl",
    "first_name": "Maria",
    "last_name": "Gomez",
    "rut": "12345678-9",
    "grupos": [{"id": 2, "name": "Trabajadores"}],
    "is_active": true,
    "is_staff": false,
    "date_joined": "2025-07-10T14:32:00Z"
  },
  "rut": "12345678-9",
  "telefono": "987654321",
  "direccion": "Calle 1",
  "comuna": 10,
  "sucursal": 2,
  "cargo": "Bodega",
  "activo": true
}
```

#### Ejemplo completo

```javascript
const res = await fetch('/api/accounts/trabajadores/10/', {
  method: 'PATCH',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({ activo: false })
});
const data = await res.json();
```

---

### DELETE Trabajador

**URL:** `DELETE /api/accounts/trabajadores/{id}/`
**Autenticacion:** Requerida (JWT)
**Permisos:** Usuario autenticado

#### Headers requeridos

| Header          | Valor            |
|-----------------|------------------|
| `Authorization` | `Bearer <token>` |

#### Body (Request)

No aplica.

#### Parametros de URL / Query params

| Parametro | Tipo      | Descripcion |
|----------|-----------|-------------|
| `id`     | `integer` | ID del trabajador |

#### Respuestas

**`204 No Content`** (sin body)

#### Ejemplo completo

```javascript
await fetch('/api/accounts/trabajadores/10/', {
  method: 'DELETE',
  headers: { 'Authorization': `Bearer ${token}` }
});
```

---

### GET Clientes

**URL:** `GET /api/accounts/clientes/`
**Autenticacion:** Requerida (JWT)
**Permisos:** Usuario autenticado

#### Headers requeridos

| Header          | Valor            |
|-----------------|------------------|
| `Authorization` | `Bearer <token>` |

#### Body (Request)

No aplica.

#### Parametros de URL / Query params

No aplica.

#### Respuestas

**`200 OK`**

```json
[
  {
    "id": 7,
    "usuario": {
      "id": 55,
      "username": "cliente@medistock.cl",
      "email": "cliente@medistock.cl",
      "first_name": "Juan",
      "last_name": "Perez",
      "rut": "12345678-9",
      "grupos": [{"id": 3, "name": "ClienteParticular"}],
      "is_active": true,
      "is_staff": false,
      "date_joined": "2025-07-10T14:32:00Z"
    },
    "rut": "12345678-9",
    "pasaporte": null,
    "tipo_cliente": "PARTICULAR",
    "telefono": "987654321",
    "institucion": {"id": 2, "razon_social": "Clinica X", "rut_empresa": "76123456-7"},
    "activo": true
  }
]
```

#### Ejemplo completo

```javascript
const res = await fetch('/api/accounts/clientes/', {
  headers: { 'Authorization': `Bearer ${token}` }
});
const data = await res.json();
```

---

### POST Clientes

**URL:** `POST /api/accounts/clientes/`
**Autenticacion:** Requerida (JWT)
**Permisos:** Usuario autenticado

#### Headers requeridos

| Header          | Valor              |
|-----------------|--------------------|
| `Authorization` | `Bearer <token>`   |
| `Content-Type`  | `application/json` |

#### Body (Request)

Ver endpoint `Registro cliente`.

#### Parametros de URL / Query params

No aplica.

#### Respuestas

**`201 Created`** (ver ejemplo en registro de cliente)

#### Ejemplo completo

```javascript
const res = await fetch('/api/accounts/clientes/', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify(payload)
});
const data = await res.json();
```

---

### GET Cliente (detalle)

**URL:** `GET /api/accounts/clientes/{id}/`
**Autenticacion:** Requerida (JWT)

#### Headers requeridos

| Header          | Valor            |
|-----------------|------------------|
| `Authorization` | `Bearer <token>` |

#### Body (Request)

No aplica.

#### Parametros de URL / Query params

| Parametro | Tipo      | Descripcion |
|----------|-----------|-------------|
| `id`     | `integer` | ID del cliente |

#### Respuestas

**`200 OK`**

```json
{
  "id": 7,
  "usuario": {
    "id": 55,
    "username": "cliente@medistock.cl",
    "email": "cliente@medistock.cl",
    "first_name": "Juan",
    "last_name": "Perez",
    "rut": "12345678-9",
    "grupos": [{"id": 3, "name": "ClienteParticular"}],
    "is_active": true,
    "is_staff": false,
    "date_joined": "2025-07-10T14:32:00Z"
  },
  "rut": "12345678-9",
  "pasaporte": null,
  "tipo_cliente": "PARTICULAR",
  "telefono": "987654321",
  "institucion": {"id": 2, "razon_social": "Clinica X", "rut_empresa": "76123456-7"},
  "activo": true
}
```

**`404 Not Found`**

```json
{
  "detail": "Not found."
}
```

#### Ejemplo completo

```javascript
const res = await fetch('/api/accounts/clientes/7/', {
  headers: { 'Authorization': `Bearer ${token}` }
});
const data = await res.json();
```

---

### PATCH/PUT Cliente (editar)

**URL:** `PATCH /api/accounts/clientes/{id}/`
**Autenticacion:** Requerida (JWT)

#### Headers requeridos

| Header          | Valor              |
|-----------------|--------------------|
| `Authorization` | `Bearer <token>`   |
| `Content-Type`  | `application/json` |

#### Body (Request)

Campos del serializer `PerfilClienteSerializer`:

| Campo          | Tipo     | Requerido | Default | Descripcion |
|----------------|----------|-----------|---------|-------------|
| `rut`          | `string` | No        | -       | RUT cliente |
| `pasaporte`    | `string` | No        | -       | Pasaporte |
| `tipo_cliente` | `string` | No        | -       | `PARTICULAR` o `INSTITUCIONAL` |
| `telefono`     | `string` | No        | -       | Telefono |
| `activo`       | `boolean`| No        | -       | Activo |

#### Parametros de URL / Query params

| Parametro | Tipo      | Descripcion |
|----------|-----------|-------------|
| `id`     | `integer` | ID del cliente |

#### Respuestas

**`200 OK`**

```json
{
  "id": 7,
  "usuario": {
    "id": 55,
    "username": "cliente@medistock.cl",
    "email": "cliente@medistock.cl",
    "first_name": "Juan",
    "last_name": "Perez",
    "rut": "12345678-9",
    "grupos": [{"id": 3, "name": "ClienteParticular"}],
    "is_active": true,
    "is_staff": false,
    "date_joined": "2025-07-10T14:32:00Z"
  },
  "rut": "12345678-9",
  "pasaporte": null,
  "tipo_cliente": "PARTICULAR",
  "telefono": "987654321",
  "institucion": {"id": 2, "razon_social": "Clinica X", "rut_empresa": "76123456-7"},
  "activo": true
}
```

#### Ejemplo completo

```javascript
const res = await fetch('/api/accounts/clientes/7/', {
  method: 'PATCH',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({ telefono: '11111111' })
});
const data = await res.json();
```

---

### DELETE Cliente

**URL:** `DELETE /api/accounts/clientes/{id}/`
**Autenticacion:** Requerida (JWT)

#### Headers requeridos

| Header          | Valor            |
|-----------------|------------------|
| `Authorization` | `Bearer <token>` |

#### Body (Request)

No aplica.

#### Parametros de URL / Query params

| Parametro | Tipo      | Descripcion |
|----------|-----------|-------------|
| `id`     | `integer` | ID del cliente |

#### Respuestas

**`204 No Content`** (sin body)

#### Ejemplo completo

```javascript
await fetch('/api/accounts/clientes/7/', {
  method: 'DELETE',
  headers: { 'Authorization': `Bearer ${token}` }
});
```

---

### GET Mis direcciones

Lista direcciones activas del cliente autenticado.

**URL:** `GET /api/accounts/mis-direcciones/`
**Autenticacion:** Requerida (JWT)
**Permisos:** Solo clientes

#### Headers requeridos

| Header          | Valor            |
|-----------------|------------------|
| `Authorization` | `Bearer <token>` |

#### Body (Request)

No aplica.

#### Parametros de URL / Query params

No aplica.

#### Respuestas

**`200 OK`**

```json
[
  {
    "id": 3,
    "direccion": "Av. Siempre Viva",
    "num_direccion": "742",
    "detalle_direccion": "",
    "comuna": 10,
    "comuna_detalle": {"id": 10, "nombre": "Providencia"},
    "region": {"id": 1, "nombre": "Metropolitana"},
    "referencia": "",
    "nombre_receptor": "Juan Perez",
    "telefono_receptor": "987654321",
    "es_principal": true
  }
]
```

#### Ejemplo completo

```javascript
const res = await fetch('/api/accounts/mis-direcciones/', {
  headers: { 'Authorization': `Bearer ${token}` }
});
const data = await res.json();
```

---

### POST Mis direcciones

**URL:** `POST /api/accounts/mis-direcciones/`
**Autenticacion:** Requerida (JWT)
**Permisos:** Solo clientes

#### Headers requeridos

| Header          | Valor              |
|-----------------|--------------------|
| `Authorization` | `Bearer <token>`   |
| `Content-Type`  | `application/json` |

#### Body (Request)

```json
{
  "direccion": "Av. Siempre Viva",
  "num_direccion": "742",
  "detalle_direccion": "",
  "comuna": 10,
  "referencia": "",
  "nombre_receptor": "Juan Perez",
  "telefono_receptor": "987654321",
  "es_principal": true
}
```

**Descripcion de campos:**

| Campo               | Tipo      | Requerido | Default | Descripcion |
|---------------------|-----------|-----------|---------|-------------|
| `direccion`         | `string`  | Si        | -       | Calle/Direccion |
| `num_direccion`     | `string`  | No        | -       | Numero |
| `detalle_direccion` | `string`  | No        | -       | Complemento |
| `comuna`            | `integer` | Si        | -       | ID comuna |
| `referencia`        | `string`  | No        | -       | Referencia |
| `nombre_receptor`   | `string`  | No        | -       | Nombre receptor |
| `telefono_receptor` | `string`  | No        | -       | Telefono receptor |
| `es_principal`      | `boolean` | No        | `false` | Marca principal |

#### Parametros de URL / Query params

No aplica.

#### Respuestas

**`201 Created`**

```json
{
  "id": 3,
  "direccion": "Av. Siempre Viva",
  "num_direccion": "742",
  "detalle_direccion": "",
  "comuna": 10,
  "comuna_detalle": {"id": 10, "nombre": "Providencia"},
  "region": {"id": 1, "nombre": "Metropolitana"},
  "referencia": "",
  "nombre_receptor": "Juan Perez",
  "telefono_receptor": "987654321",
  "es_principal": true
}
```

#### Ejemplo completo

```javascript
const res = await fetch('/api/accounts/mis-direcciones/', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify(payload)
});
const data = await res.json();
```

---

### GET Mis direcciones (detalle)

**URL:** `GET /api/accounts/mis-direcciones/{id}/`
**Autenticacion:** Requerida (JWT)

#### Headers requeridos

| Header          | Valor            |
|-----------------|------------------|
| `Authorization` | `Bearer <token>` |

#### Body (Request)

No aplica.

#### Parametros de URL / Query params

| Parametro | Tipo      | Descripcion |
|----------|-----------|-------------|
| `id`     | `integer` | ID de direccion |

#### Respuestas

**`200 OK`**

```json
{
  "id": 3,
  "direccion": "Av. Siempre Viva",
  "num_direccion": "742",
  "detalle_direccion": "",
  "comuna": 10,
  "comuna_detalle": {"id": 10, "nombre": "Providencia"},
  "region": {"id": 1, "nombre": "Metropolitana"},
  "referencia": "",
  "nombre_receptor": "Juan Perez",
  "telefono_receptor": "987654321",
  "es_principal": true
}
```

**`404 Not Found`**

```json
{
  "detail": "Not found."
}
```

#### Ejemplo completo

```javascript
const res = await fetch('/api/accounts/mis-direcciones/3/', {
  headers: { 'Authorization': `Bearer ${token}` }
});
const data = await res.json();
```

---

### PATCH/PUT Mis direcciones (editar)

**URL:** `PATCH /api/accounts/mis-direcciones/{id}/`
**Autenticacion:** Requerida (JWT)

#### Headers requeridos

| Header          | Valor              |
|-----------------|--------------------|
| `Authorization` | `Bearer <token>`   |
| `Content-Type`  | `application/json` |

#### Body (Request)

Campos del serializer `MiDireccionEntregaSerializer` (ver POST).

#### Parametros de URL / Query params

| Parametro | Tipo      | Descripcion |
|----------|-----------|-------------|
| `id`     | `integer` | ID de direccion |

#### Respuestas

**`200 OK`**

```json
{
  "id": 3,
  "direccion": "Av. Siempre Viva",
  "num_direccion": "742",
  "detalle_direccion": "",
  "comuna": 10,
  "comuna_detalle": {"id": 10, "nombre": "Providencia"},
  "region": {"id": 1, "nombre": "Metropolitana"},
  "referencia": "",
  "nombre_receptor": "Juan Perez",
  "telefono_receptor": "987654321",
  "es_principal": true
}
```

#### Ejemplo completo

```javascript
const res = await fetch('/api/accounts/mis-direcciones/3/', {
  method: 'PATCH',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({ es_principal: true })
});
const data = await res.json();
```

---

### DELETE Mis direcciones

**URL:** `DELETE /api/accounts/mis-direcciones/{id}/`
**Autenticacion:** Requerida (JWT)

#### Headers requeridos

| Header          | Valor            |
|-----------------|------------------|
| `Authorization` | `Bearer <token>` |

#### Body (Request)

No aplica.

#### Parametros de URL / Query params

| Parametro | Tipo      | Descripcion |
|----------|-----------|-------------|
| `id`     | `integer` | ID de direccion |

#### Respuestas

**`204 No Content`** (sin body)

#### Ejemplo completo

```javascript
await fetch('/api/accounts/mis-direcciones/3/', {
  method: 'DELETE',
  headers: { 'Authorization': `Bearer ${token}` }
});
```

---

### GET Direccion principal

Obtiene la direccion principal del cliente autenticado.

**URL:** `GET /api/accounts/mis-direcciones/principal/`
**Autenticacion:** Requerida (JWT)
**Permisos:** Solo clientes

#### Headers requeridos

| Header          | Valor            |
|-----------------|------------------|
| `Authorization` | `Bearer <token>` |

#### Body (Request)

No aplica.

#### Parametros de URL / Query params

No aplica.

#### Respuestas

**`200 OK`**

```json
{
  "id": 3,
  "direccion": "Av. Siempre Viva",
  "num_direccion": "742",
  "detalle_direccion": "",
  "comuna": 10,
  "comuna_detalle": {"id": 10, "nombre": "Providencia"},
  "region": {"id": 1, "nombre": "Metropolitana"},
  "referencia": "",
  "nombre_receptor": "Juan Perez",
  "telefono_receptor": "987654321",
  "es_principal": true
}
```

**`404 Not Found`**

```json
{
  "detail": "El cliente no tiene una direccion principal registrada."
}
```

#### Ejemplo completo

```javascript
const res = await fetch('/api/accounts/mis-direcciones/principal/', {
  headers: { 'Authorization': `Bearer ${token}` }
});
const data = await res.json();
```

---

# Inventario

---

### GET Categorias

**URL:** `GET /api/inventory/categorias/`
**Autenticacion:** Requerida (JWT)
**Permisos:** Usuario autenticado

#### Headers requeridos

| Header          | Valor            |
|-----------------|------------------|
| `Authorization` | `Bearer <token>` |

#### Body (Request)

No aplica.

#### Parametros de URL / Query params

No aplica.

#### Respuestas

**`200 OK`**

```json
[
  {"id": 1, "nombre": "Insumos", "activo": true}
]
```

#### Ejemplo completo

```javascript
const res = await fetch('/api/inventory/categorias/', {
  headers: { 'Authorization': `Bearer ${token}` }
});
const data = await res.json();
```

---

### POST Categorias

**URL:** `POST /api/inventory/categorias/`
**Autenticacion:** Requerida (JWT)

#### Headers requeridos

| Header          | Valor              |
|-----------------|--------------------|
| `Authorization` | `Bearer <token>`   |
| `Content-Type`  | `application/json` |

#### Body (Request)

```json
{
  "nombre": "Insumos",
  "activo": true
}
```

**Descripcion de campos:**

| Campo    | Tipo      | Requerido | Default | Descripcion |
|----------|-----------|-----------|---------|-------------|
| `nombre` | `string`  | Si        | -       | Nombre de categoria |
| `activo` | `boolean` | No        | `true`  | Activo/inactivo |

#### Parametros de URL / Query params

No aplica.

#### Respuestas

**`201 Created`**

```json
{"id": 1, "nombre": "Insumos", "activo": true}
```

#### Ejemplo completo

```javascript
const res = await fetch('/api/inventory/categorias/', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({ nombre: 'Insumos', activo: true })
});
const data = await res.json();
```

---

### GET Categoria (detalle)

**URL:** `GET /api/inventory/categorias/{id}/`
**Autenticacion:** Requerida (JWT)

#### Headers requeridos

| Header          | Valor            |
|-----------------|------------------|
| `Authorization` | `Bearer <token>` |

#### Body (Request)

No aplica.

#### Parametros de URL / Query params

| Parametro | Tipo      | Descripcion |
|----------|-----------|-------------|
| `id`     | `integer` | ID categoria |

#### Respuestas

**`200 OK`**

```json
{"id": 1, "nombre": "Insumos", "activo": true}
```

**`404 Not Found`**

```json
{"detail": "Not found."}
```

#### Ejemplo completo

```javascript
const res = await fetch('/api/inventory/categorias/1/', {
  headers: { 'Authorization': `Bearer ${token}` }
});
const data = await res.json();
```

---

### PATCH/PUT/DELETE Categoria

**URL:** `PATCH /api/inventory/categorias/{id}/`
**Autenticacion:** Requerida (JWT)

#### Headers requeridos

| Header          | Valor              |
|-----------------|--------------------|
| `Authorization` | `Bearer <token>`   |
| `Content-Type`  | `application/json` |

#### Body (Request)

Mismos campos del POST.

#### Parametros de URL / Query params

| Parametro | Tipo      | Descripcion |
|----------|-----------|-------------|
| `id`     | `integer` | ID categoria |

#### Respuestas

**`200 OK`** (para PATCH/PUT)

**`204 No Content`** (para DELETE)

#### Ejemplo completo

```javascript
const res = await fetch('/api/inventory/categorias/1/', {
  method: 'PATCH',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({ activo: false })
});
const data = await res.json();
```

---

### GET Categorias publicas

**URL:** `GET /api/inventory/public/categorias/`
**Autenticacion:** No requerida
**Permisos:** Publico

#### Headers requeridos

No aplica.

#### Body (Request)

No aplica.

#### Parametros de URL / Query params

No aplica.

#### Respuestas

**`200 OK`**

```json
[
  {"id": 1, "nombre": "Insumos", "activo": true}
]
```

#### Ejemplo completo

```javascript
const res = await fetch('/api/inventory/public/categorias/');
const data = await res.json();
```

---

### GET Marcas

**URL:** `GET /api/inventory/marcas/`
**Autenticacion:** Requerida (JWT)

#### Headers requeridos

| Header          | Valor            |
|-----------------|------------------|
| `Authorization` | `Bearer <token>` |

#### Body (Request)

No aplica.

#### Parametros de URL / Query params

No aplica.

#### Respuestas

**`200 OK`**

```json
[
  {"id": 1, "nombre": "ACME", "activo": true}
]
```

#### Ejemplo completo

```javascript
const res = await fetch('/api/inventory/marcas/', {
  headers: { 'Authorization': `Bearer ${token}` }
});
const data = await res.json();
```

---

### POST Marcas

**URL:** `POST /api/inventory/marcas/`
**Autenticacion:** Requerida (JWT)

#### Headers requeridos

| Header          | Valor              |
|-----------------|--------------------|
| `Authorization` | `Bearer <token>`   |
| `Content-Type`  | `application/json` |

#### Body (Request)

```json
{
  "nombre": "ACME",
  "activo": true
}
```

#### Parametros de URL / Query params

No aplica.

#### Respuestas

**`201 Created`**

```json
{"id": 1, "nombre": "ACME", "activo": true}
```

#### Ejemplo completo

```javascript
const res = await fetch('/api/inventory/marcas/', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({ nombre: 'ACME', activo: true })
});
const data = await res.json();
```

---

### GET Marca (detalle)

**URL:** `GET /api/inventory/marcas/{id}/`
**Autenticacion:** Requerida (JWT)

#### Headers requeridos

| Header          | Valor            |
|-----------------|------------------|
| `Authorization` | `Bearer <token>` |

#### Body (Request)

No aplica.

#### Parametros de URL / Query params

| Parametro | Tipo      | Descripcion |
|----------|-----------|-------------|
| `id`     | `integer` | ID marca |

#### Respuestas

**`200 OK`**

```json
{"id": 1, "nombre": "ACME", "activo": true}
```

**`404 Not Found`**

```json
{"detail": "Not found."}
```

#### Ejemplo completo

```javascript
const res = await fetch('/api/inventory/marcas/1/', {
  headers: { 'Authorization': `Bearer ${token}` }
});
const data = await res.json();
```

---

### PATCH/PUT/DELETE Marca

**URL:** `PATCH /api/inventory/marcas/{id}/`
**Autenticacion:** Requerida (JWT)

#### Headers requeridos

| Header          | Valor              |
|-----------------|--------------------|
| `Authorization` | `Bearer <token>`   |
| `Content-Type`  | `application/json` |

#### Body (Request)

Mismos campos del POST.

#### Parametros de URL / Query params

| Parametro | Tipo      | Descripcion |
|----------|-----------|-------------|
| `id`     | `integer` | ID marca |

#### Respuestas

**`200 OK`** (para PATCH/PUT)

**`204 No Content`** (para DELETE)

#### Ejemplo completo

```javascript
const res = await fetch('/api/inventory/marcas/1/', {
  method: 'PATCH',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({ activo: false })
});
const data = await res.json();
```

---

### GET Marcas publicas

**URL:** `GET /api/inventory/public/marcas/`
**Autenticacion:** No requerida

#### Headers requeridos

No aplica.

#### Body (Request)

No aplica.

#### Parametros de URL / Query params

No aplica.

#### Respuestas

**`200 OK`**

```json
[
  {"id": 1, "nombre": "ACME", "activo": true}
]
```

#### Ejemplo completo

```javascript
const res = await fetch('/api/inventory/public/marcas/');
const data = await res.json();
```

---

### GET Productos

**URL:** `GET /api/inventory/productos/`
**Autenticacion:** Requerida (JWT)

#### Headers requeridos

| Header          | Valor            |
|-----------------|------------------|
| `Authorization` | `Bearer <token>` |

#### Body (Request)

No aplica.

#### Parametros de URL / Query params

No aplica.

#### Respuestas

**`200 OK`**

```json
[
  {
    "id": 5,
    "sku": "JER-5ML-001",
    "nombre": "Jeringa 5ml",
    "descripcion": "",
    "valor_unitario": 350,
    "marca": {"id": 1, "nombre": "ACME", "activo": true},
    "marca_id": 1,
    "categorias": [{"id": 1, "categoria": {"id": 1, "nombre": "Insumos", "activo": true}}],
    "unidad_medida": "unidad",
    "largo_mm": 50,
    "ancho_mm": 20,
    "alto_mm": 20,
    "peso_mg": 30,
    "volumen_ml": 5,
    "requiere_control_vencimiento": true,
    "registro_sanitario": "REG-123",
    "activo": true,
    "es_caja": false
  }
]
```

#### Ejemplo completo

```javascript
const res = await fetch('/api/inventory/productos/', {
  headers: { 'Authorization': `Bearer ${token}` }
});
const data = await res.json();
```

---

### POST Productos

**URL:** `POST /api/inventory/productos/`
**Autenticacion:** Requerida (JWT)

#### Headers requeridos

| Header          | Valor              |
|-----------------|--------------------|
| `Authorization` | `Bearer <token>`   |
| `Content-Type`  | `application/json` |

#### Body (Request)

```json
{
  "sku": "JER-5ML-001",
  "nombre": "Jeringa 5ml",
  "descripcion": "",
  "valor_unitario": 350,
  "marca_id": 1,
  "unidad_medida": "unidad",
  "largo_mm": 50,
  "ancho_mm": 20,
  "alto_mm": 20,
  "peso_mg": 30,
  "volumen_ml": 5,
  "requiere_control_vencimiento": true,
  "registro_sanitario": "REG-123",
  "activo": true,
  "es_caja": false
}
```

#### Parametros de URL / Query params

No aplica.

#### Respuestas

**`201 Created`**

```json
{
  "id": 3,
  "direccion": "Av. Siempre Viva",
  "num_direccion": "742",
  "detalle_direccion": "",
  "comuna": 10,
  "comuna_detalle": {"id": 10, "nombre": "Providencia"},
  "region": {"id": 1, "nombre": "Metropolitana"},
  "referencia": "",
  "nombre_receptor": "Juan Perez",
  "telefono_receptor": "987654321",
  "es_principal": true
}
```

#### Ejemplo completo

```javascript
const res = await fetch('/api/inventory/productos/', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify(payload)
});
const data = await res.json();
```

---

### GET Producto (detalle)

**URL:** `GET /api/inventory/productos/{id}/`
**Autenticacion:** Requerida (JWT)

#### Headers requeridos

| Header          | Valor            |
|-----------------|------------------|
| `Authorization` | `Bearer <token>` |

#### Body (Request)

No aplica.

#### Parametros de URL / Query params

| Parametro | Tipo      | Descripcion |
|----------|-----------|-------------|
| `id`     | `integer` | ID producto |

#### Respuestas

**`200 OK`**

```json
{
  "id": 3,
  "direccion": "Av. Siempre Viva",
  "num_direccion": "742",
  "detalle_direccion": "",
  "comuna": 10,
  "comuna_detalle": {"id": 10, "nombre": "Providencia"},
  "region": {"id": 1, "nombre": "Metropolitana"},
  "referencia": "",
  "nombre_receptor": "Juan Perez",
  "telefono_receptor": "987654321",
  "es_principal": true
}
```

**`404 Not Found`**

```json
{"detail": "Not found."}
```

#### Ejemplo completo

```javascript
const res = await fetch('/api/inventory/productos/5/', {
  headers: { 'Authorization': `Bearer ${token}` }
});
const data = await res.json();
```

---

### PATCH/PUT/DELETE Producto

**URL:** `PATCH /api/inventory/productos/{id}/`
**Autenticacion:** Requerida (JWT)

#### Headers requeridos

| Header          | Valor              |
|-----------------|--------------------|
| `Authorization` | `Bearer <token>`   |
| `Content-Type`  | `application/json` |

#### Body (Request)

Mismos campos del POST.

#### Parametros de URL / Query params

| Parametro | Tipo      | Descripcion |
|----------|-----------|-------------|
| `id`     | `integer` | ID producto |

#### Respuestas

**`200 OK`** (para PATCH/PUT)

**`204 No Content`** (para DELETE)

#### Ejemplo completo

```javascript
const res = await fetch('/api/inventory/productos/5/', {
  method: 'PATCH',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({ activo: false })
});
const data = await res.json();
```

---

### GET Producto publico (detalle)

**URL:** `GET /api/inventory/public/productos/{id}/`
**Autenticacion:** No requerida
**Permisos:** Publico

#### Headers requeridos

No aplica.

#### Body (Request)

No aplica.

#### Parametros de URL / Query params

| Parametro | Tipo      | Descripcion |
|----------|-----------|-------------|
| `id`     | `integer` | ID producto |

#### Respuestas

**`200 OK`**

```json
{
  "id": 3,
  "direccion": "Av. Siempre Viva",
  "num_direccion": "742",
  "detalle_direccion": "",
  "comuna": 10,
  "comuna_detalle": {"id": 10, "nombre": "Providencia"},
  "region": {"id": 1, "nombre": "Metropolitana"},
  "referencia": "",
  "nombre_receptor": "Juan Perez",
  "telefono_receptor": "987654321",
  "es_principal": true
}
```

**`404 Not Found`**

```json
{"detail": "Not found."}
```

#### Ejemplo completo

```javascript
const res = await fetch('/api/inventory/public/productos/5/');
const data = await res.json();
```

---

### GET Lotes

**URL:** `GET /api/inventory/lotes/`
**Autenticacion:** Requerida (JWT)

#### Headers requeridos

| Header          | Valor            |
|-----------------|------------------|
| `Authorization` | `Bearer <token>` |

#### Body (Request)

No aplica.

#### Parametros de URL / Query params

No aplica.

#### Respuestas

**`200 OK`**

```json
[
  {
    "id": 9,
    "producto": {"id": 5, "sku": "JER-5ML-001", "nombre": "Jeringa 5ml", "valor_unitario": 350, "precio_con_iva": 417, "marca_nombre": "ACME", "unidad_medida": "unidad"},
    "producto_id": 5,
    "codigo_lote": "LOT-2025-A",
    "fecha_elaboracion": "2025-01-01",
    "fecha_vencimiento": "2026-01-01",
    "dias_para_vencer": 300,
    "activo": true
  }
]
```

#### Ejemplo completo

```javascript
const res = await fetch('/api/inventory/lotes/', {
  headers: { 'Authorization': `Bearer ${token}` }
});
const data = await res.json();
```

---

### POST Lotes

**URL:** `POST /api/inventory/lotes/`
**Autenticacion:** Requerida (JWT)

#### Headers requeridos

| Header          | Valor              |
|-----------------|--------------------|
| `Authorization` | `Bearer <token>`   |
| `Content-Type`  | `application/json` |

#### Body (Request)

```json
{
  "producto_id": 5,
  "codigo_lote": "LOT-2025-A",
  "fecha_elaboracion": "2025-01-01",
  "fecha_vencimiento": "2026-01-01",
  "activo": true
}
```

#### Parametros de URL / Query params

No aplica.

#### Respuestas

**`201 Created`**

```json
{
  "id": 9,
  "producto": {"id": 5, "sku": "JER-5ML-001", "nombre": "Jeringa 5ml", "valor_unitario": 350, "precio_con_iva": 417, "marca_nombre": "ACME", "unidad_medida": "unidad"},
  "producto_id": 5,
  "codigo_lote": "LOT-2025-A",
  "fecha_elaboracion": "2025-01-01",
  "fecha_vencimiento": "2026-01-01",
  "dias_para_vencer": 300,
  "activo": true
}
```

#### Ejemplo completo

```javascript
const res = await fetch('/api/inventory/lotes/', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify(payload)
});
const data = await res.json();
```

---

### GET Lote (detalle)

**URL:** `GET /api/inventory/lotes/{id}/`
**Autenticacion:** Requerida (JWT)

#### Headers requeridos

| Header          | Valor            |
|-----------------|------------------|
| `Authorization` | `Bearer <token>` |

#### Body (Request)

No aplica.

#### Parametros de URL / Query params

| Parametro | Tipo      | Descripcion |
|----------|-----------|-------------|
| `id`     | `integer` | ID lote |

#### Respuestas

**`200 OK`**

```json
{
  "id": 3,
  "direccion": "Av. Siempre Viva",
  "num_direccion": "742",
  "detalle_direccion": "",
  "comuna": 10,
  "comuna_detalle": {"id": 10, "nombre": "Providencia"},
  "region": {"id": 1, "nombre": "Metropolitana"},
  "referencia": "",
  "nombre_receptor": "Juan Perez",
  "telefono_receptor": "987654321",
  "es_principal": true
}
```

**`404 Not Found`**

```json
{"detail": "Not found."}
```

#### Ejemplo completo

```javascript
const res = await fetch('/api/inventory/lotes/9/', {
  headers: { 'Authorization': `Bearer ${token}` }
});
const data = await res.json();
```

---

### PATCH/PUT/DELETE Lote

**URL:** `PATCH /api/inventory/lotes/{id}/`
**Autenticacion:** Requerida (JWT)

#### Headers requeridos

| Header          | Valor              |
|-----------------|--------------------|
| `Authorization` | `Bearer <token>`   |
| `Content-Type`  | `application/json` |

#### Body (Request)

Mismos campos del POST.

#### Parametros de URL / Query params

| Parametro | Tipo      | Descripcion |
|----------|-----------|-------------|
| `id`     | `integer` | ID lote |

#### Respuestas

**`200 OK`** (para PATCH/PUT)

**`204 No Content`** (para DELETE)

#### Ejemplo completo

```javascript
const res = await fetch('/api/inventory/lotes/9/', {
  method: 'PATCH',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({ activo: false })
});
const data = await res.json();
```

---

### GET Inventarios

**URL:** `GET /api/inventory/inventarios/`
**Autenticacion:** Requerida (JWT)

#### Headers requeridos

| Header          | Valor            |
|-----------------|------------------|
| `Authorization` | `Bearer <token>` |

#### Body (Request)

No aplica.

#### Parametros de URL / Query params

No aplica.

#### Respuestas

**`200 OK`**

```json
[
  {
    "id": 10,
    "lote": {
      "id": 9,
      "producto": {"id": 5, "sku": "JER-5ML-001", "nombre": "Jeringa 5ml", "valor_unitario": 350, "precio_con_iva": 417, "marca_nombre": "ACME", "unidad_medida": "unidad"},
      "producto_id": 5,
      "codigo_lote": "LOT-2025-A",
      "fecha_elaboracion": "2025-01-01",
      "fecha_vencimiento": "2026-01-01",
      "dias_para_vencer": 300,
      "activo": true
    },
    "lote_id": 9,
    "sucursal": 1,
    "sucursal_nombre": "Sucursal Providencia",
    "cantidad_disponible": 100,
    "cantidad_reservada": 0,
    "stock_neto": 100,
    "stock_critico": 10,
    "alerta_stock_critico": false,
    "fecha_actualizacion": "2025-07-10T14:32:00Z"
  }
]
```

#### Ejemplo completo

```javascript
const res = await fetch('/api/inventory/inventarios/', {
  headers: { 'Authorization': `Bearer ${token}` }
});
const data = await res.json();
```

---

### POST Inventarios

**URL:** `POST /api/inventory/inventarios/`
**Autenticacion:** Requerida (JWT)

#### Headers requeridos

| Header          | Valor              |
|-----------------|--------------------|
| `Authorization` | `Bearer <token>`   |
| `Content-Type`  | `application/json` |

#### Body (Request)

```json
{
  "lote_id": 9,
  "sucursal": 1,
  "cantidad_disponible": 100,
  "cantidad_reservada": 0,
  "stock_critico": 10
}
```

#### Parametros de URL / Query params

No aplica.

#### Respuestas

**`201 Created`**

```json
{
  "id": 10,
  "lote": {
    "id": 9,
    "producto": {"id": 5, "sku": "JER-5ML-001", "nombre": "Jeringa 5ml", "valor_unitario": 350, "precio_con_iva": 417, "marca_nombre": "ACME", "unidad_medida": "unidad"},
    "producto_id": 5,
    "codigo_lote": "LOT-2025-A",
    "fecha_elaboracion": "2025-01-01",
    "fecha_vencimiento": "2026-01-01",
    "dias_para_vencer": 300,
    "activo": true
  },
  "lote_id": 9,
  "sucursal": 1,
  "sucursal_nombre": "Sucursal Providencia",
  "cantidad_disponible": 100,
  "cantidad_reservada": 0,
  "stock_neto": 100,
  "stock_critico": 10,
  "alerta_stock_critico": false,
  "fecha_actualizacion": "2025-07-10T14:32:00Z"
}
```

#### Ejemplo completo

```javascript
const res = await fetch('/api/inventory/inventarios/', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify(payload)
});
const data = await res.json();
```

---

### GET Inventario (detalle)

**URL:** `GET /api/inventory/inventarios/{id}/`
**Autenticacion:** Requerida (JWT)

#### Headers requeridos

| Header          | Valor            |
|-----------------|------------------|
| `Authorization` | `Bearer <token>` |

#### Body (Request)

No aplica.

#### Parametros de URL / Query params

| Parametro | Tipo      | Descripcion |
|----------|-----------|-------------|
| `id`     | `integer` | ID inventario |

#### Respuestas

**`200 OK`**

```json
{
  "id": 10,
  "lote": {
    "id": 9,
    "producto": {"id": 5, "sku": "JER-5ML-001", "nombre": "Jeringa 5ml", "valor_unitario": 350, "precio_con_iva": 417, "marca_nombre": "ACME", "unidad_medida": "unidad"},
    "producto_id": 5,
    "codigo_lote": "LOT-2025-A",
    "fecha_elaboracion": "2025-01-01",
    "fecha_vencimiento": "2026-01-01",
    "dias_para_vencer": 300,
    "activo": true
  },
  "lote_id": 9,
  "sucursal": 1,
  "sucursal_nombre": "Sucursal Providencia",
  "cantidad_disponible": 100,
  "cantidad_reservada": 0,
  "stock_neto": 100,
  "stock_critico": 10,
  "alerta_stock_critico": false,
  "fecha_actualizacion": "2025-07-10T14:32:00Z"
}
```

**`404 Not Found`**

```json
{"detail": "Not found."}
```

#### Ejemplo completo

```javascript
const res = await fetch('/api/inventory/inventarios/10/', {
  headers: { 'Authorization': `Bearer ${token}` }
});
const data = await res.json();
```

---

### PATCH/PUT/DELETE Inventario

**URL:** `PATCH /api/inventory/inventarios/{id}/`
**Autenticacion:** Requerida (JWT)

#### Headers requeridos

| Header          | Valor              |
|-----------------|--------------------|
| `Authorization` | `Bearer <token>`   |
| `Content-Type`  | `application/json` |

#### Body (Request)

Mismos campos del POST.

#### Parametros de URL / Query params

| Parametro | Tipo      | Descripcion |
|----------|-----------|-------------|
| `id`     | `integer` | ID inventario |

#### Respuestas

**`200 OK`** (para PATCH/PUT)

**`204 No Content`** (para DELETE)

#### Ejemplo completo

```javascript
const res = await fetch('/api/inventory/inventarios/10/', {
  method: 'PATCH',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({ stock_critico: 5 })
});
const data = await res.json();
```

---

### GET Movimientos de inventario

**URL:** `GET /api/inventory/movimientos/`
**Autenticacion:** Requerida (JWT)

#### Headers requeridos

| Header          | Valor            |
|-----------------|------------------|
| `Authorization` | `Bearer <token>` |

#### Body (Request)

No aplica.

#### Parametros de URL / Query params

No aplica.

#### Respuestas

**`200 OK`**

```json
[
  {
    "id": 50,
    "inventario_id": 10,
    "usuario": 1,
    "usuario_nombre": "Admin User",
    "pedido": 42,
    "compra_proveedor": null,
    "traslado_inventario": null,
    "tipo_movimiento": "ENTRADA",
    "tipo_movimiento_display": "Entrada",
    "cantidad": 5,
    "fecha_movimiento": "2025-07-10T14:32:00Z",
    "motivo": "Ingreso",
    "observacion": ""
  }
]
```

#### Ejemplo completo

```javascript
const res = await fetch('/api/inventory/movimientos/', {
  headers: { 'Authorization': `Bearer ${token}` }
});
const data = await res.json();
```

---

### POST Movimiento de inventario

**URL:** `POST /api/inventory/movimientos/`
**Autenticacion:** Requerida (JWT)

#### Headers requeridos

| Header          | Valor              |
|-----------------|--------------------|
| `Authorization` | `Bearer <token>`   |
| `Content-Type`  | `application/json` |

#### Body (Request)

```json
{
  "inventario_id": 10,
  "pedido": 42,
  "compra_proveedor": null,
  "traslado_inventario": null,
  "tipo_movimiento": "ENTRADA",
  "cantidad": 5,
  "motivo": "Ingreso",
  "observacion": ""
}
```

**Valores permitidos `tipo_movimiento`:**

| Valor | Descripcion |
|-------|-------------|
| `ENTRADA` | Entrada |
| `SALIDA` | Salida |
| `AJUSTE` | Ajuste |
| `MERMA` | Merma |
| `DEVOLUCION` | Devolucion |
| `TRASLADO` | Traslado |
| `RESERVA` | Reserva |

#### Parametros de URL / Query params

No aplica.

#### Respuestas

**`201 Created`**

```json
{
  "id": 50,
  "inventario_id": 10,
  "usuario": 1,
  "usuario_nombre": "Admin User",
  "pedido": 42,
  "compra_proveedor": null,
  "traslado_inventario": null,
  "tipo_movimiento": "ENTRADA",
  "tipo_movimiento_display": "Entrada",
  "cantidad": 5,
  "fecha_movimiento": "2025-07-10T14:32:00Z",
  "motivo": "Ingreso",
  "observacion": ""
}
```

#### Ejemplo completo

```javascript
const res = await fetch('/api/inventory/movimientos/', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify(payload)
});
const data = await res.json();
```

---

### GET Movimiento (detalle)

**URL:** `GET /api/inventory/movimientos/{id}/`
**Autenticacion:** Requerida (JWT)

#### Headers requeridos

| Header          | Valor            |
|-----------------|------------------|
| `Authorization` | `Bearer <token>` |

#### Body (Request)

No aplica.

#### Parametros de URL / Query params

| Parametro | Tipo      | Descripcion |
|----------|-----------|-------------|
| `id`     | `integer` | ID movimiento |

#### Respuestas

**`200 OK`**

```json
{
  "id": 50,
  "inventario_id": 10,
  "usuario": 1,
  "usuario_nombre": "Admin User",
  "pedido": 42,
  "compra_proveedor": null,
  "traslado_inventario": null,
  "tipo_movimiento": "ENTRADA",
  "tipo_movimiento_display": "Entrada",
  "cantidad": 5,
  "fecha_movimiento": "2025-07-10T14:32:00Z",
  "motivo": "Ingreso",
  "observacion": ""
}
```

**`404 Not Found`**

```json
{"detail": "Not found."}
```

#### Ejemplo completo

```javascript
const res = await fetch('/api/inventory/movimientos/50/', {
  headers: { 'Authorization': `Bearer ${token}` }
});
const data = await res.json();
```

---

### GET Traslados

**URL:** `GET /api/inventory/traslados/`
**Autenticacion:** Requerida (JWT)

#### Headers requeridos

| Header          | Valor            |
|-----------------|------------------|
| `Authorization` | `Bearer <token>` |

#### Body (Request)

No aplica.

#### Parametros de URL / Query params

No aplica.

#### Respuestas

**`200 OK`**

```json
[
  {
    "id": 3,
    "sucursal_origen": 1,
    "sucursal_origen_nombre": "Sucursal A",
    "sucursal_destino": 2,
    "sucursal_destino_nombre": "Sucursal B",
    "solicitado_por": 10,
    "fecha_solicitud": "2025-07-10T14:32:00Z",
    "fecha_envio": null,
    "fecha_recepcion": null,
    "estado": "SOLICITADO",
    "observacion": "",
    "detalles": [
      {"id": 1, "lote": {"id": 9, "codigo_lote": "LOT-2025-A", "fecha_vencimiento": "2026-01-01"}, "lote_id": 9, "cantidad": 10}
    ]
  }
]
```

#### Ejemplo completo

```javascript
const res = await fetch('/api/inventory/traslados/', {
  headers: { 'Authorization': `Bearer ${token}` }
});
const data = await res.json();
```

---

### POST Traslados

**URL:** `POST /api/inventory/traslados/`
**Autenticacion:** Requerida (JWT)

#### Headers requeridos

| Header          | Valor              |
|-----------------|--------------------|
| `Authorization` | `Bearer <token>`   |
| `Content-Type`  | `application/json` |

#### Body (Request)

```json
{
  "sucursal_origen": 1,
  "sucursal_destino": 2,
  "observacion": "",
  "detalles_write": [
    {"lote_id": 9, "cantidad": 10}
  ]
}
```

#### Parametros de URL / Query params

No aplica.

#### Respuestas

**`201 Created`**

```json
{
  "id": 3,
  "sucursal_origen": 1,
  "sucursal_origen_nombre": "Sucursal A",
  "sucursal_destino": 2,
  "sucursal_destino_nombre": "Sucursal B",
  "solicitado_por": 10,
  "fecha_solicitud": "2025-07-10T14:32:00Z",
  "fecha_envio": null,
  "fecha_recepcion": null,
  "estado": "SOLICITADO",
  "observacion": "",
  "detalles": [
    {"id": 1, "lote": {"id": 9, "codigo_lote": "LOT-2025-A", "fecha_vencimiento": "2026-01-01"}, "lote_id": 9, "cantidad": 10}
  ]
}
```

#### Ejemplo completo

```javascript
const res = await fetch('/api/inventory/traslados/', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify(payload)
});
const data = await res.json();
```

---

### GET Traslado (detalle)

**URL:** `GET /api/inventory/traslados/{id}/`
**Autenticacion:** Requerida (JWT)

#### Headers requeridos

| Header          | Valor            |
|-----------------|------------------|
| `Authorization` | `Bearer <token>` |

#### Body (Request)

No aplica.

#### Parametros de URL / Query params

| Parametro | Tipo      | Descripcion |
|----------|-----------|-------------|
| `id`     | `integer` | ID traslado |

#### Respuestas

**`200 OK`**

```json
{
  "id": 3,
  "sucursal_origen": 1,
  "sucursal_origen_nombre": "Sucursal A",
  "sucursal_destino": 2,
  "sucursal_destino_nombre": "Sucursal B",
  "solicitado_por": 10,
  "fecha_solicitud": "2025-07-10T14:32:00Z",
  "fecha_envio": null,
  "fecha_recepcion": null,
  "estado": "SOLICITADO",
  "observacion": "",
  "detalles": [
    {"id": 1, "lote": {"id": 9, "codigo_lote": "LOT-2025-A", "fecha_vencimiento": "2026-01-01"}, "lote_id": 9, "cantidad": 10}
  ]
}
```

**`404 Not Found`**

```json
{"detail": "Not found."}
```

#### Ejemplo completo

```javascript
const res = await fetch('/api/inventory/traslados/3/', {
  headers: { 'Authorization': `Bearer ${token}` }
});
const data = await res.json();
```

---

### PATCH/PUT/DELETE Traslado

**URL:** `PATCH /api/inventory/traslados/{id}/`
**Autenticacion:** Requerida (JWT)

#### Headers requeridos

| Header          | Valor              |
|-----------------|--------------------|
| `Authorization` | `Bearer <token>`   |
| `Content-Type`  | `application/json` |

#### Body (Request)

Campos del serializer `TrasladoInventarioSerializer`.

#### Parametros de URL / Query params

| Parametro | Tipo      | Descripcion |
|----------|-----------|-------------|
| `id`     | `integer` | ID traslado |

#### Respuestas

**`200 OK`** (para PATCH/PUT)

**`204 No Content`** (para DELETE)

#### Ejemplo completo

```javascript
const res = await fetch('/api/inventory/traslados/3/', {
  method: 'PATCH',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({ estado: 'EN_TRANSITO' })
});
const data = await res.json();
```

---

### GET Catalogo de productos

Catalogo publico con stock por sucursal.

**URL:** `GET /api/inventory/catalogo/?marca_id=&categoria_id=&sucursal_id=`
**Autenticacion:** No requerida
**Permisos:** Publico

#### Headers requeridos

No aplica.

#### Body (Request)

No aplica.

#### Parametros de URL / Query params

| Parametro      | Tipo      | Descripcion |
|----------------|-----------|-------------|
| `marca_id`     | `integer` | Filtra por marca |
| `categoria_id` | `integer` | Filtra por categoria |
| `sucursal_id`  | `integer` | Filtra por sucursal (stock) |

#### Respuestas

**`200 OK`**

```json
[
  {
    "id": 5,
    "sku": "JER-5ML-001",
    "nombre": "Jeringa 5ml",
    "descripcion": "",
    "valor_unitario": 350,
    "precio_con_iva": 417,
    "marca": {"id": 1, "nombre": "ACME", "activo": true},
    "unidad_medida": "unidad",
    "largo_mm": 50,
    "ancho_mm": 20,
    "alto_mm": 20,
    "peso_mg": 30,
    "volumen_ml": 5,
    "requiere_control_vencimiento": true,
    "registro_sanitario": "REG-123",
    "activo": true,
    "es_caja": false,
    "categorias": ["Insumos"],
    "stock_por_sucursal": [
      {"sucursal_id": 1, "sucursal_nombre": "Sucursal A", "stock_neto": 100}
    ]
  }
]
```

#### Ejemplo completo

```javascript
const res = await fetch('/api/inventory/catalogo/?categoria_id=1');
const data = await res.json();
```

---

### GET Catalogo de cajas

Catalogo publico solo productos `es_caja=true`.

**URL:** `GET /api/inventory/catalogo-cajas/?marca_id=&categoria_id=&sucursal_id=`
**Autenticacion:** No requerida
**Permisos:** Publico

#### Headers requeridos

No aplica.

#### Body (Request)

No aplica.

#### Parametros de URL / Query params

Mismos que `catalogo`.

#### Respuestas

**`200 OK`**

```json
[
  {
    "id": 5,
    "sku": "JER-5ML-001",
    "nombre": "Jeringa 5ml",
    "descripcion": "",
    "valor_unitario": 350,
    "precio_con_iva": 417,
    "marca": {"id": 1, "nombre": "ACME", "activo": true},
    "unidad_medida": "unidad",
    "largo_mm": 50,
    "ancho_mm": 20,
    "alto_mm": 20,
    "peso_mg": 30,
    "volumen_ml": 5,
    "requiere_control_vencimiento": true,
    "registro_sanitario": "REG-123",
    "activo": true,
    "es_caja": true,
    "categorias": ["Embalaje"],
    "stock_por_sucursal": [
      {"sucursal_id": 1, "sucursal_nombre": "Sucursal A", "stock_neto": 20}
    ]
  }
]
```

#### Ejemplo completo

```javascript
const res = await fetch('/api/inventory/catalogo-cajas/');
const data = await res.json();
```

---

### POST Ingresar producto a inventario

Crea producto/lote e ingresa stock en una sucursal.

**URL:** `POST /api/inventory/ingresar-producto/`
**Autenticacion:** Requerida (JWT)
**Permisos:** Solo trabajadores activos

#### Headers requeridos

| Header          | Valor              |
|-----------------|--------------------|
| `Authorization` | `Bearer <token>`   |
| `Content-Type`  | `application/json` |

#### Body (Request)

```json
{
  "sku": "JER-5ML-001",
  "nombre": "Jeringa 5ml",
  "descripcion": "",
  "valor_unitario": 350,
  "marca_id": 1,
  "unidad_medida": "unidad",
  "requiere_control_vencimiento": true,
  "registro_sanitario": "REG-123",
  "es_caja": false,
  "largo_mm": 50,
  "ancho_mm": 20,
  "alto_mm": 20,
  "peso_mg": 30,
  "volumen_ml": 5,
  "categoria_ids": [1, 2],
  "codigo_lote": "LOT-2025-A",
  "fecha_elaboracion": "2025-01-01",
  "fecha_vencimiento": "2026-01-01",
  "sucursal_id": 1,
  "cantidad": 100,
  "stock_critico": 10,
  "motivo": "Ingreso inicial",
  "observacion": ""
}
```

#### Parametros de URL / Query params

No aplica.

#### Respuestas

**`201 Created`**

```json
{
  "mensaje": "Producto creado e ingresado al inventario.",
  "producto_id": 5,
  "sku": "JER-5ML-001",
  "lote_id": 9,
  "codigo_lote": "LOT-2025-A",
  "inventario_id": 10,
  "sucursal_id": 1,
  "stock_actual": 100,
  "movimiento_id": 50
}
```

#### Ejemplo completo

```javascript
const res = await fetch('/api/inventory/ingresar-producto/', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify(payload)
});
const data = await res.json();
```

---

# Pedidos

---

### POST Crear pedido

Crea un pedido para el cliente autenticado.

**URL:** `POST /api/orders/pedidos/`
**Autenticacion:** Requerida (JWT)
**Permisos:** Solo clientes

#### Headers requeridos

| Header          | Valor              |
|-----------------|--------------------|
| `Authorization` | `Bearer <token>`   |
| `Content-Type`  | `application/json` |

#### Body (Request)

```json
{
  "sucursal_origen_id": 1,
  "direccion_entrega_id": 3,
  "tipo_venta": "WEBPAY",
  "tipo_despacho": "NORMAL",
  "prioridad_medica": "NORMAL",
  "fecha_requerida_entrega": "2025-08-15T10:00:00Z",
  "observacion": "Entregar en porteria",
  "detalles": [
    {"producto_id": 5, "cantidad": 2},
    {"producto_id": 8, "cantidad": 1, "lote_id": 12}
  ]
}
```

**Descripcion de campos:**

| Campo                     | Tipo       | Requerido | Default   | Descripcion |
|---------------------------|------------|-----------|-----------|-------------|
| `sucursal_origen_id`      | `integer`  | Si        | -         | ID sucursal origen |
| `direccion_entrega_id`    | `integer`  | Si        | -         | ID direccion del cliente |
| `tipo_venta`              | `string`   | Si        | -         | Ver valores permitidos |
| `tipo_despacho`           | `string`   | No        | `NORMAL`  | `NORMAL` o `EXPRESS` |
| `prioridad_medica`        | `string`   | No        | `NORMAL`  | `NORMAL`, `ALTA`, `CRITICA` |
| `fecha_requerida_entrega` | `datetime` | No        | -         | ISO 8601 |
| `observacion`             | `string`   | No        | -         | Max 255 |
| `detalles`                | `array`    | Si        | -         | Lineas de pedido |

**Estructura de `detalles`:**

| Campo        | Tipo      | Requerido | Default | Descripcion |
|--------------|-----------|-----------|---------|-------------|
| `producto_id`| `integer` | Si        | -       | ID producto |
| `cantidad`   | `integer` | Si        | -       | Minimo 1 |
| `lote_id`    | `integer` | No        | -       | Si no viene, FEFO |
| `observacion`| `string`  | No        | -       | Observacion linea |

**Valores permitidos `tipo_venta`:**

| Valor | Descripcion |
|-------|-------------|
| `WEBPAY` | WebPay |
| `TRANSFERENCIA` | Transferencia |
| `MAYORISTA` | Mayorista |
| `CREDITO_INSTITUCIONAL` | Credito institucional |

#### Parametros de URL / Query params

No aplica.

#### Respuestas

**`201 Created`**

```json
{
  "id": 42,
  "cliente_id": 7,
  "cliente_nombre": "Juan Perez",
  "sucursal_origen_id": 1,
  "sucursal_nombre": "Sucursal Providencia",
  "direccion_entrega_id": 3,
  "estado_pedido": "PENDIENTE",
  "tipo_venta": "WEBPAY",
  "tipo_despacho": "NORMAL",
  "prioridad_medica": "NORMAL",
  "fecha_creacion": "2025-07-10T14:32:00Z",
  "fecha_actualizacion": "2025-07-10T14:32:00Z",
  "fecha_requerida_entrega": "2025-08-15T10:00:00Z",
  "subtotal": 50000,
  "descuento_total": 0,
  "monto_neto": 50000,
  "monto_iva": 9500,
  "total": 59500,
  "observacion": "Entregar en porteria",
  "detalles": [
    {
      "id": 101,
      "producto_id": 5,
      "producto_sku": "JER-5ML-001",
      "producto_nombre": "Jeringa 5ml",
      "lote_id": 9,
      "lote_codigo": "LOT-2025-A",
      "cantidad": 2,
      "cantidad_preparada": 0,
      "precio_unitario_historico": 350,
      "descuento": 0,
      "subtotal": 700,
      "observacion": ""
    }
  ]
}
```

**`400 Bad Request`**

```json
{
  "detalles": [
    "Producto id=5: stock insuficiente en la sucursal. Disponible neto: 1, solicitado: 2."
  ]
}
```

**`403 Forbidden`**

```json
{
  "detail": "El usuario autenticado no tiene un perfil de cliente asociado."
}
```

**`409 Conflict`**

```json
{
  "error": "Sin stock disponible para producto id=5 en la sucursal indicada."
}
```

#### Ejemplo completo

```javascript
const res = await fetch('/api/orders/pedidos/', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify(payload)
});
const data = await res.json();
```

---

### GET Mis pedidos

**URL:** `GET /api/orders/pedidos/mis-pedidos/`
**Autenticacion:** Requerida (JWT)
**Permisos:** Solo clientes

#### Headers requeridos

| Header          | Valor            |
|-----------------|------------------|
| `Authorization` | `Bearer <token>` |

#### Body (Request)

No aplica.

#### Parametros de URL / Query params

No aplica.

#### Respuestas

**`200 OK`**

```json
[
  {
    "id": 42,
    "cliente_id": 7,
    "cliente_nombre": "Juan Perez",
    "sucursal_origen_id": 1,
    "sucursal_nombre": "Sucursal Providencia",
    "direccion_entrega_id": 3,
    "estado_pedido": "PENDIENTE",
    "tipo_venta": "WEBPAY",
    "tipo_despacho": "NORMAL",
    "prioridad_medica": "NORMAL",
    "fecha_creacion": "2025-07-10T14:32:00Z",
    "fecha_actualizacion": "2025-07-10T14:32:00Z",
    "fecha_requerida_entrega": "2025-08-15T10:00:00Z",
    "subtotal": 50000,
    "descuento_total": 0,
    "monto_neto": 50000,
    "monto_iva": 9500,
    "total": 59500,
    "observacion": "Entregar en porteria",
    "detalles": [
      {
        "id": 101,
        "producto_id": 5,
        "producto_sku": "JER-5ML-001",
        "producto_nombre": "Jeringa 5ml",
        "lote_id": 9,
        "lote_codigo": "LOT-2025-A",
        "cantidad": 2,
        "cantidad_preparada": 0,
        "precio_unitario_historico": 350,
        "descuento": 0,
        "subtotal": 700,
        "observacion": ""
      }
    ]
  }
]
```

#### Ejemplo completo

```javascript
const res = await fetch('/api/orders/pedidos/mis-pedidos/', {
  headers: { 'Authorization': `Bearer ${token}` }
});
const data = await res.json();
```

---

### GET Todos los pedidos

**URL:** `GET /api/orders/pedidos/todos/`
**Autenticacion:** Requerida (JWT)
**Permisos:** Ejecutivos/Administrador

#### Headers requeridos

| Header          | Valor            |
|-----------------|------------------|
| `Authorization` | `Bearer <token>` |

#### Body (Request)

No aplica.

#### Parametros de URL / Query params

No aplica.

#### Respuestas

**`200 OK`**

```json
[
  {
    "id": 42,
    "cliente_id": 7,
    "cliente_nombre": "Juan Perez",
    "sucursal_origen_id": 1,
    "sucursal_nombre": "Sucursal Providencia",
    "direccion_entrega_id": 3,
    "estado_pedido": "PENDIENTE",
    "tipo_venta": "WEBPAY",
    "tipo_despacho": "NORMAL",
    "prioridad_medica": "NORMAL",
    "fecha_creacion": "2025-07-10T14:32:00Z",
    "fecha_actualizacion": "2025-07-10T14:32:00Z",
    "fecha_requerida_entrega": "2025-08-15T10:00:00Z",
    "subtotal": 50000,
    "descuento_total": 0,
    "monto_neto": 50000,
    "monto_iva": 9500,
    "total": 59500,
    "observacion": "Entregar en porteria",
    "detalles": [
      {
        "id": 101,
        "producto_id": 5,
        "producto_sku": "JER-5ML-001",
        "producto_nombre": "Jeringa 5ml",
        "lote_id": 9,
        "lote_codigo": "LOT-2025-A",
        "cantidad": 2,
        "cantidad_preparada": 0,
        "precio_unitario_historico": 350,
        "descuento": 0,
        "subtotal": 700,
        "observacion": ""
      }
    ]
  }
]
```

**`403 Forbidden`**

```json
{
  "error": "No tienes permiso para ver todos los pedidos."
}
```

#### Ejemplo completo

```javascript
const res = await fetch('/api/orders/pedidos/todos/', {
  headers: { 'Authorization': `Bearer ${token}` }
});
const data = await res.json();
```

---

### GET Detalle de pedido

**URL:** `GET /api/orders/pedidos/{pedido_id}/`
**Autenticacion:** Requerida (JWT)
**Permisos:** Cliente duenno o trabajador

#### Headers requeridos

| Header          | Valor            |
|-----------------|------------------|
| `Authorization` | `Bearer <token>` |

#### Body (Request)

No aplica.

#### Parametros de URL / Query params

| Parametro   | Tipo      | Descripcion |
|------------|-----------|-------------|
| `pedido_id`| `integer` | ID pedido |

#### Respuestas

**`200 OK`** (formato `PedidoOutputSerializer`)

**`404 Not Found`**

```json
{
  "error": "No existe un pedido con id=42."
}
```

#### Ejemplo completo

```javascript
const res = await fetch('/api/orders/pedidos/42/', {
  headers: { 'Authorization': `Bearer ${token}` }
});
const data = await res.json();
```

---

### PATCH Editar pedido (cliente)

**URL:** `PATCH /api/orders/pedidos/{pedido_id}/`
**Autenticacion:** Requerida (JWT)
**Permisos:** Cliente duenno (estado PENDIENTE/APROBADO)

#### Headers requeridos

| Header          | Valor              |
|-----------------|--------------------|
| `Authorization` | `Bearer <token>`   |
| `Content-Type`  | `application/json` |

#### Body (Request)

```json
{
  "direccion_entrega": 3,
  "tipo_despacho": "NORMAL",
  "prioridad_medica": "NORMAL",
  "fecha_requerida_entrega": "2025-08-15T10:00:00Z",
  "observacion": ""
}
```

#### Parametros de URL / Query params

| Parametro   | Tipo      | Descripcion |
|------------|-----------|-------------|
| `pedido_id`| `integer` | ID pedido |

#### Respuestas

**`200 OK`** (formato `PedidoOutputSerializer`)

**`403 Forbidden`**

```json
{
  "error": "Este endpoint de edicion esta pensado para clientes."
}
```

#### Ejemplo completo

```javascript
const res = await fetch('/api/orders/pedidos/42/', {
  method: 'PATCH',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({ observacion: 'Entregar en porteria' })
});
const data = await res.json();
```

---

### POST Aprobar/Rechazar pedido

**URL:** `POST /api/orders/pedidos/{pedido_id}/aprobar/`
**Autenticacion:** Requerida (JWT)
**Permisos:** Ejecutivos/Administrador

#### Headers requeridos

| Header          | Valor              |
|-----------------|--------------------|
| `Authorization` | `Bearer <token>`   |
| `Content-Type`  | `application/json` |

#### Body (Request)

```json
{
  "accion": "APROBADO",
  "comentario": "ok"
}
```

**Valores permitidos `accion`:** `APROBADO`, `RECHAZADO`

#### Parametros de URL / Query params

| Parametro   | Tipo      | Descripcion |
|------------|-----------|-------------|
| `pedido_id`| `integer` | ID pedido |

#### Respuestas

**`200 OK`**

```json
{
  "pedido_id": 42,
  "estado_pedido": "APROBADO",
  "comentario": "ok"
}
```

**`400 Bad Request`**

```json
{
  "error": "El campo 'accion' debe ser 'APROBADO' o 'RECHAZADO'."
}
```

**`403 Forbidden`**

```json
{
  "error": "Solo los ejecutivos pueden aprobar pedidos."
}
```

**`404 Not Found`**

```json
{
  "error": "No existe un pedido con id=42."
}
```

**`409 Conflict`**

```json
{
  "error": "Sin stock disponible para producto id=5 en la sucursal indicada."
}
```

#### Ejemplo completo

```javascript
const res = await fetch('/api/orders/pedidos/42/aprobar/', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({ accion: 'APROBADO', comentario: 'ok' })
});
const data = await res.json();
```

---

# Logistica

---

### POST Cotizar envio

Cotiza con Chilexpress, con o sin pedido.

**URL:** `POST /api/logistics/cotizar/`
**Autenticacion:** Requerida (JWT)

#### Headers requeridos

| Header          | Valor              |
|-----------------|--------------------|
| `Authorization` | `Bearer <token>`   |
| `Content-Type`  | `application/json` |

#### Body (Request)

Con pedido:

```json
{
  "pedido_id": 42,
  "county_code_destino": "PROV"
}
```

Sin pedido:

```json
{
  "sucursal_id": 1,
  "county_code_destino": "CONC",
  "productos": [
    {"peso_mg": 500000, "largo_mm": 200, "ancho_mm": 150, "alto_mm": 100, "cantidad": 3, "valor_unitario": 1000}
  ]
}
```

**Descripcion de campos:**

| Campo                | Tipo      | Requerido | Default | Descripcion |
|----------------------|-----------|-----------|---------|-------------|
| `pedido_id`          | `integer` | Cond.     | -       | Pedido existente |
| `sucursal_id`        | `integer` | Cond.     | -       | Sucursal si no hay pedido |
| `county_code_destino`| `string`  | Si        | -       | Codigo Chilexpress destino |
| `productos`          | `array`   | Cond.     | -       | Productos manuales |

**Estructura `productos`:**

| Campo         | Tipo      | Requerido | Default | Descripcion |
|---------------|-----------|-----------|---------|-------------|
| `peso_mg`     | `integer` | Si        | -       | Peso en mg |
| `largo_mm`    | `integer` | Si        | -       | Largo en mm |
| `ancho_mm`    | `integer` | Si        | -       | Ancho en mm |
| `alto_mm`     | `integer` | Si        | -       | Alto en mm |
| `cantidad`    | `integer` | Si        | `1`     | Cantidad |
| `valor_unitario` | `integer` | No     | `0`     | Valor para declarado |

#### Parametros de URL / Query params

No aplica.

#### Respuestas

**`200 OK`**

```json
{
  "origin_county_code": "STGO",
  "destination_county_code": "PROV",
  "servicios_disponibles": [
    {
      "serviceTypeCode": 3,
      "serviceDescription": "Express",
      "finalWeight": "1",
      "serviceValue": "2500",
      "deliveryType": 1
    }
  ],
  "pedido_id": 42,
  "num_cajas": 1
}
```

**`400 Bad Request`**

```json
{
  "error": "Error al construir los parametros de cotizacion: ..."
}
```

**`502 Bad Gateway`**

```json
{
  "error": "Error al consultar Chilexpress: ..."
}
```

#### Ejemplo completo

```javascript
const res = await fetch('/api/logistics/cotizar/', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({ pedido_id: 42, county_code_destino: 'PROV' })
});
const data = await res.json();
```

---

### POST Crear envio

Crea OT en Chilexpress para pedido aprobado.

**URL:** `POST /api/logistics/envios/`
**Autenticacion:** Requerida (JWT)

#### Headers requeridos

| Header          | Valor              |
|-----------------|--------------------|
| `Authorization` | `Bearer <token>`   |
| `Content-Type`  | `application/json` |

#### Body (Request)

```json
{
  "pedido_id": 42,
  "service_type_code": 3,
  "label_type": 2,
  "contacto_nombre": "Clinica Bio-Bio",
  "contacto_telefono": "412223344",
  "contacto_email": "bodega@clinica.cl"
}
```

**Descripcion de campos:**

| Campo             | Tipo      | Requerido | Default | Descripcion |
|-------------------|-----------|-----------|---------|-------------|
| `pedido_id`       | `integer` | Si        | -       | Pedido aprobado |
| `service_type_code` | `integer` | Si      | -       | ServiceTypeCode de cotizacion |
| `label_type`      | `integer` | No        | `2`     | 0=datos,1=EPL,2=binaria |
| `contacto_nombre` | `string`  | No        | -       | Nombre contacto |
| `contacto_telefono` | `string` | No       | -       | Telefono contacto |
| `contacto_email`  | `string`  | No        | -       | Email contacto |

#### Parametros de URL / Query params

No aplica.

#### Respuestas

**`201 Created`**

```json
{
  "despacho": {
    "id": 7,
    "pedido_id": 42,
    "courier_nombre": "Chilexpress",
    "numero_seguimiento": "123456789",
    "estado_envio": "PENDIENTE",
    "tipo_despacho": "NORMAL",
    "fecha_despacho": null,
    "fecha_entrega_estimada": null,
    "costo_despacho": 0,
    "url_etiqueta": ""
  },
  "numero_ot": "123456789",
  "num_cajas": 1,
  "etiqueta_disponible": true,
  "service_description": "Express"
}
```

**`400 Bad Request`**

```json
{
  "error": "El pedido debe estar APROBADO o EN_PICKING. Estado actual: ..."
}
```

**`502 Bad Gateway`**

```json
{
  "error": "Error al crear la OT en Chilexpress: ..."
}
```

#### Ejemplo completo

```javascript
const res = await fetch('/api/logistics/envios/', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify(payload)
});
const data = await res.json();
```

---

### GET Tracking envio

**URL:** `GET /api/logistics/envios/{pedido_id}/tracking/?historial=true`
**Autenticacion:** Requerida (JWT)

#### Headers requeridos

| Header          | Valor            |
|-----------------|------------------|
| `Authorization` | `Bearer <token>` |

#### Body (Request)

No aplica.

#### Parametros de URL / Query params

| Parametro   | Tipo      | Descripcion |
|------------|-----------|-------------|
| `pedido_id`| `integer` | ID pedido |
| `historial`| `boolean` | Si `true`, devuelve eventos completos |

#### Respuestas

**`200 OK`**

```json
{
  "data": {
    "tracking": []
  }
}
```

**`404 Not Found`**

```json
{
  "error": "No existe despacho para el pedido 42."
}
```

**`502 Bad Gateway`**

```json
{
  "error": "Error al consultar tracking: ..."
}
```

#### Ejemplo completo

```javascript
const res = await fetch('/api/logistics/envios/42/tracking/?historial=true', {
  headers: { 'Authorization': `Bearer ${token}` }
});
const data = await res.json();
```

---

# Ubicaciones

---

### GET Regiones

**URL:** `GET /api/locations/regions/`
**Autenticacion:** No requerida

#### Headers requeridos

No aplica.

#### Body (Request)

No aplica.

#### Parametros de URL / Query params

No aplica.

#### Respuestas

**`200 OK`**

```json
[
  {"id": 1, "nombre": "Metropolitana", "chilexpress_region_id": 13}
]
```

#### Ejemplo completo

```javascript
const res = await fetch('/api/locations/regions/');
const data = await res.json();
```

---

### GET Regiones con comunas

**URL:** `GET /api/locations/regions-with-comunas/`
**Autenticacion:** No requerida

#### Headers requeridos

No aplica.

#### Body (Request)

No aplica.

#### Parametros de URL / Query params

No aplica.

#### Respuestas

**`200 OK`**

```json
[
  {
    "id": 1,
    "nombre": "Metropolitana",
    "chilexpress_region_id": 13,
    "comunas": [
      {
        "id": 10,
        "nombre": "Providencia",
        "region": {"id": 1, "nombre": "Metropolitana", "chilexpress_region_id": 13},
        "chilexpress": {"county_code": "PROV", "county_name": "Providencia", "coverage_name": "Urbano", "retorna_respuesta": true}
      }
    ]
  }
]
```

#### Ejemplo completo

```javascript
const res = await fetch('/api/locations/regions-with-comunas/');
const data = await res.json();
```

---

### GET Comunas con cobertura

**URL:** `GET /api/locations/comunas/?region_id=1`
**Autenticacion:** No requerida

#### Headers requeridos

No aplica.

#### Body (Request)

No aplica.

#### Parametros de URL / Query params

| Parametro  | Tipo      | Descripcion |
|-----------|-----------|-------------|
| `region_id` | `integer` | Filtra comunas por region |

#### Respuestas

**`200 OK`**

```json
[
  {
    "id": 10,
    "nombre": "Providencia",
    "region": {"id": 1, "nombre": "Metropolitana", "chilexpress_region_id": 13},
    "chilexpress": {"county_code": "PROV", "county_name": "Providencia", "coverage_name": "Urbano", "retorna_respuesta": true}
  }
]
```

**`400 Bad Request`**

```json
{
  "region_id": "El parametro region_id debe ser un numero valido."
}
```

#### Ejemplo completo

```javascript
const res = await fetch('/api/locations/comunas/?region_id=1');
const data = await res.json();
```

---

### GET Comunas Chilexpress

**URL:** `GET /api/locations/comunas-chilexpress/?retorna_respuesta=true&comuna_id=10`
**Autenticacion:** No requerida

#### Headers requeridos

No aplica.

#### Body (Request)

No aplica.

#### Parametros de URL / Query params

| Parametro            | Tipo     | Descripcion |
|----------------------|----------|-------------|
| `retorna_respuesta`  | `string` | `true` o `false` |
| `comuna_id`          | `integer`| Filtra por comuna |

#### Respuestas

**`200 OK`**

```json
[
  {"county_code": "PROV", "county_name": "Providencia", "coverage_name": "Urbano", "retorna_respuesta": true}
]
```

#### Ejemplo completo

```javascript
const res = await fetch('/api/locations/comunas-chilexpress/?retorna_respuesta=true');
const data = await res.json();
```

---

### GET Sucursal (publico)

**URL:** `GET /api/locations/sucursales/{id}/`
**Autenticacion:** No requerida

#### Headers requeridos

No aplica.

#### Body (Request)

No aplica.

#### Parametros de URL / Query params

| Parametro | Tipo      | Descripcion |
|----------|-----------|-------------|
| `id`     | `integer` | ID sucursal |

#### Respuestas

**`200 OK`**

```json
{
  "id": 1,
  "nombre": "Sucursal A",
  "direccion": "Av. Siempre Viva",
  "num_direccion": "742",
  "telefono": "225551234",
  "comuna": {"id": 10, "nombre": "Providencia"},
  "region": {"id": 1, "nombre": "Metropolitana"},
  "county_code": "PROV",
  "activo": true
}
```

**`404 Not Found`**

```json
{"detail": "Not found."}
```

#### Ejemplo completo

```javascript
const res = await fetch('/api/locations/sucursales/1/');
const data = await res.json();
```

---

# Integraciones

---

### POST Crear pedido B2B (ERP clinicas)

Crea un pedido directamente desde un ERP institucional usando API Key.

**URL:** `POST /api/integrations/pedidos/`
**Autenticacion:** Requerida (API Key en `X-Api-Key`)
**Permisos:** Solo clientes API activos (instituciones con ApiClient activo)

#### Headers requeridos

| Header         | Valor                     |
|----------------|---------------------------|
| `X-Api-Key`    | `<tu_api_key>`            |
| `Content-Type` | `application/json`        |

#### Body (Request)

```json
{
  "sucursal_id": 1,
  "tipo_venta": "CREDITO_INSTITUCIONAL",
  "tipo_despacho": "NORMAL",
  "prioridad_medica": "ALTA",
  "fecha_requerida_entrega": "2025-08-15T10:00:00Z",
  "referencia_erp": "OC-2025-00847",
  "observacion": "Entregar en bodega",
  "lineas": [
    { "producto_sku": "JER-5ML-001", "cantidad": 200 },
    { "producto_sku": "GUA-LAT-M", "cantidad": 500, "lote_id": 3 }
  ]
}
```

**Descripcion de campos:**

| Campo                    | Tipo      | Requerido | Default | Descripcion |
|--------------------------|-----------|-----------|---------|-------------|
| `sucursal_id`            | `integer` | Si        | -       | Sucursal desde donde se despacha |
| `direccion_entrega_id`   | `integer` | No        | -       | Direccion de entrega de la institucion; si se omite se usa la principal |
| `tipo_venta`             | `string`  | No        | `CREDITO_INSTITUCIONAL` | Solo `TRANSFERENCIA` o `CREDITO_INSTITUCIONAL` |
| `tipo_despacho`          | `string`  | No        | `NORMAL` | `NORMAL` o `EXPRESS` |
| `prioridad_medica`       | `string`  | No        | `NORMAL` | `NORMAL`, `ALTA` o `CRITICA` |
| `fecha_requerida_entrega`| `datetime`| No        | -       | ISO 8601. Fecha estimada requerida |
| `referencia_erp`         | `string`  | No        | -       | Orden interna del ERP para trazabilidad |
| `observacion`            | `string`  | No        | `""`    | Observacion del pedido |
| `lineas`                 | `array`   | Si        | -       | Lista de lineas del pedido |

**Estructura de cada objeto en `lineas`:**

| Campo           | Tipo      | Requerido | Default | Descripcion |
|-----------------|-----------|-----------|---------|-------------|
| `producto_sku`  | `string`  | Si        | -       | SKU del producto (catalogo) |
| `cantidad`      | `integer` | Si        | -       | Cantidad solicitada (min 1) |
| `lote_id`       | `integer` | No        | -       | Lote especifico; si no se envia se aplica FEFO |
| `observacion`   | `string`  | No        | `""`    | Observacion por linea |

**Valores permitidos para `tipo_venta`:**

| Valor                   | Descripcion |
|-------------------------|-------------|
| `TRANSFERENCIA`         | Transferencia bancaria |
| `CREDITO_INSTITUCIONAL` | Credito de convenio |

#### Parametros de URL / Query params

No aplica.

#### Respuestas

**`201 Created` — Pedido creado**

```json
{
  "pedido_id": 87,
  "referencia_erp": "OC-2025-00847",
  "estado": "PENDIENTE",
  "institucion": "Clinica Bio-Bio SpA",
  "total": 95200,
  "monto_neto": 80000,
  "monto_iva": 15200,
  "lineas": [
    {
      "producto_sku": "JER-5ML-001",
      "producto_nombre": "Jeringa 5ml c/aguja",
      "lote_id": 9,
      "cantidad": 200,
      "precio_unitario": 350,
      "subtotal": 70000
    }
  ],
  "fecha_creacion": "2025-07-10T14:32:00Z",
  "mensaje": "Pedido creado correctamente. Quedara en estado PENDIENTE hasta aprobacion."
}
```

**`400 Bad Request` — Error de validacion**

```json
{
  "stock": [
    "SKU 'JER-5ML-001': stock insuficiente en la sucursal. Disponible: 10, solicitado: 200."
  ]
}
```

**`401 Unauthorized` — API Key ausente o invalida**

```json
{
  "detail": "Authentication credentials were not provided."
}
```

**`403 Forbidden` — ApiClient inactivo**

```json
{
  "detail": "No tiene permiso para realizar esta accion."
}
```

**`409 Conflict` — Conflicto de stock (race condition)**

```json
{
  "error": "Sin stock para SKU 'JER-5ML-001'. Intenta de nuevo."
}
```

#### Ejemplo completo

```javascript
const res = await fetch('/api/integrations/pedidos/', {
  method: 'POST',
  headers: {
    'X-Api-Key': apiKey,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    sucursal_id: 1,
    tipo_venta: 'CREDITO_INSTITUCIONAL',
    prioridad_medica: 'ALTA',
    referencia_erp: 'OC-2025-00847',
    lineas: [
      { producto_sku: 'JER-5ML-001', cantidad: 200 },
      { producto_sku: 'GUA-LAT-M', cantidad: 500, lote_id: 3 }
    ]
  })
});

const data = await res.json();
```

---

### POST Crear API Key para institucion

Genera una API Key para una institución cliente. La key se muestra **una sola vez** en la respuesta — si se pierde, debe generarse una nueva. Solo trabajadores activos de MEDISTOCK pueden usar este endpoint.

**URL:** `POST /api/integrations/api-clients/crear/`
**Autenticacion:** Requerida (JWT)
**Permisos:** Solo trabajadores activos (`EsTrabajador`)

#### Headers requeridos

| Header          | Valor              |
|-----------------|--------------------|
| `Authorization` | `Bearer <token>`   |
| `Content-Type`  | `application/json` |

#### Body (Request)

```json
{
  "institucion_id": 5,
  "nombre_cliente_api": "ERP Clinica Bio-Bio",
  "limite_requests_diario": 500,
  "fecha_expiracion": "2026-12-31T23:59:59Z"
}
```

**Descripcion de campos:**

| Campo                    | Tipo       | Requerido | Default | Descripcion |
|--------------------------|------------|-----------|---------|-------------|
| `institucion_id`         | `integer`  | Si        | -       | ID de la institucion a la que pertenece la key |
| `nombre_cliente_api`     | `string`   | Si        | -       | Nombre descriptivo. Ej: `"ERP Clinica Bio-Bio"` |
| `limite_requests_diario` | `integer`  | No        | `1000`  | Limite de requests diarios para este cliente |
| `fecha_expiracion`       | `datetime` | No        | `null`  | ISO 8601. Si se omite, la key no expira |

#### Parametros de URL / Query params

No aplica.

#### Respuestas

**`201 Created` — API Key creada**

```json
{
  "id": 3,
  "institucion": "Clinica Bio-Bio SpA",
  "nombre_cliente_api": "ERP Clinica Bio-Bio",
  "api_key": "a3f8c2d1e9b047a56f1230cde4891bfa2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f",
  "activo": true,
  "limite_requests_diario": 500,
  "fecha_expiracion": "2026-12-31T23:59:59Z",
  "fecha_creacion": "2025-07-10T14:32:00Z",
  "advertencia": "Guarda esta API Key ahora. No se puede recuperar despues — si se pierde, deberas generar una nueva."
}
```

> **Importante:** El campo `api_key` solo aparece en esta respuesta. Despues de este momento, no existe forma de recuperarla — ni desde la BD ni desde otro endpoint.

**`400 Bad Request` — Campos faltantes**

```json
{
  "error": "El campo institucion_id es requerido."
}
```

**`401 Unauthorized`**

```json
{
  "detail": "Authentication credentials were not provided."
}
```

**`403 Forbidden` — No es trabajador**

```json
{
  "detail": "Solo los trabajadores de MEDISTOCK pueden realizar esta accion."
}
```

**`404 Not Found` — Institucion no existe**

```json
{
  "error": "No existe una institucion activa con id=5."
}
```

#### Ejemplo completo

```javascript
const res = await fetch('/api/integrations/api-clients/crear/', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    institucion_id: 5,
    nombre_cliente_api: 'ERP Clinica Bio-Bio',
    limite_requests_diario: 500
  })
});

const data = await res.json();
// Guardar data.api_key en un lugar seguro — no se puede recuperar despues
console.log(data.api_key);
```

---

### GET Listar API Clients

Lista todos los clientes API registrados. No expone las keys — solo metadata.

**URL:** `GET /api/integrations/api-clients/`
**Autenticacion:** Requerida (JWT)
**Permisos:** Solo trabajadores activos (`EsTrabajador`)

#### Headers requeridos

| Header          | Valor            |
|-----------------|------------------|
| `Authorization` | `Bearer <token>` |

#### Body (Request)

No aplica.

#### Parametros de URL / Query params

No aplica.

#### Respuestas

**`200 OK`**

```json
[
  {
    "id": 3,
    "institucion": "Clinica Bio-Bio SpA",
    "institucion_id": 5,
    "nombre_cliente_api": "ERP Clinica Bio-Bio",
    "activo": true,
    "limite_requests_diario": 500,
    "fecha_creacion": "2025-07-10T14:32:00Z",
    "fecha_expiracion": "2026-12-31T23:59:59Z",
    "vencida": false
  }
]
```

**Descripcion de campos de respuesta:**

| Campo                    | Tipo       | Descripcion |
|--------------------------|------------|-------------|
| `id`                     | `integer`  | ID del ApiClient |
| `institucion`            | `string`   | Nombre de la institucion |
| `institucion_id`         | `integer`  | ID de la institucion |
| `nombre_cliente_api`     | `string`   | Nombre descriptivo |
| `activo`                 | `boolean`  | Si puede autenticarse actualmente |
| `limite_requests_diario` | `integer`  | Limite de requests por dia |
| `fecha_creacion`         | `datetime` | Cuando se creo la key |
| `fecha_expiracion`       | `datetime` | Cuando expira (`null` si no expira) |
| `vencida`                | `boolean`  | `true` si `fecha_expiracion` ya paso |

**`403 Forbidden`**

```json
{
  "detail": "Solo los trabajadores de MEDISTOCK pueden realizar esta accion."
}
```

#### Ejemplo completo

```javascript
const res = await fetch('/api/integrations/api-clients/', {
  headers: { 'Authorization': `Bearer ${token}` }
});
const data = await res.json();
```

---

### GET Detalle de API Client

Retorna la metadata de un ApiClient especifico. No expone la key.

**URL:** `GET /api/integrations/api-clients/{id}/`
**Autenticacion:** Requerida (JWT)
**Permisos:** Solo trabajadores activos (`EsTrabajador`)

#### Headers requeridos

| Header          | Valor            |
|-----------------|------------------|
| `Authorization` | `Bearer <token>` |

#### Body (Request)

No aplica.

#### Parametros de URL / Query params

| Parametro | Tipo      | Descripcion |
|-----------|-----------|-------------|
| `id`      | `integer` | ID del ApiClient |

#### Respuestas

**`200 OK`**

```json
{
  "id": 3,
  "institucion": "Clinica Bio-Bio SpA",
  "nombre_cliente_api": "ERP Clinica Bio-Bio",
  "activo": true,
  "limite_requests_diario": 500,
  "fecha_creacion": "2025-07-10T14:32:00Z",
  "fecha_expiracion": "2026-12-31T23:59:59Z"
}
```

**`404 Not Found`**

```json
{
  "error": "ApiClient no encontrado."
}
```

#### Ejemplo completo

```javascript
const res = await fetch('/api/integrations/api-clients/3/', {
  headers: { 'Authorization': `Bearer ${token}` }
});
const data = await res.json();
```

---

### PATCH Actualizar API Client / Rotar Key

Permite activar, desactivar, cambiar el limite de requests, actualizar la fecha de expiracion o rotar la API Key de un cliente. Si se rota la key, la anterior queda invalida de inmediato.

**URL:** `PATCH /api/integrations/api-clients/{id}/`
**Autenticacion:** Requerida (JWT)
**Permisos:** Solo trabajadores activos (`EsTrabajador`)

#### Headers requeridos

| Header          | Valor              |
|-----------------|--------------------|
| `Authorization` | `Bearer <token>`   |
| `Content-Type`  | `application/json` |

#### Body (Request)

Todos los campos son opcionales — envia solo lo que quieres cambiar.

```json
{
  "activo": false,
  "limite_requests_diario": 200,
  "fecha_expiracion": "2027-06-30T23:59:59Z",
  "rotar_key": true
}
```

**Descripcion de campos:**

| Campo                    | Tipo       | Requerido | Descripcion |
|--------------------------|------------|-----------|-------------|
| `activo`                 | `boolean`  | No        | `false` bloquea inmediatamente al cliente |
| `limite_requests_diario` | `integer`  | No        | Nuevo limite de requests diarios |
| `fecha_expiracion`       | `datetime` | No        | Nueva fecha de expiracion (ISO 8601) |
| `rotar_key`              | `boolean`  | No        | Si `true`, genera una nueva key. La antigua queda invalida al instante |

#### Parametros de URL / Query params

| Parametro | Tipo      | Descripcion |
|-----------|-----------|-------------|
| `id`      | `integer` | ID del ApiClient |

#### Respuestas

**`200 OK` — Sin rotacion de key**

```json
{
  "id": 3,
  "institucion": "Clinica Bio-Bio SpA",
  "activo": false,
  "limite_requests_diario": 200,
  "fecha_expiracion": "2027-06-30T23:59:59Z",
  "mensaje": "ApiClient actualizado correctamente."
}
```

**`200 OK` — Con rotacion de key (`rotar_key: true`)**

```json
{
  "id": 3,
  "institucion": "Clinica Bio-Bio SpA",
  "activo": true,
  "limite_requests_diario": 500,
  "fecha_expiracion": null,
  "mensaje": "ApiClient actualizado correctamente.",
  "nueva_api_key": "b9e1d4f2a0c856e7f3421bcd9078ef3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e",
  "advertencia": "La key anterior queda invalida inmediatamente. Actualiza el ERP de la clinica ahora."
}
```

> **Importante:** Si `rotar_key` es `true`, el campo `nueva_api_key` solo aparece en esta respuesta. Guardala antes de cerrar.

**`404 Not Found`**

```json
{
  "error": "ApiClient no encontrado."
}
```

#### Ejemplo completo

```javascript
// Desactivar un cliente (bloquear acceso)
const res = await fetch('/api/integrations/api-clients/3/', {
  method: 'PATCH',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({ activo: false })
});
const data = await res.json();
```

```javascript
// Rotar la key (la clinica perdio la anterior)
const res = await fetch('/api/integrations/api-clients/3/', {
  method: 'PATCH',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({ rotar_key: true })
});
const data = await res.json();
// Entregar data.nueva_api_key a la clinica por canal seguro
```

---

### DELETE Eliminar API Client

Elimina permanentemente un ApiClient. La key asociada queda invalida de inmediato.

**URL:** `DELETE /api/integrations/api-clients/{id}/`
**Autenticacion:** Requerida (JWT)
**Permisos:** Solo trabajadores activos (`EsTrabajador`)

#### Headers requeridos

| Header          | Valor            |
|-----------------|------------------|
| `Authorization` | `Bearer <token>` |

#### Body (Request)

No aplica.

#### Parametros de URL / Query params

| Parametro | Tipo      | Descripcion |
|-----------|-----------|-------------|
| `id`      | `integer` | ID del ApiClient a eliminar |

#### Respuestas

**`204 No Content` — Eliminado correctamente**

Sin body.

**`404 Not Found`**

```json
{
  "error": "ApiClient no encontrado."
}
```

#### Ejemplo completo

```javascript
const res = await fetch('/api/integrations/api-clients/3/', {
  method: 'DELETE',
  headers: { 'Authorization': `Bearer ${token}` }
});

if (res.status === 204) {
  console.log('ApiClient eliminado correctamente.');
}
```

---

# Pagos

---

### POST Iniciar pago Webpay

**URL:** `POST /api/payments/webpay/iniciar/`
**Autenticacion:** Requerida (JWT)
**Permisos:** Solo clientes

#### Headers requeridos

| Header          | Valor              |
|-----------------|--------------------|
| `Authorization` | `Bearer <token>`   |
| `Content-Type`  | `application/json` |

#### Body (Request)

```json
{
  "pedido_id": 42
}
```

**Descripcion de campos:**

| Campo      | Tipo      | Requerido | Default | Descripcion |
|------------|-----------|-----------|---------|-------------|
| `pedido_id`| `integer` | Si        | -       | ID pedido |

#### Parametros de URL / Query params

No aplica.

#### Respuestas

**`201 Created`**

```json
{
  "transaccion_pago_id": 15,
  "pedido_id": 42,
  "buy_order": "PED-42",
  "session_id": "USER-7-PED-42",
  "amount": 59500,
  "token": "<token>",
  "url": "https://webpay.url",
  "redirect_url": "https://webpay.url?token=..."
}
```

**`200 OK`** (si ya existe transaccion iniciada)

```json
{
  "detail": "Ya existe una transaccion Webpay iniciada para este pedido.",
  "transaccion_pago": {
    "id": 15,
    "pedido": 42,
    "pedido_id": 42,
    "pedido_total": 59500,
    "metodo_pago": "WEBPAY",
    "estado_pago": "INICIADO",
    "monto_confirmado": 59500,
    "buy_order": "PED-42",
    "session_id": "USER-7-PED-42",
    "token_ws": "<token>",
    "id_transaccion_externa": "<token>",
    "authorization_code": null,
    "response_code": null,
    "payment_type_code": null,
    "installments_number": null,
    "card_last_digits": null,
    "webpay_status": null,
    "transaction_date": null,
    "raw_response": null,
    "fecha_creacion": "2025-07-10T14:32:00Z",
    "fecha_confirmacion": null,
    "observacion": "Transaccion Webpay iniciada."
  }
}
```

**`403 Forbidden`**

```json
{
  "detail": "Solo los clientes pueden pagar pedidos con Webpay."
}
```

**`404 Not Found`**

```json
{
  "detail": "No existe un pedido con el ID indicado."
}
```

#### Ejemplo completo

```javascript
const res = await fetch('/api/payments/webpay/iniciar/', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({ pedido_id: 42 })
});
const data = await res.json();
```

---

### GET/POST Commit Webpay

Confirma transaccion Webpay (callback).

**URL:** `GET /api/payments/webpay/commit/?token_ws=...`
**URL:** `POST /api/payments/webpay/commit/`
**Autenticacion:** No requerida
**Permisos:** Publico

#### Headers requeridos

Para POST:

| Header          | Valor              |
|-----------------|--------------------|
| `Content-Type`  | `application/json` |

#### Body (Request)

Para POST:

```json
{
  "token_ws": "<token>"
}
```

#### Parametros de URL / Query params

| Parametro | Tipo     | Descripcion |
|----------|----------|-------------|
| `token_ws` | `string` | Token Webpay (GET) |

#### Respuestas

**`200 OK`**

```json
{
  "transaccion_pago_id": 15,
  "pedido_id": 42,
  "aprobada": true,
  "estado_pago": "CONFIRMADO",
  "estado_pedido": "APROBADO",
  "webpay": {
    "status": "AUTHORIZED",
    "response_code": 0
  },
  "despacho": {
    "id": 7,
    "estado_envio": "PENDIENTE",
    "creado": true
  }
}
```

**`400 Bad Request`**

```json
{
  "buy_order": "La orden de compra devuelta por Webpay no coincide con la transaccion local."
}
```

**`404 Not Found`**

```json
{
  "detail": "No se encontro una transaccion local asociada al token_ws recibido."
}
```

#### Ejemplo completo

```javascript
const res = await fetch('/api/payments/webpay/commit/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ token_ws: tokenWs })
});
const data = await res.json();
```

---

### GET Estado Webpay

**URL:** `GET /api/payments/webpay/estado/{token_ws}/`
**Autenticacion:** Requerida (JWT)
**Permisos:** Cliente duenno

#### Headers requeridos

| Header          | Valor            |
|-----------------|------------------|
| `Authorization` | `Bearer <token>` |

#### Body (Request)

No aplica.

#### Parametros de URL / Query params

| Parametro | Tipo     | Descripcion |
|----------|----------|-------------|
| `token_ws` | `string` | Token Webpay |

#### Respuestas

**`200 OK`**

```json
{
  "transaccion_pago": {
    "id": 15,
    "pedido": 42,
    "pedido_id": 42,
    "pedido_total": 59500,
    "metodo_pago": "WEBPAY",
    "estado_pago": "CONFIRMADO",
    "monto_confirmado": 59500,
    "buy_order": "PED-42",
    "session_id": "USER-7-PED-42",
    "token_ws": "<token>",
    "id_transaccion_externa": "<token>",
    "authorization_code": "123456",
    "response_code": 0,
    "payment_type_code": "VD",
    "installments_number": 0,
    "card_last_digits": "1234",
    "webpay_status": "AUTHORIZED",
    "transaction_date": "2025-07-10T14:40:00Z",
    "raw_response": {},
    "fecha_creacion": "2025-07-10T14:32:00Z",
    "fecha_confirmacion": "2025-07-10T14:40:00Z",
    "observacion": "Pago confirmado correctamente por Webpay."
  },
  "webpay": {
    "status": "AUTHORIZED",
    "response_code": 0
  }
}
```

**`403 Forbidden`**

```json
{
  "detail": "No puedes consultar una transaccion que no pertenece a tu cuenta."
}
```

**`404 Not Found`**

```json
{
  "detail": "No se encontro una transaccion asociada al token indicado."
}
```

#### Ejemplo completo

```javascript
const res = await fetch('/api/payments/webpay/estado/abc123/', {
  headers: { 'Authorization': `Bearer ${token}` }
});
const data = await res.json();
```

---

### GET Mis pagos

**URL:** `GET /api/payments/mis-pagos/`
**Autenticacion:** Requerida (JWT)
**Permisos:** Solo clientes

#### Headers requeridos

| Header          | Valor            |
|-----------------|------------------|
| `Authorization` | `Bearer <token>` |

#### Body (Request)

No aplica.

#### Parametros de URL / Query params

No aplica.

#### Respuestas

**`200 OK`**

```json
[
  {
    "id": 15,
    "pedido": 42,
    "pedido_id": 42,
    "pedido_total": 59500,
    "metodo_pago": "WEBPAY",
    "estado_pago": "CONFIRMADO",
    "monto_confirmado": 59500,
    "buy_order": "PED-42",
    "session_id": "USER-7-PED-42",
    "token_ws": "<token>",
    "id_transaccion_externa": "<token>",
    "authorization_code": "123456",
    "response_code": 0,
    "payment_type_code": "VD",
    "installments_number": 0,
    "card_last_digits": "1234",
    "webpay_status": "AUTHORIZED",
    "transaction_date": "2025-07-10T14:40:00Z",
    "raw_response": {},
    "fecha_creacion": "2025-07-10T14:32:00Z",
    "fecha_confirmacion": "2025-07-10T14:40:00Z",
    "observacion": "Pago confirmado correctamente por Webpay."
  }
]
```

**`403 Forbidden`**

```json
{
  "detail": "Solo los clientes pueden consultar sus pagos."
}
```

#### Ejemplo completo

```javascript
const res = await fetch('/api/payments/mis-pagos/', {
  headers: { 'Authorization': `Bearer ${token}` }
});
const data = await res.json();
```

---

### GET Todos los pagos (trabajadores)

Lista todas las transacciones de pago del sistema, enriquecidas con datos del cliente y del pedido asociado. Permite filtrar por estado o método de pago mediante query params.

**URL:** `GET /api/payments/todos/`
**Autenticacion:** Requerida (JWT)
**Permisos:** Solo Administrador, Ejecutivo o Analista

#### Headers requeridos

| Header          | Valor            |
|-----------------|------------------|
| `Authorization` | `Bearer <token>` |

#### Body (Request)

No aplica.

#### Parametros de URL / Query params

| Parametro      | Tipo     | Requerido | Descripcion |
|----------------|----------|-----------|-------------|
| `estado_pago`  | `string` | No        | Filtra por estado. Valores: `PENDIENTE`, `INICIADO`, `AUTORIZADO`, `CONFIRMADO`, `RECHAZADO`, `ANULADO`, `REEMBOLSADO`, `ERROR` |
| `metodo_pago`  | `string` | No        | Filtra por metodo. Valores: `WEBPAY`, `MERCADOPAGO`, `TRANSFERENCIA`, `CREDITO_INSTITUCIONAL` |

#### Respuestas

**`200 OK`**

```json
[
  {
    "id": 15,
    "pedido_id": 42,
    "pedido_total": 59500,
    "cliente_id": 7,
    "cliente_nombre": "Juan Perez",
    "cliente_rut": "12345678-9",
    "cliente_email": "cliente@medistock.cl",
    "metodo_pago": "WEBPAY",
    "estado_pago": "CONFIRMADO",
    "monto_confirmado": 59500,
    "buy_order": "PED-42",
    "authorization_code": "123456",
    "response_code": 0,
    "payment_type_code": "VD",
    "installments_number": 0,
    "card_last_digits": "1234",
    "webpay_status": "AUTHORIZED",
    "transaction_date": "2025-07-10T14:40:00Z",
    "fecha_creacion": "2025-07-10T14:32:00Z",
    "fecha_confirmacion": "2025-07-10T14:40:00Z",
    "observacion": "Pago confirmado correctamente por Webpay."
  }
]
```

**`403 Forbidden`**

```json
{
  "detail": "Solo Administrador, Ejecutivo o Analista pueden ver todos los pagos."
}
```

#### Ejemplo completo

```javascript
// Listar todos los pagos confirmados
const res = await fetch('/api/payments/todos/?estado_pago=CONFIRMADO', {
  headers: { 'Authorization': `Bearer ${token}` }
});
const data = await res.json();
```

```javascript
// Listar todos los pagos sin filtro
const res = await fetch('/api/payments/todos/', {
  headers: { 'Authorization': `Bearer ${token}` }
});
const data = await res.json();
```