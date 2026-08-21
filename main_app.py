import flet as ft
import os
from datetime import datetime
import db_local
import pdf_generator
import search_dialogs

def main(page: ft.Page):
    page.title = "MCR IMPULSO - Control de Remisiones Móviles"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 15
    page.scroll = ft.ScrollMode.AUTO
    
    # Inicializar BD local
    db_local.init_db()

    # Variables de Estado de la Remisión
    items_partidas = []
    
    # Campos de Entrada
    txt_folio = ft.TextField(label="Folio Remisión", value=f"REM-{datetime.now().strftime('%d%H%M')}", width=180, read_only=True)
    txt_fecha = ft.TextField(label="Fecha", value=datetime.now().strftime("%d/%m/%Y"), width=150)
    txt_cliente = ft.TextField(label="Cliente", hint_text="Nombre del Cliente o Clínica", expand=True)
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

    # Checkboxes Especialidades
    chk_electrofisiologia = ft.Checkbox(label="Electrofisiología y Mapeo", value=False)
    chk_radiologia = ft.Checkbox(label="Radiología Intervencionista", value=False)
    chk_cardiologia = ft.Checkbox(label="Cardiología Intervencionista", value=False)
    chk_endovascular = ft.Checkbox(label="Endovascular Periférico", value=False)
    chk_neuromodulacion = ft.Checkbox(label="Neuromodulación", value=False)

    # Campos Expediente Médicos
    txt_paciente = ft.TextField(label="Nombre del Paciente", expand=True)
    txt_doctor = ft.TextField(label="Nombre del Doctor", expand=True)
    txt_episodio = ft.TextField(label="Episodio", width=180)
    txt_aseguradora = ft.TextField(label="Aseguradora", width=220)
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

    # Tabla de Partidas Táctil
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
            page.show_snack_bar(ft.SnackBar(ft.Text("Escriba la descripción del producto")))
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
            
            # Limpiar entradas de partida
            txt_part_cant.value = "1"
            txt_part_cve.value = ""
            txt_part_alg.value = ""
            txt_part_descr.value = ""
            txt_part_lote.value = ""
            txt_part_precio.value = "0.00"
            
            # Renderizar fila en DataTable
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
            page.show_snack_bar(ft.SnackBar(ft.Text("Valores numéricos inválidos en cantidad o precio")))

    def guardar_y_generar_pdf(e):
        if not txt_cliente.value:
            page.show_snack_bar(ft.SnackBar(ft.Text("Por favor ingrese el nombre del Cliente")))
            return
        if not items_partidas:
            page.show_snack_bar(ft.SnackBar(ft.Text("Debe agregar al menos una partida a la remisión")))
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

        # Guardar PDF en carpeta de salida
        out_dir = os.path.dirname(__file__)
        pdf_path = os.path.join(out_dir, f"{txt_folio.value}.pdf")
        
        try:
            pdf_generator.generar_pdf_remision(datos_remision, items_partidas, pdf_path)
            page.dialog = ft.AlertDialog(
                title=ft.Text("Remisión Generada"),
                content=ft.Text(f"Se ha guardado y generado el PDF exitosamente:\n{pdf_path}"),
                actions=[ft.TextButton("OK", on_click=lambda e: page.close_dialog())]
            )
            page.dialog.open = True
            page.update()
        except Exception as ex:
            page.show_snack_bar(ft.SnackBar(ft.Text(f"Error al generar el PDF: {str(ex)}")))

    # UI LAYOUT
    page.add(
        ft.Container(
            content=ft.Column([
                # ENCABEZADO
                ft.Row([
                    ft.Text("MCR IMPULSO - REMISIÓN MÓVIL", size=22, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_900),
                    txt_folio,
                    txt_fecha
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Divider(),
                
                # DATOS CLIENTE
                ft.Row([txt_cliente, btn_buscar_cliente, txt_vendedor]),
                txt_direccion,
                ft.Divider(),
                
                # ESPECIALIDADES CHECKBOXES
                ft.Text("Especialidades Médico-Quirúrgicas:", weight=ft.FontWeight.BOLD),
                ft.Row([
                    chk_electrofisiologia,
                    chk_radiologia,
                    chk_cardiologia,
                    chk_endovascular,
                    chk_neuromodulacion
                ], wrap=True),
                ft.Divider(),

                # EXPEDIENTE MÉDICO
                ft.Text("Datos de Expediente y Paciente:", weight=ft.FontWeight.BOLD),
                ft.Row([txt_paciente, txt_doctor]),
                ft.Row([txt_episodio, txt_aseguradora, txt_diagnostico]),
                ft.Divider(),

                # CAPTURA DE PARTIDA
                ft.Text("Agregar Producto / Partida:", weight=ft.FontWeight.BOLD),
                ft.Row([
                    txt_part_cant,
                    txt_part_cve,
                    btn_buscar_producto,
                    txt_part_alg,
                    txt_part_descr,
                    txt_part_lote,
                    txt_part_precio,
                    ft.ElevatedButton("Agregar", icon=ft.Icons.ADD if hasattr(ft, "Icons") else None, on_click=agregar_partida_click)
                ]),
                
                # TABLA DE PARTIDAS
                dt_partidas,
                ft.Divider(),

                # RESUMEN TOTALES Y BOTÓN GENERAR
                ft.Row([
                    ft.Column([
                        ft.Row([ft.Text("Subtotal: "), lbl_subtotal]),
                        ft.Row([ft.Text("IVA (16%): "), lbl_iva]),
                        ft.Row([ft.Text("TOTAL: "), lbl_total]),
                    ]),
                    ft.ElevatedButton(
                        "GUARDAR Y GENERAR PDF",
                        icon=ft.Icons.PICTURE_AS_PDF if hasattr(ft, "Icons") else None,
                        style=ft.ButtonStyle(color=ft.Colors.WHITE, bgcolor=ft.Colors.GREEN_700),
                        height=50,
                        on_click=guardar_y_generar_pdf
                    )
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
            ]),
            padding=10
        )
    )

if __name__ == "__main__":
    ft.app(target=main)
