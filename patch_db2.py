import sqlite3
conn = sqlite3.connect('remisiones_local.db')
c = conn.cursor()
try:
    c.execute("ALTER TABLE remision_partidas ADD COLUMN iva_monto REAL DEFAULT 0.0")
    print("Added iva_monto to remision_partidas")
except Exception as e:
    print(f"remision_partidas iva_monto: {e}")

try:
    c.execute("ALTER TABLE remision_partidas ADD COLUMN cve_esqimpu INTEGER DEFAULT 1")
    print("Added cve_esqimpu to remision_partidas")
except Exception as e:
    print(f"remision_partidas cve_esqimpu: {e}")
    
conn.commit()
conn.close()
