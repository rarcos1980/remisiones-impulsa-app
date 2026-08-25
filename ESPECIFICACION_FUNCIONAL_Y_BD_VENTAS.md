# ESPECIFICACION FUNCIONAL Y BD VENTAS

## Descripción
Sistema de Remisiones Móvil conectado a Aspel SAE (Firebird).

## BD Local (SQLite - remisiones_local.db)
- encabezados_remision (id, folio, fecha, cliente_clave, nombre_cliente, direccion_cliente, rfc_cliente, subtotal, iva, total, vendedor, condicion, observaciones)
- detalle_remision (id, remision_id, cantidad, cve_producto, descripcion, precio_unitario, total_partida)

## Dependencias DLL (Firebird)
- Requiere fbclient.dll en la carpeta del ejecutable o entorno local.

## Actualización [2026-08-24]: Impuestos Dinámicos (SAE IMPUXX)
- Se agregó la tabla squemas_impuestos a SQLite (cve_esquema, descripcion, impuesto1 al 4).
- Se agregó el campo cve_esqimpu a la tabla productos y la tabla emision_partidas.
- sae_connector.py ahora lee IMPU01 y el esquema asociado por producto desde INVE01.
- El total de IVA en la remisión (main_app.py) ahora es la suma individual de (total_partida * (impuesto1/100)) dependiendo de su respectivo cve_esqimpu.

## Actualización [2026-08-24]: Formas de Pago y Corte de Caja
- El campo condicion en el cobro ahora está restringido a: EFECTIVO, TARJETA CREDITO, TARJETA DEBITO, TRANSFERENCIA, CREDITO.
- Nueva función SQL generar_corte_dia en db_local.py que agrupa remisiones por condicion y echa.
- Se agregó interfaz de "Corte del Día" en la pestaña Historial.
