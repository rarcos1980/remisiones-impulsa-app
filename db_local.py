import sqlite3
import os
import json
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "remisiones_local.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Inicializa las tablas de SQLite en la tablet para operar Offline-First."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Tabla de Clientes
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clientes (
            clave TEXT PRIMARY KEY,
            nombre TEXT NOT NULL,
            rfc TEXT,
            direccion TEXT,
            telefono TEXT
        )
    """)
    
    # 2. Tabla de Productos / Inventario
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS productos (
            clave TEXT PRIMARY KEY,
            descripcion TEXT NOT NULL,
            precio REAL DEFAULT 0.0,
            existencia REAL DEFAULT 0.0,
            linea TEXT,
            cve_esqimpu INTEGER DEFAULT 1
        )
    """)

    # 3. Tabla de Precios por Producto (PRECIO_X_PROD)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS precios_x_producto (
            cve_art TEXT,
            cve_precio INTEGER,
            precio REAL DEFAULT 0.0,
            PRIMARY KEY (cve_art, cve_precio)
        )
    """)
    
    # 4. Tabla de Lotes por Producto
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS lotes (
            cve_art TEXT,
            lote TEXT,
            cantidad REAL,
            fecha_cad TEXT,
            PRIMARY KEY (cve_art, lote)
        )
    """)

    # 5. Tabla de Vendedores
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS esquemas_impuestos (
            cve_esquema INTEGER PRIMARY KEY,
            descripcion TEXT,
            impuesto1 REAL DEFAULT 0.0,
            impuesto2 REAL DEFAULT 0.0,
            impuesto3 REAL DEFAULT 0.0,
            impuesto4 REAL DEFAULT 0.0
        )
    """)
    
    # 6. Tabla de Vendedores
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vendedores (
            clave TEXT PRIMARY KEY,
            nombre TEXT NOT NULL
        )
    """)
    
    # 6. Tabla de Remisiones (Encabezado)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS remisiones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            folio TEXT UNIQUE,
            fecha TEXT,
            cve_cliente TEXT,
            nombre_cliente TEXT,
            direccion_cliente TEXT,
            cve_vendedor TEXT,
            nombre_vendedor TEXT,
            
            -- Especialidades (Checkboxes)
            esp_electrofisiologia INTEGER DEFAULT 0,
            esp_radiologia INTEGER DEFAULT 0,
            esp_cardiologia INTEGER DEFAULT 0,
            esp_endovascular INTEGER DEFAULT 0,
            esp_neuromodulacion INTEGER DEFAULT 0,
            
            -- Datos Paciente / Expediente
            nombre_paciente TEXT,
            nombre_doctor TEXT,
            episodio TEXT,
            aseguradora TEXT,
            diagnostico TEXT,
            agente TEXT,
            
            -- Nuevos campos
            condicion TEXT DEFAULT 'CONTADO',
            observaciones TEXT,
            
            -- Totales
            subtotal REAL DEFAULT 0.0,
            descuento_porcentaje REAL DEFAULT 0.0,
            descuento_monto REAL DEFAULT 0.0,
            iva_monto REAL DEFAULT 0.0,
            total REAL DEFAULT 0.0,
            total_letra TEXT,
            
            -- Pagaré y Firmas
            fecha_pagare TEXT,
            monto_pagare REAL DEFAULT 0.0,
            firma_agente_path TEXT,
            firma_cliente_path TEXT,
            
            -- Estado de Sincronización
            estatus_sync TEXT DEFAULT 'PENDIENTE', -- 'PENDIENTE', 'SINCRONIZADO', 'ERROR'
            fecha_creacion TEXT,
            fecha_sync TEXT
        )
    """)

    # 7. Tabla de Partidas de Remisión
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS remision_partidas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            remision_id INTEGER,
            num_partida INTEGER,
            cve_producto TEXT,
            alg TEXT,
            descripcion TEXT,
            lote TEXT,
            cantidad REAL,
            precio_unitario REAL,
            total_partida REAL,
            iva_monto REAL DEFAULT 0.0,
            cve_esqimpu INTEGER DEFAULT 1,
            FOREIGN KEY (remision_id) REFERENCES remisiones(id) ON DELETE CASCADE
        )
    """)

    # Migraciones para agregar campos si ya existía la BD
    try:
        cursor.execute("ALTER TABLE remisiones ADD COLUMN condicion TEXT DEFAULT 'CONTADO'")
    except sqlite3.OperationalError:
        pass # La columna ya existe
    try:
        cursor.execute("ALTER TABLE remisiones ADD COLUMN observaciones TEXT")
    except sqlite3.OperationalError:
        pass # La columna ya existe

    conn.commit()
    conn.close()
    print("Base de datos local SQLite inicializada correctamente.")

