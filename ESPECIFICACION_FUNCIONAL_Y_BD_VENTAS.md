# ESPECIFICACION FUNCIONAL Y BD VENTAS

## Descripción
Sistema de Remisiones Móvil conectado a Aspel SAE (Firebird).

## BD Local (SQLite - remisiones_local.db)
- encabezados_remision (id, folio, fecha, cliente_clave, nombre_cliente, direccion_cliente, rfc_cliente, subtotal, iva, total, vendedor, condicion, observaciones)
- detalle_remision (id, remision_id, cantidad, cve_producto, descripcion, precio_unitario, total_partida)

## Dependencias DLL (Firebird)
- Requiere fbclient.dll en la carpeta del ejecutable o entorno local.
