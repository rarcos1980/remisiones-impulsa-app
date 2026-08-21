import flet as ft
import os
from datetime import datetime
import db_local
import pdf_generator
import search_dialogs
import sae_connector

def main(page: ft.Page):
    page.title = "PTOVENTAMOVIL - Punto de Venta Móvil"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 10
    page.scroll = ft.ScrollMode.AUTO
    
    # Inicializar BD local
    db_local.init_db()

    # Variables de Estado de la Remisión
    items_partidas = []
    
    # Botón de Sincronización SAE
    def ejecutar_sincronizacion(e):
        ok, msg = sae_connector.sync_catalogos_desde_sae()
        icon_type = ft.Icons.CHECK_CIRCLE if ok else ft.Icons.ERROR
        color_type = ft.Colors.GREEN if ok else ft.Colors.RED
        dlg = ft.AlertDialog(
            title=ft.Row([ft.Icon(icon_type, color=color_type), ft.Text("Sincronizador SAE")]),
            content=ft.Text(msg),
            actions=[ft.TextButton("Aceptar", on_click=lambda ev: page.pop_dialog())]
        )
        page.show_dialog(dlg)

    btn_sync_sae = ft.Button(
        "Sincronizar SAE",
        icon=ft.Icons.SYNC,
        style=ft.ButtonStyle(color=ft.Colors.WHITE, bgcolor=ft.Colors.BLUE_800),
        on_click=ejecutar_sincronizacion
    )

    # ══════════════════════════════════════════════════════════════════════
    # VISTA 1: CAPTURA DE REMISIONES / VENTAS
    # ══════════════════════════════════════════════════════════════════════
    txt_folio = ft.TextField(label="Folio Remisión", value=f"REM-{datetime.now().strftime('%d%H%M')}", width=160, read_only=True)
    txt_fecha = ft.TextField(label="Fecha", value=datetime.now().strftime("%d/%m/%Y"), width=130)
    txt_cliente = ft.TextField(label="Cliente / Clínica", hint_text="Nombre del Cliente", expand=True)
    txt_direccion = ft.TextField(label="Dirección Cliente", expand=True)
    txt_vendedor = ft.TextField(label="Vendedor / Agente", value="DANIEL ALEJANDRO VIELMA TELLE", expand=True)

    def abrir_buscador_cliente(e):
        def cliente_seleccionado(clave, nombre, direccion):
            txt_cliente.value = f"{nombre} ({clave})"
            txt_direccion.value = direccion
            page.update()
        search_dialogs.search_clients_dialog(page, cliente_seleccionado)

    btn_buscar_cliente = ft.IconButton(
        icon=ft.Icons.SEARCH,
        tooltip="Buscar Cliente en Catálogo",
        on_click=abrir_buscador_cliente
    )

    # Checkboxes Especialidades Médicas
    chk_electrofisiologia = ft.Checkbox(label="Electrofisiología", value=False)
    chk_radiologia = ft.Checkbox(label="Radiología", value=False)
    chk_cardiologia = ft.Checkbox(label="Cardiología", value=False)
    chk_endovascular = ft.Checkbox(label="Endovascular", value=False)
    chk_neuromodulacion = ft.Checkbox(label="Neuromodulación", value=False)

    # Campos Expediente Médicos
    txt_paciente = ft.TextField(label="Paciente", expand=True)
    txt_doctor = ft.TextField(label="Doctor", expand=True)
    txt_episodio = ft.TextField(label="Episodio", width=140)
    txt_aseguradora = ft.TextField(label="Aseguradora", width=180)
    txt_diagnostico = ft.TextField(label="Diagnóstico", expand=True)

    # Totales UI
    lbl_subtotal = ft.Text(value="$0.00", size=16, weight=ft.FontWeight.BOLD)
    lbl_iva = ft.Text(value="$0.00", size=16, weight=ft.FontWeight.BOLD)
    lbl_total = ft.Text(value="$0.00", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_700)

    # Formulario Agregar Partida
    txt_part_cant = ft.TextField(label="Cant.", value="1", width=70, keyboard_type=ft.KeyboardType.NUMBER)
    txt_part_cve = ft.TextField(label="Cve. Prod", width=110)
    txt_part_alg = ft.TextField(label="ALG", width=70)
    txt_part_descr = ft.TextField(label="Descripción del Producto", expand=True)
    txt_part_lote = ft.TextField(label="Lote", width=110)
    txt_part_precio = ft.TextField(label="Precio U.", value="0.00", width=100, keyboard_type=ft.KeyboardType.NUMBER)

    def abrir_buscador_producto(e):
        def producto_seleccionado(clave, descripcion, precio):
            txt_part_cve.value = clave
            txt_part_descr.value = descripcion
            txt_part_precio.value = f"{precio:.2f}"
            page.update()
        search_dialogs.search_products_dialog(page, producto_seleccionado)

    btn_buscar_producto = ft.IconButton(
        icon=ft.Icons.SEARCH,
        tooltip="Buscar Producto en Catálogo",
        on_click=abrir_buscador_producto
    )

    dt_partidas = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Cant.")),
            ft.DataColumn(ft.Text("Clave")),
            ft.DataColumn(ft.Text("ALG")),
            ft.DataColumn(ft.Text("Descripción")),
            ft.DataColumn(ft.Text("Lote")),
            ft.DataColumn(ft.Text("Precio U.")),
            ft.DataColumn(ft.Text("Total")),
        ],
        rows=[]
    )

    def calcular_totales():
        subtotal = sum(p['total_partida'] for p in items_partidas)
        iva = subtotal * 0.16
        total = subtotal + iva
        lbl_subtotal.value = f"${subtotal:,.2f}"
        lbl_iva.value = f"${iva:,.2f}"
        lbl_total.value = f"${total:,.2f}"
        page.update()

    def agregar_partida_click(e):
        if not txt_part_descr.value:
            page.open(ft.SnackBar(ft.Text("Escriba la descripción del producto")))
            return
        
        try:
            cant = float(txt_part_cant.value or 1)
            pu = float(txt_part_precio.value or 0)
            tot = cant * pu
            
            p = {
                'cantidad': cant,
                'cve_producto': txt_part_cve.value or '',
                'alg': txt_part_alg.value or '',
                'descripcion': txt_part_descr.value,
                'lote': txt_part_lote.value or '',
                'precio_unitario': pu,
                'total_partida': tot
            }
            items_partidas.append(p)
            
            txt_part_cant.value = "1"
            txt_part_cve.value = ""
            txt_part_alg.value = ""
            txt_part_descr.value = ""
            txt_part_lote.value = ""
            txt_part_precio.value = "0.00"
            
            dt_partidas.rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(f"{cant:.2f}")),
                        ft.DataCell(ft.Text(p['cve_producto'])),
                        ft.DataCell(ft.Text(p['alg'])),
                        ft.DataCell(ft.Text(p['descripcion'])),
                        ft.DataCell(ft.Text(p['lote'])),
                        ft.DataCell(ft.Text(f"${pu:,.2f}")),
                        ft.DataCell(ft.Text(f"${tot:,.2f}")),
                    ]
                )
            )
            calcular_totales()
        except ValueError:
            page.open(ft.SnackBar(ft.Text("Valores numéricos inválidos en cantidad o precio")))

    def guardar_y_generar_pdf(e):
        if not txt_cliente.value:
            page.open(ft.SnackBar(ft.Text("Por favor ingrese el nombre del Cliente")))
            return
        if not items_partidas:
            page.open(ft.SnackBar(ft.Text("Debe agregar al menos una partida a la remisión")))
            return
        
        subtotal = sum(p['total_partida'] for p in items_partidas)
        iva = subtotal * 0.16
        total = subtotal + iva

        datos_remision = {
            'folio': txt_folio.value,
            'fecha': txt_fecha.value,
            'nombre_cliente': txt_cliente.value,
            'direccion_cliente': txt_direccion.value,
            'nombre_vendedor': txt_vendedor.value,
            'especialidades': {
                'electrofisiologia': chk_electrofisiologia.value,
                'radiologia': chk_radiologia.value,
                'cardiologia': chk_cardiologia.value,
                'endovascular': chk_endovascular.value,
                'neuromodulacion': chk_neuromodulacion.value
            },
            'subtotal': subtotal,
            'descuento_pct': 0.0,
            'descuento_monto': 0.0,
            'iva': iva,
            'total': total,
            'total_letra': f"{total:,.2f} PESOS M.N.",
            'nombre_paciente': txt_paciente.value,
            'nombre_doctor': txt_doctor.value,
            'episodio': txt_episodio.value,
            'aseguradora': txt_aseguradora.value,
            'diagnostico': txt_diagnostico.value,
            'agente': txt_vendedor.value,
            'fecha_pagare': txt_fecha.value
        }

        out_dir = os.path.dirname(__file__)
        pdf_path = os.path.join(out_dir, f"{txt_folio.value}.pdf")
        
        try:
            # 1. Guardar en SQLite local (para persistencia y sincronización posterior con SAE)
            ok_db, rem_id, msg_db = db_local.guardar_remision_local(datos_remision, items_partidas)
            
            # 2. Generar PDF idéntico a remision.pdf
            pdf_generator.generar_pdf_remision(datos_remision, items_partidas, pdf_path)
            
            dlg = ft.AlertDialog(
                title=ft.Text("Remisión Guardada y PDF Generado"),
                content=ft.Text(f"La remisión fue registrada localmente en SQLite (ID: {rem_id}) y se generó el PDF:\n{pdf_path}"),
                actions=[ft.TextButton("OK", on_click=lambda ev: page.pop_dialog())]
            )
            page.show_dialog(dlg)
        except Exception as ex:
            page.overlay.append(ft.SnackBar(ft.Text(f"Error al procesar remisión: {str(ex)}"), open=True))
            page.update()

    view_remisiones = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Text("REMISIONES Y VENTAS", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_900),
                btn_sync_sae,
                txt_folio,
                txt_fecha
            ], wrap=True, alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Divider(),
            ft.Row([txt_cliente, btn_buscar_cliente, txt_vendedor], wrap=True),
            txt_direccion,
            ft.Divider(),
            ft.Text("Especialidades Médico-Quirúrgicas:", weight=ft.FontWeight.BOLD),
            ft.Row([chk_electrofisiologia, chk_radiologia, chk_cardiologia, chk_endovascular, chk_neuromodulacion], wrap=True),
            ft.Divider(),
            ft.Text("Expediente Médico y Paciente:", weight=ft.FontWeight.BOLD),
            ft.Row([txt_paciente, txt_doctor], wrap=True),
            ft.Row([txt_episodio, txt_aseguradora, txt_diagnostico], wrap=True),
            ft.Divider(),
            ft.Text("Agregar Producto / Partida:", weight=ft.FontWeight.BOLD),
            ft.Row([txt_part_cant, txt_part_cve, btn_buscar_producto, txt_part_alg, txt_part_descr, txt_part_lote, txt_part_precio, ft.Button("Agregar", icon=ft.Icons.ADD, on_click=agregar_partida_click)], wrap=True),
            ft.Row([dt_partidas], scroll=ft.ScrollMode.ALWAYS),
            ft.Divider(),
            ft.Row([
                ft.Column([
                    ft.Row([ft.Text("Subtotal: "), lbl_subtotal]),
                    ft.Row([ft.Text("IVA (16%): "), lbl_iva]),
                    ft.Row([ft.Text("TOTAL: "), lbl_total]),
                ]),
                ft.Button("GUARDAR Y GENERAR PDF", icon=ft.Icons.PICTURE_AS_PDF, style=ft.ButtonStyle(color=ft.Colors.WHITE, bgcolor=ft.Colors.GREEN_700), height=50, on_click=guardar_y_generar_pdf)
            ], wrap=True, alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
        ], scroll=ft.ScrollMode.AUTO),
        padding=10,
        expand=True
    )

    # ══════════════════════════════════════════════════════════════════════
    # VISTA 2: CATÁLOGO DE CLIENTES
    # ══════════════════════════════════════════════════════════════════════
    lv_clientes_cat = ft.ListView(expand=True, spacing=5, height=450)
    txt_filtro_clie = ft.TextField(label="Filtrar Clientes", hint_text="Buscar por Clave o Nombre...", expand=True)

    def cargar_tabla_clientes(e=None):
        lv_clientes_cat.controls.clear()
        filtro = (txt_filtro_clie.value or "").strip()
        try:
            conn = db_local.get_connection()
            cur = conn.cursor()
            if filtro:
                cur.execute("SELECT clave, nombre, rfc, direccion FROM clientes WHERE clave LIKE ? OR UPPER(nombre) LIKE UPPER(?) LIMIT 50", (f"%{filtro}%", f"%{filtro}%"))
            else:
                cur.execute("SELECT clave, nombre, rfc, direccion FROM clientes LIMIT 50")
            rows = cur.fetchall()
            conn.close()
            
            for r in rows:
                c_clave, c_nom, c_rfc, c_dir = r['clave'], r['nombre'], r['rfc'] or '', r['direccion'] or ''
                lv_clientes_cat.controls.append(
                    ft.ListTile(
                        leading=ft.Icon(ft.Icons.PERSON, color=ft.Colors.BLUE_800),
                        title=ft.Text(f"{c_nom} ({c_clave})", weight=ft.FontWeight.BOLD),
                        subtitle=ft.Text(f"RFC: {c_rfc} | Dirección: {c_dir}")
                    )
                )
        except Exception as ex:
            lv_clientes_cat.controls.append(ft.Text(f"Error: {str(ex)}"))
        page.update()

    txt_filtro_clie.on_change = cargar_tabla_clientes

    view_clientes = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Text("CATÁLOGO DE CLIENTES (SAE)", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_900),
                btn_sync_sae
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Divider(),
            ft.Row([txt_filtro_clie, ft.IconButton(icon=ft.Icons.REFRESH, tooltip="Actualizar Lista", on_click=cargar_tabla_clientes)]),
            lv_clientes_cat
        ]),
        padding=10
    )

    # ══════════════════════════════════════════════════════════════════════
    # VISTA 3: CATÁLOGO DE PRODUCTOS / INVENTARIO
    # ══════════════════════════════════════════════════════════════════════
    lv_productos_cat = ft.ListView(expand=True, spacing=5, height=450)
    txt_filtro_prod = ft.TextField(label="Filtrar Productos", hint_text="Buscar por Clave o Descripción...", expand=True)

    def cargar_tabla_productos(e=None):
        lv_productos_cat.controls.clear()
        filtro = (txt_filtro_prod.value or "").strip()
        try:
            conn = db_local.get_connection()
            cur = conn.cursor()
            if filtro:
                cur.execute("SELECT clave, descripcion, precio, existencia FROM productos WHERE clave LIKE ? OR UPPER(descripcion) LIKE UPPER(?) LIMIT 50", (f"%{filtro}%", f"%{filtro}%"))
            else:
                cur.execute("SELECT clave, descripcion, precio, existencia FROM productos LIMIT 50")
            rows = cur.fetchall()
            conn.close()
            
            for r in rows:
                p_cve, p_desc, p_prec, p_exis = r['clave'], r['descripcion'], float(r['precio'] or 0), float(r['existencia'] or 0)
                lv_productos_cat.controls.append(
                    ft.ListTile(
                        leading=ft.Icon(ft.Icons.INVENTORY_2, color=ft.Colors.GREEN_800),
                        title=ft.Text(f"{p_desc} ({p_cve})", weight=ft.FontWeight.BOLD),
                        subtitle=ft.Text(f"Precio: ${p_prec:,.2f} | Stock Disponible: {p_exis:.2f}")
                    )
                )
        except Exception as ex:
            lv_productos_cat.controls.append(ft.Text(f"Error: {str(ex)}"))
        page.update()

    txt_filtro_prod.on_change = cargar_tabla_productos

    view_productos = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Text("CATÁLOGO DE INVENTARIO (SAE)", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_900),
                btn_sync_sae
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Divider(),
            ft.Row([txt_filtro_prod, ft.IconButton(icon=ft.Icons.REFRESH, tooltip="Actualizar Lista", on_click=cargar_tabla_productos)]),
            lv_productos_cat
        ]),
        padding=10
    )

    # ══════════════════════════════════════════════════════════════════════
    # VISTA 4: AJUSTES Y CONFIGURACIÓN DE BASE DE DATOS SAE
    # ══════════════════════════════════════════════════════════════════════
    cfg_actual = sae_connector.load_config()
    
    txt_cfg_host = ft.TextField(label="Servidor / Host (IP o localhost)", value=cfg_actual.get('host', 'localhost'), expand=True)
    txt_cfg_database = ft.TextField(label="Ruta Base de Datos Firebird (.FDB)", value=cfg_actual.get('database', ''), expand=True)
    txt_cfg_empresa = ft.TextField(label="No. Empresa (ej: 01, 07)", value=cfg_actual.get('empresa', '01'), width=140)
    txt_cfg_user = ft.TextField(label="Usuario Firebird", value=cfg_actual.get('user', 'SYSDBA'), width=160)
    txt_cfg_password = ft.TextField(label="Contraseña", value=cfg_actual.get('password', 'masterkey'), password=True, can_reveal_password=True, width=180)

    def guardar_config_click(e):
        nuevos_datos = {
            'host': txt_cfg_host.value.strip(),
            'database': txt_cfg_database.value.strip(),
            'empresa': txt_cfg_empresa.value.strip(),
            'user': txt_cfg_user.value.strip(),
            'password': txt_cfg_password.value.strip(),
            'charset': 'UTF8'
        }
        ok, msg = sae_connector.save_config(nuevos_datos)
        page.overlay.append(ft.SnackBar(ft.Text(msg), open=True))
        page.update()

    def probar_conexion_click(e):
        ok, msg = sae_connector.test_connection()
        icon_t = ft.Icons.CHECK_CIRCLE if ok else ft.Icons.ERROR
        color_t = ft.Colors.GREEN if ok else ft.Colors.RED
        dlg = ft.AlertDialog(
            title=ft.Row([ft.Icon(icon_t, color=color_t), ft.Text("Prueba de Conexión")]),
            content=ft.Text(msg),
            actions=[ft.TextButton("Aceptar", on_click=lambda ev: page.pop_dialog())]
        )
        page.show_dialog(dlg)

    view_ajustes = ft.Container(
        content=ft.Column([
            ft.Text("CONFIGURACIÓN CONEXIÓN CON ASPEL SAE", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_900),
            ft.Text("Configure la ruta del servidor Firebird y la empresa para sincronización táctil:"),
            ft.Divider(),
            ft.Row([txt_cfg_host, txt_cfg_empresa], wrap=True),
            txt_cfg_database,
            ft.Row([txt_cfg_user, txt_cfg_password], wrap=True),
            ft.Divider(),
            ft.Row([
                ft.Button("Probar Conexión", icon=ft.Icons.NETWORK_CHECK, on_click=probar_conexion_click),
                ft.Button("Guardar Configuración", icon=ft.Icons.SAVE, style=ft.ButtonStyle(color=ft.Colors.WHITE, bgcolor=ft.Colors.GREEN_700), on_click=guardar_config_click),
            ], wrap=True)
        ], scroll=ft.ScrollMode.AUTO),
        padding=10,
        expand=True
    )

    # ══════════════════════════════════════════════════════════════════════
    # BARRA DE NAVEGACIÓN MÓVIL (TABS / PESTAÑAS)
    # ══════════════════════════════════════════════════════════════════════
    body_container = ft.Container(content=view_remisiones, expand=True)

    def cambiar_pestana(e):
        idx = e.control.selected_index
        if idx == 0:
            body_container.content = view_remisiones
        elif idx == 1:
            body_container.content = view_clientes
            cargar_tabla_clientes()
        elif idx == 2:
            body_container.content = view_productos
            cargar_tabla_productos()
        elif idx == 3:
            body_container.content = view_ajustes
        page.update()

    page.navigation_bar = ft.NavigationBar(
        destinations=[
            ft.NavigationBarDestination(icon=ft.Icons.RECEIPT_LONG, label="Remisión / Venta"),
            ft.NavigationBarDestination(icon=ft.Icons.PEOPLE, label="Clientes"),
            ft.NavigationBarDestination(icon=ft.Icons.INVENTORY, label="Inventario"),
            ft.NavigationBarDestination(icon=ft.Icons.SETTINGS, label="Ajustes SAE"),
        ],
        selected_index=0,
        on_change=cambiar_pestana
    )

    page.add(body_container)

if __name__ == "__main__":
    ft.run(target=main)
