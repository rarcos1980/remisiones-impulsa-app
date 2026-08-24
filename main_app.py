import flet as ft
import os
from datetime import datetime
import db_local
import pdf_generator
import search_dialogs
import sae_connector

def main(page: ft.Page):
    page.title = "Sistema de Remisiones Móvil"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.window_width = 400
    page.window_height = 700
    page.scroll = ft.ScrollMode.AUTO
    
    # Inicializar BD local
    db_local.init_db()

    # Variables de Estado de la Remisión
    items_partidas = []
    
    # Cargar configuración global al inicio
    cfg_actual = sae_connector.load_config()
    
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
    txt_folio = ft.TextField(label="Folio", value=datetime.now().strftime('%d%H%M'), col={"xs": 6})
    txt_fecha = ft.TextField(label="Fecha", value=datetime.now().strftime("%d/%m/%Y"), col={"xs": 6})

    # Buscador unificado
    def abrir_buscador_producto(e):
        def producto_seleccionado(clave, descripcion, precio):
            agregar_partida_directa(clave, descripcion, precio)
        search_dialogs.search_products_dialog(page, producto_seleccionado)

    txt_buscar = ft.TextField(
        label="Buscar Producto / Insumo", 
        hint_text="Escriba Clave o Descripción... (Toque para buscar)", 
        read_only=True,
        on_click=abrir_buscador_producto,
        icon=ft.Icons.SEARCH
    )

    lbl_total = ft.Text(value="$0.00", size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_700)
    lv_partidas = ft.Column(spacing=0)

    def calcular_totales():
        subtotal = sum(p['total_partida'] for p in items_partidas)
        iva = subtotal * 0.16
        total = subtotal + iva
        lbl_total.value = f"${total:,.2f}"
        page.update()

    def agregar_partida_directa(clave, descripcion, precio, cantidad_agregar=1.0):
        pu = float(precio or 0)
        
        # Verificar si el producto ya está en el carrito
        for t in lv_partidas.controls:
            p = t.data
            if p['cve_producto'] == clave:
                p['cantidad'] += cantidad_agregar
                p['total_partida'] = p['cantidad'] * p['precio_unitario']
                txt_qty = t.content.subtitle.controls[0]
                txt_qty.value = str(int(p['cantidad']) if p['cantidad'].is_integer() else p['cantidad'])
                calcular_totales()
                page.overlay.append(ft.SnackBar(ft.Text(f"Se sumó {cantidad_agregar} pieza(s) a: {descripcion}"), open=True, duration=1500))
                page.update()
                return

        p = {
            'cantidad': float(cantidad_agregar),
            'cve_producto': clave,
            'alg': '',
            'descripcion': descripcion,
            'lote': '',
            'precio_unitario': pu,
            'total_partida': pu * float(cantidad_agregar)
        }
        items_partidas.append(p)
        
        def btn_eliminar_click(e, p_item=p):
            items_partidas.remove(p_item)
            for t in lv_partidas.controls[:]:
                if t.data == p_item:
                    lv_partidas.controls.remove(t)
            calcular_totales()

        # UI del Item en el carrito
        str_cant = str(int(cantidad_agregar)) if float(cantidad_agregar).is_integer() else str(cantidad_agregar)
        txt_qty = ft.TextField(value=str_cant, label="Cant.", width=60, keyboard_type=ft.KeyboardType.NUMBER, dense=True, content_padding=5)
        txt_prc = ft.TextField(value=f"{pu:.2f}", label="Precio $", width=90, keyboard_type=ft.KeyboardType.NUMBER, dense=True, content_padding=5)
        
        def update_item_totals(e):
            try:
                new_cant = float(txt_qty.value or 0)
                new_pu = float(txt_prc.value or 0)
                p['cantidad'] = new_cant
                p['precio_unitario'] = new_pu
                p['total_partida'] = new_cant * new_pu
                calcular_totales()
            except ValueError:
                pass

        txt_qty.on_change = update_item_totals
        txt_prc.on_change = update_item_totals

        tile = ft.Container(
            content=ft.ListTile(
                title=ft.Text(f"{p['descripcion']} ({p['cve_producto']})", weight=ft.FontWeight.W_500, size=14, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                subtitle=ft.Row([txt_qty, txt_prc, ft.IconButton(icon=ft.Icons.DELETE, icon_color=ft.Colors.RED_400, on_click=btn_eliminar_click)], wrap=True, vertical_alignment=ft.CrossAxisAlignment.CENTER)
            ),
            data=p,
            bgcolor=ft.Colors.GREY_100,
            border=ft.Border(bottom=ft.BorderSide(1, ft.Colors.GREY_300)),
            padding=5
        )
        lv_partidas.controls.append(tile)
        calcular_totales()

    # MODAL DE COBRO
    txt_cobro_cliente = ft.TextField(label="Cliente", value="CLIENTE MOSTR", col={"md": 10, "xs": 10})
    txt_cobro_condicion = ft.TextField(label="Condición", value="CONTADO", col={"md": 6, "xs": 6})
    txt_cobro_vendedor = ft.TextField(label="Vendedor", value=cfg_actual.get('vendedor_predeterminado', ''), col={"md": 6, "xs": 6})
    txt_cobro_observaciones = ft.TextField(label="Observaciones", multiline=True, min_lines=2, col={"md": 12, "xs": 12})

    def abrir_buscador_cliente_modal(e):
        def cliente_seleccionado(clave, nombre, direccion):
            txt_cobro_cliente.value = f"{nombre} ({clave})"
            page.update()
        search_dialogs.search_clients_dialog(page, cliente_seleccionado)

    btn_buscar_cliente_modal = ft.IconButton(icon=ft.Icons.SEARCH, on_click=abrir_buscador_cliente_modal, col={"md": 2, "xs": 2})

    dlg_cobro = ft.AlertDialog(
        modal=True,
        title=ft.Text("Finalizar Venta"),
        content=ft.Container(
            width=400,
            content=ft.Column([
                ft.ResponsiveRow([txt_cobro_cliente, btn_buscar_cliente_modal]),
                ft.ResponsiveRow([txt_cobro_condicion, txt_cobro_vendedor]),
                ft.ResponsiveRow([txt_cobro_observaciones])
            ], tight=True)
        ),
        actions=[
            ft.TextButton("Cancelar", on_click=lambda e: cerrar_modal_cobro()),
            ft.ElevatedButton("Confirmar Cobro", bgcolor=ft.Colors.GREEN_700, color=ft.Colors.WHITE, on_click=lambda e: ejecutar_guardado())
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    def cerrar_modal_cobro():
        page.pop_dialog()

    def mostrar_modal_cobro(e):
        if not items_partidas:
            page.overlay.append(ft.SnackBar(ft.Text("Debe agregar al menos una partida a la venta"), open=True))
            page.update()
            return
        page.show_dialog(dlg_cobro)

    def ejecutar_guardado():
        cerrar_modal_cobro()
        
        subtotal = sum(p['total_partida'] for p in items_partidas)
        iva = subtotal * 0.16
        total = subtotal + iva
        
        folio_completo = f"V-{txt_folio.value}"

        datos_remision = {
            'folio': folio_completo,
            'fecha': txt_fecha.value,
            'nombre_cliente': txt_cobro_cliente.value,
            'direccion_cliente': "",
            'nombre_vendedor': txt_cobro_vendedor.value,
            'condicion': txt_cobro_condicion.value,
            'observaciones': txt_cobro_observaciones.value,
            'subtotal': subtotal,
            'descuento_pct': 0.0,
            'descuento_monto': 0.0,
            'iva': iva,
            'total': total,
            'total_letra': f"{total:,.2f} PESOS M.N.",
            'agente': txt_cobro_vendedor.value,
            'almacen': cfg_actual.get('almacen', '1')
        }

        out_dir = os.path.dirname(__file__)
        pdf_path = os.path.join(out_dir, f"TKT-{folio_completo}.pdf")
        
        try:
            ok_db, rem_id, msg_db = db_local.guardar_remision_local(datos_remision, items_partidas)
            if not ok_db:
                dlg = ft.AlertDialog(
                    title=ft.Text("Error al Guardar Venta", color=ft.Colors.RED),
                    content=ft.Text(f"Hubo un problema:\n{msg_db}"),
                    actions=[ft.TextButton("Aceptar", on_click=lambda ev: page.pop_dialog())]
                )
                page.show_dialog(dlg)
                return
                
            pdf_generator.generar_pdf_ticket_58mm(datos_remision, items_partidas, pdf_path)
            
            dlg = ft.AlertDialog(
                title=ft.Text("Venta Guardada y Ticket Generado"),
                content=ft.Text(f"La venta fue registrada localmente en SQLite (ID: {rem_id}).\n{msg_db}"),
                actions=[
                    ft.TextButton("OK", on_click=lambda ev: page.pop_dialog())
                ]
            )
            page.show_dialog(dlg)
            
            # Limpiar UI
            items_partidas.clear()
            lv_partidas.controls.clear()
            txt_folio.value = datetime.now().strftime('%d%H%M')
            txt_cobro_cliente.value = "CLIENTE MOSTR"
            txt_cobro_condicion.value = "CONTADO"
            txt_cobro_observaciones.value = ""
            calcular_totales()
            
        except Exception as ex:
            page.overlay.append(ft.SnackBar(ft.Text(f"Error al procesar: {str(ex)}"), open=True))
            page.update()

    # Layout de VISTA 1 (Carrito)
    body = ft.Column(
        controls=[
            ft.ResponsiveRow([txt_folio, txt_fecha]),
            ft.Divider(height=1, color=ft.Colors.GREY_300),
            lv_partidas
        ],
        scroll=ft.ScrollMode.AUTO,
        expand=True
    )

    barra_inferior = ft.Container(
        content=ft.Row([
            ft.Text("TOTAL A COBRAR:", size=16, weight=ft.FontWeight.BOLD),
            lbl_total,
            ft.Container(expand=True),
            ft.ElevatedButton("GUARDAR Y COBRAR", icon=ft.Icons.CHECK_CIRCLE, style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN_700, color=ft.Colors.WHITE), on_click=mostrar_modal_cobro, height=50)
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        padding=10,
        bgcolor=ft.Colors.WHITE,
        border=ft.Border(top=ft.BorderSide(1, ft.Colors.GREY_300))
    )

    view_remisiones = ft.Container(
        content=ft.Column([body, barra_inferior]),
        padding=0,
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
                def tap_add_product(e, c=p_cve, d=p_desc, p=p_prec):
                    agregar_partida_directa(c, d, p)
                
                def long_press_product(e, c=p_cve, d=p_desc, p=p_prec):
                    txt_qty_manual = ft.TextField(label="Cantidad", value="1", keyboard_type=ft.KeyboardType.NUMBER, autofocus=True)
                    def add_manual(ev):
                        try:
                            q = float(txt_qty_manual.value)
                            if q > 0:
                                agregar_partida_directa(c, d, p, cantidad_agregar=q)
                            page.pop_dialog()
                        except:
                            pass
                    dlg = ft.AlertDialog(
                        title=ft.Text(f"Cantidad para {d}"),
                        content=txt_qty_manual,
                        actions=[ft.TextButton("Agregar", on_click=add_manual)]
                    )
                    page.show_dialog(dlg)
                
                lv_productos_cat.controls.append(
                    ft.ListTile(
                        leading=ft.Icon(ft.Icons.INVENTORY_2, color=ft.Colors.BLUE_800),
                        title=ft.Text(f"{p_desc} ({p_cve})", weight=ft.FontWeight.BOLD, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                        subtitle=ft.Text(f"Precio: ${p_prec:,.2f} | Stock: {p_exis:.2f}"),
                        on_click=tap_add_product,
                        on_long_press=long_press_product
                    )
                )
        except Exception as ex:
            lv_productos_cat.controls.append(ft.Text(f"Error: {str(ex)}"))
        page.update()

    txt_filtro_prod.on_change = cargar_tabla_productos

    view_productos = ft.Container(
        content=ft.Column([
            ft.Row([txt_filtro_prod, ft.IconButton(icon=ft.Icons.REFRESH, tooltip="Actualizar Lista", on_click=cargar_tabla_productos)]),
            lv_productos_cat
        ]),
        padding=10
    )

    # ══════════════════════════════════════════════════════════════════════
    # VISTA 4: AJUSTES Y CONFIGURACIÓN DE BASE DE DATOS SAE
    # ══════════════════════════════════════════════════════════════════════
    
    txt_cfg_host = ft.TextField(label="Servidor / Host (IP o localhost)", value=cfg_actual.get('host', 'localhost'), col={"md": 8, "xs": 12})
    txt_cfg_database = ft.TextField(label="Ruta Base de Datos Firebird (.FDB)", value=cfg_actual.get('database', ''), col={"md": 12, "xs": 12})
    txt_cfg_empresa = ft.TextField(label="No. Empresa (ej: 01, 07)", value=cfg_actual.get('empresa', '01'), col={"md": 4, "xs": 12})
    txt_cfg_user = ft.TextField(label="Usuario Firebird", value=cfg_actual.get('user', 'SYSDBA'), col={"md": 6, "xs": 12})
    txt_cfg_password = ft.TextField(label="Contraseña", value=cfg_actual.get('password', 'masterkey'), password=True, can_reveal_password=True, col={"md": 6, "xs": 12})
    txt_cfg_vendedor = ft.TextField(label="Vendedor Predeterminado", value=cfg_actual.get('vendedor_predeterminado', ''), col={"md": 6, "xs": 6})
    txt_cfg_almacen = ft.TextField(label="Almacén", value=cfg_actual.get('almacen', '1'), keyboard_type=ft.KeyboardType.NUMBER, col={"md": 6, "xs": 6})
    
    txt_cfg_ticket_empresa = ft.TextField(label="Nombre Empresa (Ticket)", value=cfg_actual.get('ticket_empresa', 'MCR IMPULSO'), col={"md": 6, "xs": 12})
    txt_cfg_ticket_rfc = ft.TextField(label="RFC (Ticket)", value=cfg_actual.get('ticket_rfc', 'RFC: MIM 180215 3ZA'), col={"md": 6, "xs": 12})
    txt_cfg_ticket_dir = ft.TextField(label="Dirección (Ticket)", value=cfg_actual.get('ticket_dir', 'CAMINO A LOS OLVERA NO. 721\nCOL. LOS OLVERA\nEL PUEBLITO, CORREGIDORA'), multiline=True, min_lines=2, col={"md": 12, "xs": 12})
    txt_cfg_ticket_tel = ft.TextField(label="Teléfono (Ticket)", value=cfg_actual.get('ticket_tel', 'TEL: (442) 277 8358'), col={"md": 12, "xs": 12})

    def guardar_config_click(e):
        nuevos_datos = {
            'host': txt_cfg_host.value.strip(),
            'database': txt_cfg_database.value.strip(),
            'empresa': txt_cfg_empresa.value.strip(),
            'user': txt_cfg_user.value.strip(),
            'password': txt_cfg_password.value.strip(),
            'charset': 'UTF8',
            'vendedor_predeterminado': txt_cfg_vendedor.value.strip(),
            'almacen': txt_cfg_almacen.value.strip() or '1',
            'ticket_empresa': txt_cfg_ticket_empresa.value.strip(),
            'ticket_rfc': txt_cfg_ticket_rfc.value.strip(),
            'ticket_dir': txt_cfg_ticket_dir.value.strip(),
            'ticket_tel': txt_cfg_ticket_tel.value.strip()
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
            ft.ResponsiveRow([txt_cfg_vendedor, txt_cfg_almacen]),
            ft.Divider(),
            ft.Text("DATOS DEL TICKET", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_900),
            ft.ResponsiveRow([txt_cfg_ticket_empresa, txt_cfg_ticket_rfc]),
            ft.ResponsiveRow([txt_cfg_ticket_dir]),
            ft.ResponsiveRow([txt_cfg_ticket_tel]),
            ft.Divider(),
            ft.ResponsiveRow([
                ft.Column(col={"xs": 12, "sm": 6}, controls=[ft.ElevatedButton("Probar Conexión", icon=ft.Icons.NETWORK_CHECK, on_click=probar_conexion_click, width=250)]),
                ft.Column(col={"xs": 12, "sm": 6}, controls=[ft.ElevatedButton("Guardar Configuración", icon=ft.Icons.SAVE, style=ft.ButtonStyle(color=ft.Colors.WHITE, bgcolor=ft.Colors.GREEN_700), on_click=guardar_config_click, width=250)])
            ]),
            ft.Divider(),
            ft.Text("MANTENIMIENTO", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_900),
            ft.Text("Para traer los productos y clientes de la base de datos SAE a esta terminal táctil, haga clic en Sincronizar."),
            btn_sync_sae
        ], scroll=ft.ScrollMode.AUTO),
        padding=10,
        expand=True
    )

    # ══════════════════════════════════════════════════════════════════════
    # VISTA 5: HISTORIAL Y SINCRONIZACIÓN
    # ══════════════════════════════════════════════════════════════════════
    lv_historial = ft.ListView(expand=True, spacing=5, height=450)
    
    def cargar_historial():
        lv_historial.controls.clear()
        ventas = db_local.obtener_ventas_historial()
        
        def mostrar_detalles_venta(e):
            rem_id = e.control.data
            encabezado, partidas = db_local.obtener_venta_completa(rem_id)
            if not encabezado: return
            
            folio = encabezado.get('folio', '')
            pdf_path = os.path.join(os.path.dirname(__file__), f"TKT-{folio}.pdf")
            def abrir_pdf(ev):
                if os.path.exists(pdf_path):
                    if hasattr(os, 'startfile'):
                        os.startfile(pdf_path)
                    else:
                        page.launch_url(f"file://{pdf_path}")
                else:
                    page.overlay.append(ft.SnackBar(ft.Text("PDF no encontrado"), open=True))
                    page.update()

            def cerrar_modal(ev):
                page.pop_dialog()

            # --- PRODUCTOS LIST ---
            lista_partidas = ft.Column(spacing=0)
            lista_partidas.controls.append(
                ft.Row([
                    ft.Text("Cantidad", size=12, color=ft.Colors.GREY_700, expand=1, text_align=ft.TextAlign.CENTER),
                    ft.Text("Precio $", size=12, color=ft.Colors.GREY_700, expand=1, text_align=ft.TextAlign.CENTER),
                    ft.Text("Subtotal $", size=12, color=ft.Colors.GREY_700, expand=1, text_align=ft.TextAlign.CENTER),
                ])
            )
            for i, p in enumerate(partidas):
                bg = ft.Colors.TRANSPARENT if i % 2 == 0 else ft.Colors.GREY_200
                lista_partidas.controls.append(
                    ft.Container(
                        bgcolor=bg,
                        padding=8,
                        content=ft.Column([
                            ft.Row([
                                ft.Icon(ft.Icons.INVENTORY_2, size=16, color=ft.Colors.GREY_700),
                                ft.Text(f"{p['descripcion']}", size=13, weight=ft.FontWeight.W_500, expand=True)
                            ]),
                            ft.Row([
                                ft.Text(f"{p['cantidad']:.0f}", size=13, expand=1, text_align=ft.TextAlign.CENTER),
                                ft.Text(f"{p['precio_unitario']:,.0f}", size=13, expand=1, text_align=ft.TextAlign.CENTER),
                                ft.Text(f"{p['total_partida']:,.0f}", size=13, expand=1, text_align=ft.TextAlign.CENTER),
                            ])
                        ], spacing=2)
                    )
                )

            # --- UI CONTENT ---
            cliente_nombre = encabezado.get('nombre_cliente') or "Sin información"
            cliente_dir = encabezado.get('direccion_cliente') or "Sin información"
            info_adic = encabezado.get('observaciones') or "Sin información"
            metodo_pago = encabezado.get('condicion') or "EFECTIVO"
            total_val = encabezado.get('total', 0)

            content_col = ft.Column([
                # Top bar (Blue)
                ft.Container(
                    bgcolor=ft.Colors.LIGHT_BLUE_500,
                    padding=10,
                    content=ft.Row([
                        ft.IconButton(ft.Icons.CLOSE, icon_color=ft.Colors.WHITE, on_click=cerrar_modal),
                        ft.Text("Venta", color=ft.Colors.WHITE, size=20, weight=ft.FontWeight.W_500, expand=True),
                        ft.IconButton(ft.Icons.PICTURE_AS_PDF, icon_color=ft.Colors.WHITE, on_click=abrir_pdf)
                    ])
                ),
                # Body
                ft.Container(
                    padding=20,
                    content=ft.Column([
                        ft.Text("Pagado", color=ft.Colors.GREEN_600, size=18, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
                        ft.Divider(color=ft.Colors.TRANSPARENT, height=5),
                        ft.Text(f"Folio: {folio}", size=14, color=ft.Colors.GREY_800),
                        ft.Row([ft.Icon(ft.Icons.CALENDAR_MONTH, size=18, color=ft.Colors.BLACK87), ft.Text(encabezado.get('fecha', ''), size=14, color=ft.Colors.GREY_800)]),
                        ft.Divider(),
                        
                        ft.Text("Nombre del cliente", size=12, color=ft.Colors.GREY_600),
                        ft.Row([ft.Icon(ft.Icons.PERSON, size=18, color=ft.Colors.BLACK87), ft.Text(cliente_nombre, size=14, color=ft.Colors.GREY_800)]),
                        ft.Text("Dirección", size=12, color=ft.Colors.GREY_600),
                        ft.Row([ft.Icon(ft.Icons.LOCATION_ON, size=18, color=ft.Colors.BLACK87), ft.Text(cliente_dir, size=14, color=ft.Colors.GREY_800)]),
                        ft.Divider(),
                        
                        ft.Text("Información Adicional", size=12, color=ft.Colors.GREY_600),
                        ft.Row([ft.Icon(ft.Icons.INFO_OUTLINE, size=18, color=ft.Colors.BLACK87), ft.Text(info_adic, size=14, color=ft.Colors.GREY_800)]),
                        ft.Row([ft.Icon(ft.Icons.MONEY, size=18, color=ft.Colors.BLACK87), ft.Text(metodo_pago, size=14, color=ft.Colors.GREY_800)], alignment=ft.MainAxisAlignment.END),
                        
                        # Total Box
                        ft.Container(
                            bgcolor=ft.Colors.WHITE,
                            border=ft.border.all(1, ft.Colors.GREY_300),
                            border_radius=10,
                            padding=15,
                            margin=15,
                            content=ft.Row([
                                ft.Text("Total $", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.GREY_700),
                                ft.Text(f"{total_val:,.0f}", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.GREY_800)
                            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                        ),
                        
                        # Products list section
                        ft.Text("Lista de productos y servicios", size=14, color=ft.Colors.GREY_700, text_align=ft.TextAlign.CENTER),
                        lista_partidas
                    ], spacing=8, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
                )
            ], spacing=0, scroll=ft.ScrollMode.AUTO)

            dlg = ft.AlertDialog(
                content_padding=0,
                content=ft.Container(width=400, height=600, content=content_col)
            )
            page.show_dialog(dlg)

        for v in ventas:
            color_estatus = ft.Colors.ORANGE_800 if v['estatus_sync'] == 'PENDIENTE' else ft.Colors.GREEN_700
            icono_estatus = ft.Icons.PENDING if v['estatus_sync'] == 'PENDIENTE' else ft.Icons.CLOUD_DONE
            
            lv_historial.controls.append(
                ft.ListTile(
                    leading=ft.Icon(icono_estatus, color=color_estatus),
                    title=ft.Text(f"{v['folio']} - {v['fecha']}", weight=ft.FontWeight.BOLD),
                    subtitle=ft.Text(f"Cliente: {v['nombre_cliente']} | Total: ${v['total']:,.2f}"),
                    trailing=ft.Text(v['estatus_sync'], color=color_estatus, weight=ft.FontWeight.W_500),
                    data=v['id'],
                    on_click=mostrar_detalles_venta
                )
            )
        if not ventas:
            lv_historial.controls.append(ft.Text("No hay ventas registradas en esta terminal.", italic=True))
        page.update()

    def btn_sincronizar_ventas_click(e):
        btn_sincronizar_ventas.disabled = True
        btn_sincronizar_ventas.text = "Sincronizando..."
        page.update()
        
        ok, msg = sae_connector.subir_ventas_pendientes()
        
        btn_sincronizar_ventas.disabled = False
        btn_sincronizar_ventas.text = "Subir Ventas Pendientes a SAE"
        cargar_historial()
        
        icon_t = ft.Icons.CHECK_CIRCLE if ok else ft.Icons.ERROR
        color_t = ft.Colors.GREEN if ok else ft.Colors.RED
        dlg = ft.AlertDialog(
            title=ft.Row([ft.Icon(icon_t, color=color_t), ft.Text("Sincronización de Ventas")]),
            content=ft.Text(msg),
            actions=[ft.TextButton("Aceptar", on_click=lambda ev: page.pop_dialog())]
        )
        page.show_dialog(dlg)

    def btn_exportar_csv_click(e):
        import csv
        ventas = db_local.obtener_ventas_historial()
        fecha_filtro = txt_fecha_csv.value.strip()
        
        out_csv = os.path.join(os.path.dirname(__file__), f"ventas_exportadas_{fecha_filtro.replace('/','-')}.csv")
        try:
            with open(out_csv, mode='w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['CVE_DOC', 'CVE_ART', 'DESCR', 'UNIDAD', 'PRECIO VENTA'])
                for v in ventas:
                    # El historial trae la fecha de creación 'fecha'
                    if fecha_filtro and v['fecha'] != fecha_filtro:
                        continue
                        
                    encabezado, partidas = db_local.obtener_venta_completa(v['id'])
                    if encabezado and partidas:
                        for p in partidas:
                            cve_doc = str(encabezado.get('folio', ''))
                            cve_art = str(p.get('cve_producto', ''))
                            writer.writerow([
                                f'="{cve_doc}"' if cve_doc else '',
                                f'="{cve_art}"' if cve_art else '',
                                p.get('descripcion', ''),
                                p.get('cantidad', 0),
                                p.get('precio_unitario', 0)
                            ])
            page.overlay.append(ft.SnackBar(ft.Text(f"Exportado a {out_csv}"), open=True))
            if hasattr(os, 'startfile'):
                os.startfile(out_csv)
            else:
                page.launch_url(f"file://{out_csv}")
        except Exception as ex:
            page.overlay.append(ft.SnackBar(ft.Text(f"Error al exportar: {ex}"), open=True))
        page.update()

    btn_sincronizar_ventas = ft.ElevatedButton(
        "Subir Ventas Pendientes a SAE", 
        icon=ft.Icons.CLOUD_UPLOAD, 
        style=ft.ButtonStyle(bgcolor=ft.Colors.BLUE_800, color=ft.Colors.WHITE),
        on_click=btn_sincronizar_ventas_click
    )
    
    txt_fecha_csv = ft.TextField(label="Fecha (DD/MM/YYYY)", value=datetime.now().strftime("%d/%m/%Y"), width=180, dense=True)
    btn_exportar_csv = ft.ElevatedButton("Exportar CSV", icon=ft.Icons.DOWNLOAD, on_click=btn_exportar_csv_click, bgcolor=ft.Colors.GREEN_700, color=ft.Colors.WHITE)

    view_historial = ft.Container(
        content=ft.Column([
            ft.ResponsiveRow([
                ft.Column(col={"xs": 12, "sm": 6}, controls=[ft.Text("HISTORIAL DE VENTAS", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_900)]),
                ft.Column(col={"xs": 12, "sm": 6}, controls=[btn_sincronizar_ventas])
            ]),
            ft.Divider(),
            ft.Row([txt_fecha_csv, btn_exportar_csv], alignment=ft.MainAxisAlignment.START, wrap=True),
            ft.Divider(),
            lv_historial
        ]),
        padding=10,
        expand=True
    )

    # ══════════════════════════════════════════════════════════════════════
    # BARRA DE NAVEGACIÓN MÓVIL (TABS / PESTAÑAS)
    # ══════════════════════════════════════════════════════════════════════
    body_container = ft.Container(content=view_productos, expand=True)
    
    # Cargar por defecto el catálogo
    cargar_tabla_productos()

    def cambiar_pestana(e):
        idx = e.control.selected_index
        if idx == 0:
            body_container.content = view_productos
            cargar_tabla_productos()
        elif idx == 1:
            body_container.content = view_remisiones
        elif idx == 2:
            body_container.content = view_clientes
            cargar_tabla_clientes()
        elif idx == 3:
            body_container.content = view_ajustes
        elif idx == 4:
            body_container.content = view_historial
            cargar_historial()
        page.update()

    page.navigation_bar = ft.NavigationBar(
        destinations=[
            ft.NavigationBarDestination(icon=ft.Icons.SEARCH, label="Catálogo"),
            ft.NavigationBarDestination(icon=ft.Icons.SHOPPING_CART, label="Carrito"),
            ft.NavigationBarDestination(icon=ft.Icons.PEOPLE, label="Clientes"),
            ft.NavigationBarDestination(icon=ft.Icons.SETTINGS, label="Ajustes"),
            ft.NavigationBarDestination(icon=ft.Icons.HISTORY, label="Historial"),
        ],
        selected_index=0,
        on_change=cambiar_pestana
    )

    page.add(body_container)

if __name__ == "__main__":
    ft.run(main)
