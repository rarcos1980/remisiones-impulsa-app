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
    txt_folio = ft.TextField(label="Folio Remisión", value=f"REM-{datetime.now().strftime('%d%H%M')}", read_only=True, col={"md": 4, "xs": 12})
    txt_fecha = ft.TextField(label="Fecha", value=datetime.now().strftime("%d/%m/%Y"), col={"md": 4, "xs": 12})
    txt_cliente = ft.TextField(label="Cliente / Clínica", hint_text="Nombre del Cliente", col={"md": 6, "xs": 10})
    txt_direccion = ft.TextField(label="Dirección Cliente", col={"md": 12, "xs": 12})
    txt_vendedor = ft.TextField(label="Vendedor / Agente", value="DANIEL ALEJANDRO VIELMA TELLE", col={"md": 5, "xs": 12})

    def abrir_buscador_cliente(e):
        def cliente_seleccionado(clave, nombre, direccion):
            txt_cliente.value = f"{nombre} ({clave})"
            txt_direccion.value = direccion
            page.update()
        search_dialogs.search_clients_dialog(page, cliente_seleccionado)

    btn_buscar_cliente = ft.IconButton(
        icon=ft.Icons.SEARCH,
        tooltip="Buscar Cliente en Catálogo",
        on_click=abrir_buscador_cliente,
        col={"md": 1, "xs": 2}
    )

    # Campos eliminados a petición del usuario (Paciente, Doctor, etc.)

    # Totales UI
    lbl_subtotal = ft.Text(value="$0.00", size=16, weight=ft.FontWeight.BOLD)
    lbl_iva = ft.Text(value="$0.00", size=16, weight=ft.FontWeight.BOLD)
    lbl_total = ft.Text(value="$0.00", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_700)

    # Formulario Agregar Partida
    txt_part_cant = ft.TextField(label="Cant.", value="1", keyboard_type=ft.KeyboardType.NUMBER, col={"md": 1, "xs": 4})
    txt_part_cve = ft.TextField(label="Cve. Prod", col={"md": 2, "xs": 6})
    txt_part_alg = ft.TextField(label="ALG", col={"md": 1, "xs": 3})
    txt_part_descr = ft.TextField(label="Descripción del Producto", col={"md": 4, "xs": 9})
    txt_part_lote = ft.TextField(label="Lote", col={"md": 2, "xs": 4})
    txt_part_precio = ft.TextField(label="Precio U.", value="0.00", keyboard_type=ft.KeyboardType.NUMBER, col={"md": 2, "xs": 4})

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
        on_click=abrir_buscador_producto,
        col={"md": 1, "xs": 2}
    )

    lv_partidas = ft.Column(spacing=5)

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
            
            def btn_eliminar_click(e, p_item=p):
                items_partidas.remove(p_item)
                for t in lv_partidas.controls[:]:
                    if t.data == p_item:
                        lv_partidas.controls.remove(t)
                calcular_totales()

            # TextFields editables en el carrito
            txt_qty = ft.TextField(value=str(cant), label="Cant.", width=80, keyboard_type=ft.KeyboardType.NUMBER, dense=True)
            txt_prc = ft.TextField(value=f"{pu:.2f}", label="Precio $", width=100, keyboard_type=ft.KeyboardType.NUMBER, dense=True)
            lbl_tot = ft.Text(f"${tot:,.2f}", weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_700)

            def update_item_totals(e):
                try:
                    new_cant = float(txt_qty.value or 0)
                    new_pu = float(txt_prc.value or 0)
                    p['cantidad'] = new_cant
                    p['precio_unitario'] = new_pu
                    p['total_partida'] = new_cant * new_pu
                    lbl_tot.value = f"${p['total_partida']:,.2f}"
                    calcular_totales()
                except ValueError:
                    pass

            txt_qty.on_change = update_item_totals
            txt_prc.on_change = update_item_totals

            tile = ft.Container(
                content=ft.ListTile(
                    leading=ft.Icon(ft.Icons.SHOPPING_CART, color=ft.Colors.BLUE_500),
                    title=ft.Text(f"{p['descripcion']} (Cve: {p['cve_producto']})", weight=ft.FontWeight.BOLD),
                    subtitle=ft.Row([txt_qty, txt_prc, ft.Text("Total:"), lbl_tot, ft.Text(f"Lote: {p['lote']}")], wrap=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    trailing=ft.IconButton(icon=ft.Icons.DELETE, icon_color=ft.Colors.RED, on_click=btn_eliminar_click)
                ),
                data=p,
                bgcolor=ft.Colors.WHITE,
                border=ft.border.all(1, ft.Colors.GREY_300),
                border_radius=8
            )
            lv_partidas.controls.append(tile)
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
                'electrofisiologia': False,
                'radiologia': False,
                'cardiologia': False,
                'endovascular': False,
                'neuromodulacion': False
            },
            'subtotal': subtotal,
            'descuento_pct': 0.0,
            'descuento_monto': 0.0,
            'iva': iva,
            'total': total,
            'total_letra': f"{total:,.2f} PESOS M.N.",
            'nombre_paciente': "",
            'nombre_doctor': "",
            'episodio': "",
            'aseguradora': "",
            'diagnostico': "",
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

    # 1. Acordeón para Datos Generales
    acordeon_cliente = ft.ExpansionTile(
        title=ft.Text("1. Datos Generales de la Remisión", weight=ft.FontWeight.BOLD, size=16),
        expanded=True,
        controls=[
            ft.Container(padding=10, content=ft.Column([
                ft.ResponsiveRow([txt_folio, txt_fecha]),
                ft.ResponsiveRow([txt_cliente, btn_buscar_cliente, txt_vendedor]),
                ft.ResponsiveRow([txt_direccion])
            ]))
        ]
    )

    # 2. Body Principal Scrolleable
    body = ft.Column(
        controls=[
            ft.Row([
                ft.Text("REMISIONES Y VENTAS", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_900),
                btn_sync_sae
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            acordeon_cliente,
            ft.Divider(),
            ft.Text("2. Buscador y Captura de Productos:", weight=ft.FontWeight.BOLD, size=16),
            ft.ResponsiveRow([
                txt_part_cant, txt_part_cve, btn_buscar_producto, 
                txt_part_alg, txt_part_descr, txt_part_lote, txt_part_precio, 
                ft.Container(ft.Button("Agregar", icon=ft.Icons.ADD, on_click=agregar_partida_click), col={"md": 2, "xs": 12})
            ]),
            ft.Divider(),
            ft.Text("3. Carrito de Compras:", weight=ft.FontWeight.BOLD, size=16),
            lv_partidas
        ],
        scroll=ft.ScrollMode.AUTO,
        expand=True
    )

    # 3. Sticky Bottom Bar para Totales
    barra_inferior = ft.Container(
        content=ft.ResponsiveRow([
            ft.Column([
                ft.Row([ft.Text("Subtotal:", size=12, color=ft.Colors.GREY_600), lbl_subtotal]),
                ft.Row([ft.Text("IVA (16%):", size=12, color=ft.Colors.GREY_600), lbl_iva])
            ], col={"md": 3, "xs": 12}),
            ft.Column([
                ft.Text("TOTAL A COBRAR:", size=14, weight=ft.FontWeight.BOLD), lbl_total
            ], col={"md": 4, "xs": 12}),
            ft.Column([
                ft.Button("GUARDAR Y COBRAR", icon=ft.Icons.CHECK_CIRCLE, style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN_700, color=ft.Colors.WHITE), on_click=guardar_y_generar_pdf, height=50)
            ], col={"md": 5, "xs": 12})
        ]),
        padding=10,
        bgcolor=ft.Colors.GREY_100,
        border_radius=8,
        border=ft.border.all(1, ft.Colors.GREY_300)
    )

    view_remisiones = ft.Container(
        content=ft.Column([
            body,
            barra_inferior
        ]),
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
    
    txt_cfg_host = ft.TextField(label="Servidor / Host (IP o localhost)", value=cfg_actual.get('host', 'localhost'), col={"md": 8, "xs": 12})
    txt_cfg_database = ft.TextField(label="Ruta Base de Datos Firebird (.FDB)", value=cfg_actual.get('database', ''), col={"md": 12, "xs": 12})
    txt_cfg_empresa = ft.TextField(label="No. Empresa (ej: 01, 07)", value=cfg_actual.get('empresa', '01'), col={"md": 4, "xs": 12})
    txt_cfg_user = ft.TextField(label="Usuario Firebird", value=cfg_actual.get('user', 'SYSDBA'), col={"md": 6, "xs": 12})
    txt_cfg_password = ft.TextField(label="Contraseña", value=cfg_actual.get('password', 'masterkey'), password=True, can_reveal_password=True, col={"md": 6, "xs": 12})

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
            ft.ResponsiveRow([txt_cfg_host, txt_cfg_empresa]),
            ft.ResponsiveRow([txt_cfg_database]),
            ft.ResponsiveRow([txt_cfg_user, txt_cfg_password]),
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
    ft.run(main)
