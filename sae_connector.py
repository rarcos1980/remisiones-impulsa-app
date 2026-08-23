import json
import os
import firebirdsql
import sqlite3

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config_sae.json")

DEFAULT_CONFIG = {
    'host': 'localhost',
    'database': r'C:\Program Files (x86)\Common Files\Aspel\Sistemas Aspel\SAE9.00\Empresa01\Datos\SAE90EMPRE01.FDB',
    'user': 'SYSDBA',
    'password': 'masterkey',
    'charset': 'UTF8',
    'empresa': '01',
    'vendedor_predeterminado': ''
}

def load_config():
    """Carga la configuración de conexión a SAE desde JSON o genera la por defecto."""
    if not os.path.exists(CONFIG_FILE):
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
            return cfg
    except Exception:
        return DEFAULT_CONFIG

def save_config(cfg_dict):
    """Guarda la configuración de conexión a SAE en JSON."""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(cfg_dict, f, indent=4)
        return True, "Configuración guardada correctamente."
    except Exception as e:
        return False, f"Error al guardar configuración: {str(e)}"

DB_LOCAL_PATH = os.path.join(os.path.dirname(__file__), "remisiones_local.db")

def test_connection():
    """Prueba la conexión directa con la base de datos Firebird de SAE."""
    cfg = load_config()
    try:
        conn = firebirdsql.connect(
            host=cfg.get('host', 'localhost'),
            database=cfg.get('database', ''),
            user=cfg.get('user', 'SYSDBA'),
            password=cfg.get('password', 'masterkey'),
            charset=cfg.get('charset', 'UTF8')
        )
        conn.close()
        return True, "Conexión exitosa con la base de datos de Aspel SAE."
    except Exception as e:
        return False, f"Error al conectar a SAE: {str(e)}"

def sync_catalogos_desde_sae():
    """Sincroniza los catálogos de Clientes, Productos y Vendedores de SAE hacia SQLite local."""
    cfg = load_config()
    emp = cfg.get('empresa', '01').zfill(2)
    
    tbl_clie = f"CLIE{emp}"
    tbl_inve = f"INVE{emp}"
    tbl_vend = f"VEND{emp}"

    try:
        fb_conn = firebirdsql.connect(
            host=cfg.get('host', 'localhost'),
            database=cfg.get('database', ''),
            user=cfg.get('user', 'SYSDBA'),
            password=cfg.get('password', 'masterkey'),
            charset=cfg.get('charset', 'UTF8')
        )
        cur_fb = fb_conn.cursor()

        sqlite_conn = sqlite3.connect(DB_LOCAL_PATH)
        cur_sq = sqlite_conn.cursor()

        # 1. Sync Clientes
        cur_fb.execute(f"SELECT TRIM(CLAVE), TRIM(NOMBRE), TRIM(RFC), TRIM(CALLE) FROM {tbl_clie} WHERE STATUS = 'A'")
        clientes_fb = cur_fb.fetchall()
        for c in clientes_fb:
            clave, nombre, rfc, direccion = c[0], c[1], c[2] or '', c[3] or ''
            cur_sq.execute("""
                INSERT INTO clientes (clave, nombre, rfc, direccion)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(clave) DO UPDATE SET
                    nombre=excluded.nombre,
                    rfc=excluded.rfc,
                    direccion=excluded.direccion
            """, (clave, nombre, rfc, direccion))

        # 2. Sync Productos e Importar Precios
        cur_fb.execute(f"SELECT TRIM(CVE_ART), TRIM(DESCR), EXIST FROM {tbl_inve} WHERE STATUS = 'A'")
        productos_fb = cur_fb.fetchall()
        for p in productos_fb:
            clave, descr, exist = p[0], p[1], float(p[2] or 0.0)
            precio = 0.0
            cur_sq.execute("""
                INSERT INTO productos (clave, descripcion, precio, existencia)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(clave) DO UPDATE SET
                    descripcion=excluded.descripcion,
                    existencia=excluded.existencia
            """, (clave, descr, precio, exist))

        # 2.1 Sync Lista de Precios (PRECIO_X_PROD)
        tbl_precio = f"PRECIO_X_PROD{emp}"
        try:
            cur_fb.execute(f"SELECT TRIM(CVE_ART), CVE_PRECIO, PRECIO FROM {tbl_precio}")
            precios_fb = cur_fb.fetchall()
            for px in precios_fb:
                cve_art, cve_precio, precio_val = px[0], int(px[1] or 1), float(px[2] or 0.0)
                cur_sq.execute("""
                    INSERT INTO precios_x_producto (cve_art, cve_precio, precio)
                    VALUES (?, ?, ?)
                    ON CONFLICT(cve_art, cve_precio) DO UPDATE SET precio=excluded.precio
                """, (cve_art, cve_precio, precio_val))
                
                # Actualizar precio lista 1 en tabla de productos principal
                if cve_precio == 1:
                    cur_sq.execute("UPDATE productos SET precio = ? WHERE clave = ?", (precio_val, cve_art))
        except Exception as ex_p:
            print(f"Nota: No se pudo leer {tbl_precio}: {str(ex_p)}")

        # 3. Sync Vendedores
        cur_fb.execute(f"SELECT TRIM(CVE_VEND), TRIM(NOMBRE) FROM {tbl_vend} WHERE STATUS = 'A'")
        vendedores_fb = cur_fb.fetchall()
        for v in vendedores_fb:
            clave, nombre = v[0], v[1]
            cur_sq.execute("""
                INSERT INTO vendedores (clave, nombre)
                VALUES (?, ?)
                ON CONFLICT(clave) DO UPDATE SET nombre=excluded.nombre
            """, (clave, nombre))

        sqlite_conn.commit()
        fb_conn.close()
        sqlite_conn.close()
        return True, f"Catálogos de Empresa {emp} actualizados desde SAE ({len(productos_fb)} productos, {len(clientes_fb)} clientes, {len(vendedores_fb)} vendedores)."
    except Exception as e:
        msg = f"Error al conectar con SAE Firebird ({tbl_inve}): {str(e)}"
        return False, msg

