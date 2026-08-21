import flet as ft
import sqlite3
import os

def search_clients_dialog(page: ft.Page, on_select_callback):
    """
    Diálogo táctil emergente de búsqueda de Clientes (Réplica de client_search.py de PuntoVentaPro).
    Busca por CLAVE o NOMBRE en SQLite local.
    """
    db_path = os.path.join(os.path.dirname(__file__), "remisiones_local.db")

    txt_busqueda = ft.TextField(
        label="Buscar Cliente",
        hint_text="Escriba Clave o Nombre...",
        autofocus=True,
        expand=True
    )
    
    lv_resultados = ft.ListView(expand=True, spacing=5, height=300)

    def realizar_busqueda(e=None):
        filtro = (txt_busqueda.value or "").strip()
        lv_resultados.controls.clear()
        
        try:
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            if filtro:
                cur.execute("""
                    SELECT clave, nombre, rfc, direccion 
                    FROM clientes 
                    WHERE clave LIKE ? OR UPPER(nombre) LIKE UPPER(?) 
                    LIMIT 30
                """, (f"%{filtro}%", f"%{filtro}%"))
            else:
                cur.execute("SELECT clave, nombre, rfc, direccion FROM clientes LIMIT 30")
            
            rows = cur.fetchall()
            conn.close()

            if not rows:
                lv_resultados.controls.append(
                    ft.ListTile(title=ft.Text("No se encontraron clientes coincidentes"))
                )
            else:
                for r in rows:
                    clave, nombre, rfc, direccion = r[0], r[1], r[2] or '', r[3] or ''
                    
                    def seleccionar(e, c=clave, n=nombre, d=direccion):
                        on_select_callback(c, n, d)
                        dlg.open = False
                        page.update()

                    lv_resultados.controls.append(
                        ft.ListTile(
                            leading=ft.Icon(ft.Icons.PERSON),
                            title=ft.Text(f"{nombre} ({clave})"),
                            subtitle=ft.Text(f"RFC: {rfc} | Dir: {direccion}"),
                            on_click=seleccionar
                        )
                    )
        except Exception as ex:
            lv_resultados.controls.append(ft.Text(f"Error al buscar: {str(ex)}"))
        
        page.update()

    txt_busqueda.on_change = realizar_busqueda

    dlg = ft.AlertDialog(
        title=ft.Text("Buscador de Clientes (SAE)"),
        content=ft.Container(
            content=ft.Column([
                txt_busqueda,
                ft.Divider(),
                lv_resultados
            ]),
            width=500,
            height=400
        ),
        actions=[
            ft.TextButton("Cancelar", on_click=lambda e: setattr(dlg, "open", False) or page.update())
        ]
    )

    page.dialog = dlg
    dlg.open = True
    realizar_busqueda()
    page.update()

def search_products_dialog(page: ft.Page, on_select_callback):
    """
    Diálogo táctil emergente de búsqueda de Productos (Réplica de product_search.py de PuntoVentaPro).
    Busca por CLAVE o DESCRIPCIÓN en SQLite local.
    """
    db_path = os.path.join(os.path.dirname(__file__), "remisiones_local.db")

    txt_busqueda = ft.TextField(
        label="Buscar Producto / Insumo",
        hint_text="Escriba Clave o Descripción...",
        autofocus=True,
        expand=True
    )
    
    lv_resultados = ft.ListView(expand=True, spacing=5, height=300)

    def realizar_busqueda(e=None):
        filtro = (txt_busqueda.value or "").strip()
        lv_resultados.controls.clear()
        
        try:
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            if filtro:
                cur.execute("""
                    SELECT clave, descripcion, precio, existencia 
                    FROM productos 
                    WHERE clave LIKE ? OR UPPER(descripcion) LIKE UPPER(?) 
                    LIMIT 30
                """, (f"%{filtro}%", f"%{filtro}%"))
            else:
                cur.execute("SELECT clave, descripcion, precio, existencia FROM productos LIMIT 30")
            
            rows = cur.fetchall()
            conn.close()

            if not rows:
                lv_resultados.controls.append(
                    ft.ListTile(title=ft.Text("No se encontraron productos coincidentes"))
                )
            else:
                for r in rows:
                    clave, descr, precio, exist = r[0], r[1], float(r[2] or 0), float(r[3] or 0)
                    
                    def seleccionar(e, c=clave, d=descr, p=precio):
                        on_select_callback(c, d, p)
                        dlg.open = False
                        page.update()

                    lv_resultados.controls.append(
                        ft.ListTile(
                            leading=ft.Icon(ft.Icons.INVENTORY_2),
                            title=ft.Text(f"{descr} ({clave})"),
                            subtitle=ft.Text(f"Precio U: ${precio:,.2f} | Stock: {exist:.2f}"),
                            on_click=seleccionar
                        )
                    )
        except Exception as ex:
            lv_resultados.controls.append(ft.Text(f"Error al buscar: {str(ex)}"))
        
        page.update()

    txt_busqueda.on_change = realizar_busqueda

    dlg = ft.AlertDialog(
        title=ft.Text("Buscador de Productos (SAE)"),
        content=ft.Container(
            content=ft.Column([
                txt_busqueda,
                ft.Divider(),
                lv_resultados
            ]),
            width=550,
            height=400
        ),
        actions=[
            ft.TextButton("Cancelar", on_click=lambda e: setattr(dlg, "open", False) or page.update())
        ]
    )

    page.dialog = dlg
    dlg.open = True
    realizar_busqueda()
    page.update()
