from fastapi import FastAPI, HTTPException
import firebirdsql
import sqlite3
import os

app = FastAPI(title="API Sincronizador SAE - Remisiones Móviles")

# Configuración BD Firebird (SAE)
DB_CONFIG = {
    'host': 'localhost',
    'database': r'C:\Program Files (x86)\Common Files\Aspel\Sistemas Aspel\SAE9.00\Empresa01\Datos\SAE90EMPRE01.FDB',
    'user': 'SYSDBA',
    'password': 'masterkey',
    'charset': 'NONE'
}

def get_fb_connection():
    try:
        conn = firebirdsql.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error conectando a Firebird SAE: {str(e)}")

@app.get("/sync/clientes")
def obtener_clientes():
    """Obtiene catálogo activo de clientes desde SAE (CLIE01)."""
    conn = get_fb_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT TRIM(CLAVE), TRIM(NOMBRE), TRIM(RFC), TRIM(CALLE) FROM CLIE01 WHERE STATUS = 'A'")
        rows = cur.fetchall()
        clientes = [
            {'clave': r[0], 'nombre': r[1], 'rfc': r[2] or '', 'direccion': r[3] or ''}
            for r in rows
        ]
        return {"total": len(clientes), "clientes": clientes}
    finally:
        conn.close()

@app.get("/sync/productos")
def obtener_productos():
    """Obtiene catálogo activo de productos desde SAE (INVE01)."""
    conn = get_fb_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT TRIM(CVE_ART), TRIM(DESCR), PRECIO1, EXIST FROM INVE01 WHERE STATUS = 'A'")
        rows = cur.fetchall()
        productos = [
            {'clave': r[0], 'descripcion': r[1], 'precio': float(r[2] or 0.0), 'existencia': float(r[3] or 0.0)}
            for r in rows
        ]
        return {"total": len(productos), "productos": productos}
    finally:
        conn.close()

@app.get("/sync/vendedores")
def obtener_vendedores():
    """Obtiene catálogo de vendedores desde SAE (VEND01)."""
    conn = get_fb_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT TRIM(CVE_VEND), TRIM(NOMBRE) FROM VEND01 WHERE STATUS = 'A'")
        rows = cur.fetchall()
        vendedores = [{'clave': r[0], 'nombre': r[1]} for r in rows]
        return {"total": len(vendedores), "vendedores": vendedores}
    finally:
        conn.close()

@app.post("/sync/remision")
def recibir_remision(remision: dict):
    """
    Recibe una remisión desde la tablet e inserta de forma transaccional en SAE:
    FACTR01 (Encabezado) y PAR_FACTR01 (Partidas).
    """
    conn = get_fb_connection()
    cur = conn.cursor()
    try:
        folio = remision.get("folio")
        cve_cliente = remision.get("cve_cliente")
        cve_vendedor = remision.get("cve_vendedor")
        total = remision.get("total", 0.0)
        partidas = remision.get("partidas", [])
        
        # 1. Insertar Encabezado FACTR01
        cur.execute("""
            INSERT INTO FACTR01 (TIP_DOC, CVE_DOC, CVE_CLPV, STATUS, DAT_MOSTR, CVE_VEND, CAN_TOT, IMP_TOT1, FECHA_DOCU)
            VALUES ('R', ?, ?, 'E', 0, ?, ?, 0, CURRENT_DATE)
        """, (folio, cve_cliente, cve_vendedor, total))
        
        # 2. Insertar Partidas PAR_FACTR01
        num_partida = 1
        for p in partidas:
            cur.execute("""
                INSERT INTO PAR_FACTR01 (CVE_DOC, NUM_PAR, CVE_ART, CANT, PREC, TOT_PARTIDA)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (folio, num_partida, p.get("cve_producto"), p.get("cantidad"), p.get("precio_unitario"), p.get("total_partida")))
            num_partida += 1
            
        conn.commit()
        return {"status": "OK", "message": f"Remisión {folio} sincronizada correctamente en SAE."}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error al vaciar remisión en SAE: {str(e)}")
    finally:
        conn.close()

if __name__ == "__main__":
    import uvicorn
    print("Iniciando servicio backend de sincronización con Aspel SAE...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