def subir_ventas_pendientes():
    """Sincroniza las ventas locales con estatus PENDIENTE hacia la BD de SAE."""
    import db_local
    ventas = db_local.obtener_ventas_historial()
    pendientes = [v for v in ventas if v.get('estatus_sync') == 'PENDIENTE']
    
    if not pendientes:
        return True, "No hay ventas pendientes por sincronizar."

    cfg = load_config()
    try:
        fb_conn = firebirdsql.connect(
            host=cfg.get('host', 'localhost'),
            database=cfg.get('database', ''),
            user=cfg.get('user', 'SYSDBA'),
            password=cfg.get('password', 'masterkey'),
            charset=cfg.get('charset', 'UTF8')
        )
    except Exception as e:
        return False, f"Error conectando a SAE para subir ventas: {str(e)}"
    
    cur_fb = fb_conn.cursor()
    exitos = 0
    errores = []

    for v in pendientes:
        rem_id = v['id']
        encabezado, partidas = db_local.obtener_venta_completa(rem_id)
        if not encabezado or not partidas:
            errores.append(f"Venta {rem_id} sin datos completos.")
            continue
            
        folio = encabezado.get('folio', f"RM-{rem_id}")
        cve_cliente = encabezado.get('cve_cliente', '')
        cve_vendedor = encabezado.get('cve_vendedor', '')
        total = encabezado.get('total', 0.0)
        
        # En SAE, las remisiones se guardan en FACTRXX con TIP_DOC = 'R'
        # o 'V' para Notas de Venta, o 'C' para cotizaciones, dependiendo del tipo.
        # Aquí asumiremos TIP_DOC = 'V' por ser Notas de Venta.
        tip_doc = folio[0] if folio and folio[0] in ['V', 'C'] else 'V'

        try:
            cur_fb.execute("""
                INSERT INTO FACTR01 (TIP_DOC, CVE_DOC, CVE_CLPV, STATUS, DAT_MOSTR, CVE_VEND, CAN_TOT, IMP_TOT1, FECHA_DOCU)
                VALUES (?, ?, ?, 'E', 0, ?, ?, 0, CURRENT_DATE)
            """, (tip_doc, folio, cve_cliente, cve_vendedor, total))
            
            for p in partidas:
                cur_fb.execute("""
                    INSERT INTO PAR_FACTR01 (CVE_DOC, NUM_PAR, CVE_ART, CANT, PREC, TOT_PARTIDA)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (folio, p.get('num_partida', 1), p.get('cve_producto', ''), p.get('cantidad', 1.0), p.get('precio_unitario', 0.0), p.get('total_partida', 0.0)))
            
            fb_conn.commit()
            db_local.marcar_venta_sincronizada(rem_id)
            exitos += 1
        except Exception as ex_v:
            fb_conn.rollback()
            errores.append(f"Error en folio {folio}: {str(ex_v)}")

    fb_conn.close()
    
    if errores:
        return False, f"Se sincronizaron {exitos} ventas. Hubo errores:\n" + "\n".join(errores)
    return True, f"Se sincronizaron {exitos} ventas correctamente."
