-- SQL Script para inicializar la base de datos PostgreSQL en Railway
-- Proyecto: FormalízaYa
-- Enfoque: DevSecOps y Modelo de Dominio

-- ==========================================
-- 1. EXTENSIONES Y FUNCIONES
-- ==========================================
-- Asegura que podamos guardar UUIDs u otros si fuera necesario.
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Función para actualizar el campo updated_at automáticamente
CREATE OR REPLACE FUNCTION update_modified_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- ==========================================
-- 2. TIPOS ENUMERADOS (Dominios Restringidos)
-- ==========================================
CREATE TYPE rol_usuario AS ENUM ('ambulante', 'galeria', 'admin');
CREATE TYPE tipo_negocio AS ENUM ('ambulante', 'galeria');
CREATE TYPE estado_negocio AS ENUM ('activo', 'inactivo', 'suspendido');
CREATE TYPE tipo_licencia_enum AS ENUM ('provisional', 'definitiva');
CREATE TYPE estado_licencia AS ENUM ('vigente', 'por_vencer', 'vencida', 'en_tramite', 'anulada');
CREATE TYPE estado_solicitud AS ENUM ('pendiente', 'en_revision', 'aprobada', 'rechazada');
CREATE TYPE estado_trabajador AS ENUM ('activo', 'inactivo');
CREATE TYPE estado_sunat_enum AS ENUM ('activo', 'baja', 'no_habido');
CREATE TYPE tipo_alerta AS ENUM ('vencimiento_proximo', 'licencia_vencida', 'solicitud_aprobada', 'solicitud_rechazada');
CREATE TYPE canal_alerta AS ENUM ('sistema', 'whatsapp', 'correo');
CREATE TYPE accion_auditoria AS ENUM ('INSERT', 'UPDATE', 'DELETE');
CREATE TYPE tipo_reporte AS ENUM ('negocios_formalizados', 'licencias_vencidas', 'trabajadores_activos', 'exportacion_sunat');
CREATE TYPE fuente_consulta AS ENUM ('reniec', 'sunat');

-- ==========================================
-- 3. TABLAS DEL NÚCLEO DE NEGOCIO
-- ==========================================

