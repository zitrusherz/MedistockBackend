# Estructura del proyecto

Rutas relativas desde la raiz del proyecto.

```
./
|-- .git/
|-- .github/
|-- .idea/
|-- .venv/
|-- api.http
|-- api.md
|-- documentacion_api.md
|-- estructura_proyecto.md
|-- manage.py
|-- requirements.txt
|-- usuarios_cockpit.txt
|-- apps/
|   |-- __init__.py
|   |-- __pycache__/
|   |-- accounts/
|   |   |-- __init__.py
|   |   |-- __pycache__/
|   |   |-- admin.py
|   |   |-- apps.py
|   |   |-- migrations/
|   |   |   |-- __init__.py
|   |   |   |-- 0001_initial.py
|   |   |   |-- __pycache__/
|   |   |-- models.py
|   |   |-- permissions.py
|   |   |-- serializers.py
|   |   |-- signals.py
|   |   |-- tests.py
|   |   |-- urls.py
|   |   |-- validators.py
|   |   |-- views.py
|   |-- billing/
|   |   |-- __init__.py
|   |   |-- __pycache__/
|   |   |-- admin.py
|   |   |-- apps.py
|   |   |-- migrations/
|   |   |   |-- __init__.py
|   |   |   |-- 0001_initial.py
|   |   |   |-- __pycache__/
|   |   |-- models.py
|   |   |-- tests.py
|   |   |-- views.py
|   |-- integrations/
|   |   |-- __init__.py
|   |   |-- __pycache__/
|   |   |-- admin.py
|   |   |-- apps.py
|   |   |-- migrations/
|   |   |   |-- __init__.py
|   |   |   |-- 0001_initial.py
|   |   |   |-- __pycache__/
|   |   |-- models.py
|   |   |-- tests.py
|   |   |-- views.py
|   |-- inventory/
|   |   |-- __init__.py
|   |   |-- __pycache__/
|   |   |-- admin.py
|   |   |-- apps.py
|   |   |-- migrations/
|   |   |   |-- __init__.py
|   |   |   |-- 0001_initial.py
|   |   |   |-- __pycache__/
|   |   |-- models.py
|   |   |-- permissions.py
|   |   |-- serializers.py
|   |   |-- tests.py
|   |   |-- urls.py
|   |   |-- views.py
|   |-- locations/
|   |   |-- __init__.py
|   |   |-- __pycache__/
|   |   |-- admin.py
|   |   |-- apps.py
|   |   |-- migrations/
|   |   |   |-- __init__.py
|   |   |   |-- 0001_initial.py
|   |   |   |-- 0002_alter_sucursal_options.py
|   |   |   |-- 0003_alter_sucursal_options.py
|   |   |   |-- 0004_comunachilexpress.py
|   |   |   |-- __pycache__/
|   |   |-- models.py
|   |   |-- serializers.py
|   |   |-- tests.py
|   |   |-- urls.py
|   |   |-- views.py
|   |-- logistics/
|   |   |-- __init__.py
|   |   |-- __pycache__/
|   |   |-- admin.py
|   |   |-- apps.py
|   |   |-- migrations/
|   |   |   |-- __init__.py
|   |   |   |-- 0001_initial.py
|   |   |   |-- 0002_chilexpressapilog.py
|   |   |   |-- __pycache__/
|   |   |-- models.py
|   |   |-- serializers.py
|   |   |-- services/
|   |   |   |-- __pycache__/
|   |   |   |-- chilexpress.py
|   |   |   |-- logistica.py
|   |   |   |-- poblar_comunas_chilexpress.py
|   |   |   |-- static_data/
|   |   |   |   |-- comunas_biobio.json
|   |   |   |   |-- comunas_maule.json
|   |   |   |   |-- comunas_R1.json
|   |   |   |   |-- comunas_R10.json
|   |   |   |   |-- comunas_R11.json
|   |   |   |   |-- comunas_R12.json
|   |   |   |   |-- comunas_R14.json
|   |   |   |   |-- comunas_R15.json
|   |   |   |   |-- comunas_R16.json
|   |   |   |   |-- comunas_R2.json
|   |   |   |   |-- comunas_R3.json
|   |   |   |   |-- comunas_R4.json
|   |   |   |   |-- comunas_R5.json
|   |   |   |   |-- comunas_R6.json
|   |   |   |   |-- comunas_R7.json
|   |   |   |   |-- comunas_R8.json
|   |   |   |   |-- comunas_R9.json
|   |   |   |   |-- comunas_RM.json
|   |   |   |   |-- comunas_santiago.json
|   |   |   |   |-- guardar_consulta.py
|   |   |   |   |-- regiones.json
|   |   |-- tests.py
|   |   |-- urls.py
|   |   |-- utils.py
|   |   |-- views.py
|   |-- orders/
|   |   |-- __init__.py
|   |   |-- __pycache__/
|   |   |-- admin.py
|   |   |-- apps.py
|   |   |-- migrations/
|   |   |   |-- __init__.py
|   |   |   |-- 0001_initial.py
|   |   |   |-- __pycache__/
|   |   |-- models.py
|   |   |-- permissions.py
|   |   |-- serializers.py
|   |   |-- services/
|   |   |   |-- __pycache__/
|   |   |   |-- inventario.py
|   |   |-- tests.py
|   |   |-- urls.py
|   |   |-- views.py
|   |-- payments/
|   |   |-- __init__.py
|   |   |-- __pycache__/
|   |   |-- admin.py
|   |   |-- apps.py
|   |   |-- migrations/
|   |   |   |-- __init__.py
|   |   |   |-- 0001_initial.py
|   |   |   |-- __pycache__/
|   |   |-- models.py
|   |   |-- serializers.py
|   |   |-- services/
|   |   |   |-- __pycache__/
|   |   |   |-- pedido_post_pago.py
|   |   |   |-- webpay.py
|   |   |-- tests.py
|   |   |-- urls.py
|   |   |-- views.py
|   |-- procurement/
|   |   |-- __init__.py
|   |   |-- __pycache__/
|   |   |-- admin.py
|   |   |-- apps.py
|   |   |-- migrations/
|   |   |   |-- __init__.py
|   |   |   |-- 0001_initial.py
|   |   |   |-- __pycache__/
|   |   |-- models.py
|   |   |-- tests.py
|   |   |-- views.py
|-- medistockbackend/
|   |-- .env
|   |-- __init__.py
|   |-- __pycache__/
|   |-- asgi.py
|   |-- settings.py
|   |-- urls.py
|   |-- wsgi.py
|-- templates/
```