def guardar_remision_local(datos_remision, partidas):
    """
    Guarda la remisión completa (Encabezado + Partidas) en la base SQLite local de la tablet.
    Regresa el ID asignado y el folio.
    """
    conn = get_connection()
    cur = conn.cursor()
    try:
        esp = datos_remision.get('especialidades', {})
        cur.execute("""
            INSERT INTO remisiones (
                folio, fecha, cve_cliente, nombre_cliente, direccion_cliente,
                cve_vendedor, nombre_vendedor, esp_electrofisiologia, esp_radiologia,
                esp_cardiologia, esp_endovascular, esp_neuromodulacion,
                nombre_paciente, nombre_doctor, episodio, aseguradora, diagnostico, agente,
                condicion, observaciones,
                subtotal, descuento_porcentaje, descuento_monto, iva_monto, total, total_letra,
                fecha_pagare, monto_pagare, estatus_sync, fecha_creacion
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDIENTE', datetime('now', 'localtime'))
        """, (
            datos_remision.get('folio'),
            datos_remision.get('fecha'),
            datos_remision.get('cve_cliente', ''),
            datos_remision.get('nombre_cliente', ''),
            datos_remision.get('direccion_cliente', ''),
            datos_remision.get('cve_vendedor', ''),
            datos_remision.get('nombre_vendedor', ''),
            1 if esp.get('electrofisiologia') else 0,
            1 if esp.get('radiologia') else 0,
            1 if esp.get('cardiologia') else 0,
            1 if esp.get('endovascular') else 0,
            1 if esp.get('neuromodulacion') else 0,
            datos_remision.get('nombre_paciente', ''),
            datos_remision.get('nombre_doctor', ''),
            datos_remision.get('episodio', ''),
            datos_remision.get('aseguradora', ''),
            datos_remision.get('diagnostico', ''),
            datos_remision.get('agente', ''),
            datos_remision.get('condicion', 'CONTADO'),
            datos_remision.get('observaciones', ''),
            datos_remision.get('subtotal', 0.0),
            datos_remision.get('descuento_pct', 0.0),
            datos_remision.get('descuento_monto', 0.0),
            datos_remision.get('iva', 0.0),
            datos_remision.get('total', 0.0),
            datos_remision.get('total_letra', ''),
            datos_remision.get('fecha_pagare', ''),
            datos_remision.get('total', 0.0)
        ))
        
        remision_id = cur.lastrowid
        
        # Insertar partidas
        num_part = 1
        for p in partidas:
            cur.execute("""
                INSERT INTO remision_partidas (
                    remision_id, num_partida, cve_producto, alg, descripcion, lote, cantidad, precio_unitario, total_partida, iva_monto, cve_esqimpu
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                remision_id,
                num_part,
                p.get('cve_producto', ''),
                p.get('alg', ''),
                p.get('descripcion', ''),
                p.get('lote', ''),
                p.get('cantidad', 1.0),
                p.get('precio_unitario', 0.0),
                p.get('total_partida', 0.0),
                p.get('iva_monto', 0.0),
                p.get('cve_esqimpu', 1)
            ))
            num_part += 1
            
        conn.commit()
        return True, remision_id, "Remisión guardada exitosamente en la base de datos local."
    except Exception as e:
        conn.rollback()
        return False, None, f"Error al guardar remisión en SQLite: {str(e)}"
    finally:
        conn.close()

def obtener_ventas_historial():
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, folio, fecha, nombre_cliente, total, estatus_sync FROM remisiones ORDER BY id DESC")
        rows = cur.fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"Error al obtener historial: {e}")
        return []
    finally:
        conn.close()

def obtener_venta_completa(remision_id):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM remisiones WHERE id = ?", (remision_id,))
        encabezado = dict(cur.fetchone())
        
        cur.execute("SELECT * FROM remision_partidas WHERE remision_id = ? ORDER BY num_partida", (remision_id,))
        partidas = [dict(r) for r in cur.fetchall()]
        
        return encabezado, partidas
    except Exception as e:
        print(f"Error al obtener venta {remision_id}: {e}")
        return None, None
    finally:
        conn.close()

def marcar_venta_sincronizada(remision_id):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE remisiones SET estatus_sync = 'SINCRONIZADO', fecha_sync = datetime('now', 'localtime') WHERE id = ?", (remision_id,))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"Error al marcar como sincronizada: {e}")
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    init_db()
