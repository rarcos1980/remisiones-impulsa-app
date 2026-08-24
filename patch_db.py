import sqlite3
conn = sqlite3.connect('remisiones_local.db')
c = conn.cursor()
try:
    c.execute("ALTER TABLE productos ADD COLUMN cve_esqimpu INTEGER DEFAULT 1")
    print("Added cve_esqimpu to productos")
except Exception as e:
    print(f"productos: {e}")

try:
    c.execute('''
        CREATE TABLE IF NOT EXISTS esquemas_impuestos (
            cve_esquema INTEGER PRIMARY KEY,
            descripcion TEXT,
            impuesto1 REAL DEFAULT 0.0,
            impuesto2 REAL DEFAULT 0.0,
            impuesto3 REAL DEFAULT 0.0,
            impuesto4 REAL DEFAULT 0.0
        )
    ''')
    print("Created esquemas_impuestos")
except Exception as e:
    print(f"esquemas_impuestos: {e}")

try:
    c.execute("ALTER TABLE detalle_remision ADD COLUMN iva_monto REAL DEFAULT 0.0")
    print("Added iva_monto to detalle_remision")
except Exception as e:
    print(f"detalle_remision iva_monto: {e}")

try:
    c.execute("ALTER TABLE detalle_remision ADD COLUMN ieps_monto REAL DEFAULT 0.0")
    print("Added ieps_monto to detalle_remision")
except Exception as e:
    print(f"detalle_remision ieps_monto: {e}")

conn.commit()
conn.close()
