import sys
import firebirdsql
import json

try:
    with open('config_sae.json', 'r', encoding='utf-8') as f:
        cfg = json.load(f)
    conn = firebirdsql.connect(
        host=cfg.get('host', 'localhost'),
        database=cfg.get('database', ''),
        user=cfg.get('user', 'SYSDBA'),
        password=cfg.get('password', 'masterkey'),
        charset=cfg.get('charset', 'UTF8')
    )
    cur = conn.cursor()
    cur.execute("SELECT FIRST 1 * FROM IMPU01")
    desc = cur.description
    columns = [d[0] for d in desc]
    print(f"IMPU01 columns: {columns}")
    
    cur.execute("SELECT FIRST 1 * FROM INVE01")
    desc = cur.description
    columns = [d[0] for d in desc]
    print(f"INVE01 columns (containing ESQ): {[c for c in columns if 'ESQ' in c]}")
    
    conn.close()
except Exception as e:
    print(f"Error: {e}")
