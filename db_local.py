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
    
    # Tabla de Clientes
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clientes (
            clave TEXT PRIMARY KEY,
            nombre TEXT NOT NULL,
            rfc TEXT,
            direccion TEXT,
            telefono TEXT
        )
    """)
    
    # Tabla de Productos / Inventario
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS productos (
            clave TEXT PRIMARY KEY,
            descripcion TEXT NOT NULL,
            precio REAL DEFAULT 0.0,
            existencia REAL DEFAULT 0.0,
            linea TEXT
        )
    """)
    
    # Tabla de Lotes por Producto
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS lotes (
            cve_art TEXT,
            lote TEXT,
            cantidad REAL,
            fecha_cad TEXT,
            PRIMARY KEY (cve_art, lote)
        )
    """)

    # Tabla de Vendedores
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vendedores (
            clave TEXT PRIMARY KEY,
            nombre TEXT NOT NULL
        )
    """)
    
    # Tabla de Remisiones (Encabezado)
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

    # Tabla de Partidas de Remisión
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
            FOREIGN KEY (remision_id) REFERENCES remisiones(id) ON DELETE CASCADE
        )
    """)

    conn.commit()
    conn.close()
    print("Base de datos local SQLite inicializada correctamente.")

if __name__ == "__main__":
    init_db()