CREATE TABLE USUARIO (
    id SERIAL PRIMARY KEY,
    dni VARCHAR(8) UNIQUE,
    ruc VARCHAR(11) UNIQUE,
    nombre_completo VARCHAR(255) NOT NULL,
    celular VARCHAR(15),
    correo VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    rol rol_usuario DEFAULT 'ambulante',
    token_jwt TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TRIGGER update_usuario_modtime
BEFORE UPDATE ON USUARIO FOR EACH ROW EXECUTE PROCEDURE update_modified_column();


CREATE TABLE NEGOCIO (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER NOT NULL REFERENCES USUARIO(id) ON DELETE RESTRICT,
    nombre_negocio VARCHAR(255) NOT NULL,
    tipo tipo_negocio NOT NULL,
    rubro VARCHAR(255),
    descripcion_rubro TEXT,
    referencia_ubicacion TEXT,
    latitud DECIMAL(10, 8),
    longitud DECIMAL(11, 8),
    galeria_nombre VARCHAR(255),
    stand_numero VARCHAR(50),
    stand_piso VARCHAR(50),
    estado estado_negocio DEFAULT 'activo',
    qr_code_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TRIGGER update_negocio_modtime
BEFORE UPDATE ON NEGOCIO FOR EACH ROW EXECUTE PROCEDURE update_modified_column();


CREATE TABLE LICENCIA (
    id SERIAL PRIMARY KEY,
    negocio_id INTEGER NOT NULL REFERENCES NEGOCIO(id) ON DELETE RESTRICT,
    numero_licencia VARCHAR(100) UNIQUE NOT NULL,
    tipo_licencia tipo_licencia_enum NOT NULL,
    estado estado_licencia DEFAULT 'en_tramite',
    fecha_emision DATE,
    fecha_vencimiento DATE,
    entidad_emisora VARCHAR(255),
    archivo_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE SOLICITUD_RENOVACION (
    id SERIAL PRIMARY KEY,
    licencia_id INTEGER NOT NULL REFERENCES LICENCIA(id) ON DELETE RESTRICT,
    negocio_id INTEGER NOT NULL REFERENCES NEGOCIO(id) ON DELETE RESTRICT,
    estado estado_solicitud DEFAULT 'pendiente',
    motivo TEXT,
    observaciones_admin TEXT,
    fecha_solicitud TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    fecha_resolucion TIMESTAMP WITH TIME ZONE
);


CREATE TABLE TRABAJADOR (
    id SERIAL PRIMARY KEY,
    negocio_id INTEGER NOT NULL REFERENCES NEGOCIO(id) ON DELETE RESTRICT,
    dni VARCHAR(8) NOT NULL,
    nombre_completo VARCHAR(255) NOT NULL,
    cargo VARCHAR(100),
    fecha_ingreso DATE,
    fecha_salida DATE,
    estado estado_trabajador DEFAULT 'activo',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE REGISTRO_TRIBUTARIO (
    id SERIAL PRIMARY KEY,
    negocio_id INTEGER UNIQUE NOT NULL REFERENCES NEGOCIO(id) ON DELETE RESTRICT,
    ruc VARCHAR(11) NOT NULL,
    razon_social VARCHAR(255) NOT NULL,
    estado_sunat estado_sunat_enum,
    regimen_tributario VARCHAR(100),
    tipo_contribuyente VARCHAR(100),
    ultima_consulta TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ==========================================
-- 4. TABLAS DE SOPORTE Y TRAZABILIDAD
-- ==========================================

CREATE TABLE ALERTA (
    id SERIAL PRIMARY KEY,
    negocio_id INTEGER NOT NULL REFERENCES NEGOCIO(id) ON DELETE RESTRICT,
    licencia_id INTEGER REFERENCES LICENCIA(id) ON DELETE RESTRICT,
    tipo tipo_alerta NOT NULL,
    canal canal_alerta NOT NULL,
    mensaje TEXT NOT NULL,
    leida BOOLEAN DEFAULT FALSE,
    fecha_envio TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    fecha_lectura TIMESTAMP WITH TIME ZONE
);


CREATE TABLE QR_NEGOCIO (
    id SERIAL PRIMARY KEY,
    negocio_id INTEGER UNIQUE NOT NULL REFERENCES NEGOCIO(id) ON DELETE RESTRICT,
    codigo_qr VARCHAR(100) UNIQUE NOT NULL,
    url_publica TEXT NOT NULL,
    total_escaneos INTEGER DEFAULT 0,
    ultimo_escaneo TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE AUDITORIA (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER REFERENCES USUARIO(id) ON DELETE SET NULL,
    tabla_afectada VARCHAR(100) NOT NULL,
    accion accion_auditoria NOT NULL,
    datos_anteriores JSONB,
    datos_nuevos JSONB,
    ip_origen VARCHAR(45),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Evitar que la tabla AUDITORIA sea modificada o eliminada (Inmutabilidad DevSecOps)
CREATE OR REPLACE FUNCTION prevent_audit_modification()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'La tabla AUDITORIA es inmutable por motivos de DevSecOps. No se permiten UPDATE o DELETE.';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tg_prevent_audit_update
BEFORE UPDATE ON AUDITORIA
FOR EACH ROW EXECUTE PROCEDURE prevent_audit_modification();

CREATE TRIGGER tg_prevent_audit_delete
BEFORE DELETE ON AUDITORIA
FOR EACH ROW EXECUTE PROCEDURE prevent_audit_modification();


CREATE TABLE REPORTE (
    id SERIAL PRIMARY KEY,
    generado_por INTEGER NOT NULL REFERENCES USUARIO(id) ON DELETE RESTRICT,
    tipo tipo_reporte NOT NULL,
    archivo_url TEXT NOT NULL,
    filtros_aplicados JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE CONSULTA_EXTERNA (
    id SERIAL PRIMARY KEY,
    negocio_id INTEGER REFERENCES NEGOCIO(id) ON DELETE RESTRICT,
    fuente fuente_consulta NOT NULL,
    parametro_consulta VARCHAR(255),
    respuesta_raw JSONB,
    exitosa BOOLEAN DEFAULT TRUE,
    codigo_http INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ==========================================
-- FIN DEL SCRIPT
-- ==========================================