# Modelos por app

## apps/accounts
- Usuario
- Institucion
- PerfilTrabajador
- PerfilCliente
- ConvenioInstitucion
- DireccionEntrega

## apps/billing
- TipoDocumentoTributario
- FolioDte
- DocumentoTributario
- DocumentoTributarioEmisor
- DocumentoTributarioReceptor
- DetalleDocumentoTributario
- ReferenciaDocumentoTributario
- GuiaDespacho
- EnvioDteSii
- EstadoDteHistorial

## apps/integrations
- ApiClient
- IntegracionExterna
- RegistroIntegracion

## apps/inventory
- Categoria
- Marca
- Producto
- CategoriaProducto
- Lote
- Inventario
- MovimientoInventario
- TrasladoInventario
- DetalleTrasladoInventario

## apps/locations
- Region
- Comuna
- ComunaChilexpress
- Sucursal

## apps/logistics
- Despacho
- ChilexpressApiLog

## apps/orders
- Cotizacion
- DetalleCotizacion
- Pedido
- DetallePedido
- AprobacionPedido

## apps/payments
- TransaccionPago
- ComprobantePago
- ConciliacionPago
- Aseguradora
- PagoAseguradora

## apps/procurement
- Proveedor
- CompraProveedor
- DetalleCompraProveedor

