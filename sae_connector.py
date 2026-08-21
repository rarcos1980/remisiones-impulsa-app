import firebirdsql
import sqlite3
import os
import logging

logger = logging.getLogger(__name__)

# Configuración por defecto BD Firebird (SAE 9 Empresa01 local o IP)
DB_CONFIG = {
    'host': 'localhost',
    'database': r'C:\Program Files (x86)\Common Files\Aspel\Sistemas Aspel\SAE9.00\Empresa01\Datos\SAE90EMPRE01.FDB',
    'user': 'SYSDBA',
    'password': 'masterkey',
    'charset': 'UTF8'
}

DB_LOCAL_PATH = os.path.join(os.path.dirname(__file__), "remisiones_local.db")

def sync_catalogos_desde_sae():
    """
    Sincroniza directamente los catálogos de Clientes, Productos y Vendedores
    desde la base de datos de Aspel SAE (Firebird) hacia la SQLite local de la app.
    """
    try:
        fb_conn = firebirdsql.connect(**DB_CONFIG)
        cur_fb = fb_conn.cursor()

        sqlite_conn = sqlite3.connect(DB_LOCAL_PATH)
        cur_sq = sqlite_conn.cursor()

        # 1. Sync Clientes (CLIE01)
        cur_fb.execute("SELECT TRIM(CLAVE), TRIM(NOMBRE), TRIM(RFC), TRIM(CALLE) FROM CLIE01 WHERE STATUS = 'A'")
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

        # 2. Sync Productos (INVE01)
        cur_fb.execute("SELECT TRIM(CVE_ART), TRIM(DESCR), EXIST FROM INVE01 WHERE STATUS = 'A'")
        productos_fb = cur_fb.fetchall()
        for p in productos_fb:
            clave, descr, exist = p[0], p[1], float(p[2] or 0.0)
            precio = 0.0
            cur_sq.execute("""
                INSERT INTO productos (clave, descripcion, precio, existencia)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(clave) DO UPDATE SET
                    descripcion=excluded.descripcion,
                    precio=excluded.precio,
                    existencia=excluded.existencia
            """, (clave, descr, precio, exist))

        # 3. Sync Vendedores (VEND01)
        cur_fb.execute("SELECT TRIM(CVE_VEND), TRIM(NOMBRE) FROM VEND01 WHERE STATUS = 'A'")
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
        print(f"Sincronización exitosa: {len(clientes_fb)} clientes, {len(productos_fb)} productos, {len(vendedores_fb)} vendedores desde SAE.")
        return True, f"Catálogos actualizados desde SAE ({len(productos_fb)} productos, {len(clientes_fb)} clientes)."
    except Exception as e:
        msg = f"Error al conectar con SAE Firebird: {str(e)}"
        print(msg)
        return False, msg

if __name__ == "__main__":
    sync_catalogos_desde_sae()
