import enum
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, Text, Enum, Numeric, func, JSON
from sqlalchemy.orm import relationship
from database import Base

# ==========================================
# ENUMS
# ==========================================
class RolUsuario(str, enum.Enum):
    ambulante = "ambulante"
    galeria = "galeria"
    admin = "admin"

class TipoNegocio(str, enum.Enum):
    ambulante = "ambulante"
    galeria = "galeria"

class EstadoNegocio(str, enum.Enum):
    activo = "activo"
    inactivo = "inactivo"
    suspendido = "suspendido"

class TipoLicencia(str, enum.Enum):
    provisional = "provisional"
    definitiva = "definitiva"

class EstadoLicencia(str, enum.Enum):
    vigente = "vigente"
    por_vencer = "por_vencer"
    vencida = "vencida"
    en_tramite = "en_tramite"
    anulada = "anulada"

class EstadoSolicitud(str, enum.Enum):
    pendiente = "pendiente"
    en_revision = "en_revision"
    aprobada = "aprobada"
    rechazada = "rechazada"

class EstadoTrabajador(str, enum.Enum):
    activo = "activo"
    inactivo = "inactivo"

class EstadoSunat(str, enum.Enum):
    activo = "activo"
    baja = "baja"
    no_habido = "no_habido"

class TipoAlerta(str, enum.Enum):
    vencimiento_proximo = "vencimiento_proximo"
    licencia_vencida = "licencia_vencida"
    solicitud_aprobada = "solicitud_aprobada"
    solicitud_rechazada = "solicitud_rechazada"

class CanalAlerta(str, enum.Enum):
    sistema = "sistema"
    whatsapp = "whatsapp"
    correo = "correo"

class AccionAuditoria(str, enum.Enum):
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"

class TipoReporte(str, enum.Enum):
    negocios_formalizados = "negocios_formalizados"
    licencias_vencidas = "licencias_vencidas"
    trabajadores_activos = "trabajadores_activos"
    exportacion_sunat = "exportacion_sunat"

class FuenteConsulta(str, enum.Enum):
    reniec = "reniec"
    sunat = "sunat"

# ==========================================
# MODELOS DE BASE DE DATOS
# ==========================================

class Usuario(Base):
    __tablename__ = "usuario"

    id = Column(Integer, primary_key=True, index=True)
    dni = Column(String(8), unique=True, index=True)
    ruc = Column(String(11), unique=True, index=True)
    nombre_completo = Column(String(255), nullable=False)
    celular = Column(String(15))
    correo = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    rol = Column(Enum(RolUsuario), default=RolUsuario.ambulante)
    token_jwt = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    negocios = relationship("Negocio", back_populates="usuario")
    reportes = relationship("Reporte", back_populates="generador")
    auditorias = relationship("Auditoria", back_populates="usuario")


class Negocio(Base):
    __tablename__ = "negocio"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuario.id", ondelete="RESTRICT"), nullable=False)
    nombre_negocio = Column(String(255), nullable=False)
    tipo = Column(Enum(TipoNegocio), nullable=False)
    rubro = Column(String(255))
    descripcion_rubro = Column(Text)
    referencia_ubicacion = Column(Text)
    latitud = Column(Numeric(10, 8))
    longitud = Column(Numeric(11, 8))
    galeria_nombre = Column(String(255))
    stand_numero = Column(String(50))
    stand_piso = Column(String(50))
    estado = Column(Enum(EstadoNegocio), default=EstadoNegocio.activo)
    qr_code_url = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    usuario = relationship("Usuario", back_populates="negocios")
    licencias = relationship("Licencia", back_populates="negocio")
    solicitudes = relationship("SolicitudRenovacion", back_populates="negocio")
    trabajadores = relationship("Trabajador", back_populates="negocio")
    registro_tributario = relationship("RegistroTributario", back_populates="negocio", uselist=False)
    alertas = relationship("Alerta", back_populates="negocio")
    qr_negocio = relationship("QrNegocio", back_populates="negocio", uselist=False)
    consultas = relationship("ConsultaExterna", back_populates="negocio")


class Licencia(Base):
    __tablename__ = "licencia"

    id = Column(Integer, primary_key=True, index=True)
    negocio_id = Column(Integer, ForeignKey("negocio.id", ondelete="RESTRICT"), nullable=False)
    numero_licencia = Column(String(100), unique=True, index=True, nullable=False)
    tipo_licencia = Column(Enum(TipoLicencia), nullable=False)
    estado = Column(Enum(EstadoLicencia), default=EstadoLicencia.en_tramite)
    fecha_emision = Column(DateTime)
    fecha_vencimiento = Column(DateTime)
    entidad_emisora = Column(String(255))
    archivo_url = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    negocio = relationship("Negocio", back_populates="licencias")
    solicitudes = relationship("SolicitudRenovacion", back_populates="licencia")
    alertas = relationship("Alerta", back_populates="licencia")


class SolicitudRenovacion(Base):
    __tablename__ = "solicitud_renovacion"

    id = Column(Integer, primary_key=True, index=True)
    licencia_id = Column(Integer, ForeignKey("licencia.id", ondelete="RESTRICT"), nullable=False)
    negocio_id = Column(Integer, ForeignKey("negocio.id", ondelete="RESTRICT"), nullable=False)
    estado = Column(Enum(EstadoSolicitud), default=EstadoSolicitud.pendiente)
    motivo = Column(Text)
    observaciones_admin = Column(Text)
    fecha_solicitud = Column(DateTime(timezone=True), server_default=func.now())
    fecha_resolucion = Column(DateTime(timezone=True))

    licencia = relationship("Licencia", back_populates="solicitudes")
    negocio = relationship("Negocio", back_populates="solicitudes")


class Trabajador(Base):
    __tablename__ = "trabajador"

    id = Column(Integer, primary_key=True, index=True)
    negocio_id = Column(Integer, ForeignKey("negocio.id", ondelete="RESTRICT"), nullable=False)
    dni = Column(String(8), nullable=False)
    nombre_completo = Column(String(255), nullable=False)
    cargo = Column(String(100))
    fecha_ingreso = Column(DateTime)
    fecha_salida = Column(DateTime)
    estado = Column(Enum(EstadoTrabajador), default=EstadoTrabajador.activo)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    negocio = relationship("Negocio", back_populates="trabajadores")


class RegistroTributario(Base):
    __tablename__ = "registro_tributario"

    id = Column(Integer, primary_key=True, index=True)
    negocio_id = Column(Integer, ForeignKey("negocio.id", ondelete="RESTRICT"), unique=True, nullable=False)
    ruc = Column(String(11), nullable=False)
    razon_social = Column(String(255), nullable=False)
    estado_sunat = Column(Enum(EstadoSunat))
    regimen_tributario = Column(String(100))
    tipo_contribuyente = Column(String(100))
    ultima_consulta = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    negocio = relationship("Negocio", back_populates="registro_tributario")


class Alerta(Base):
    __tablename__ = "alerta"

    id = Column(Integer, primary_key=True, index=True)
    negocio_id = Column(Integer, ForeignKey("negocio.id", ondelete="RESTRICT"), nullable=False)
    licencia_id = Column(Integer, ForeignKey("licencia.id", ondelete="RESTRICT"))
    tipo = Column(Enum(TipoAlerta), nullable=False)
    canal = Column(Enum(CanalAlerta), nullable=False)
    mensaje = Column(Text, nullable=False)
    leida = Column(Boolean, default=False)
    fecha_envio = Column(DateTime(timezone=True), server_default=func.now())
    fecha_lectura = Column(DateTime(timezone=True))

    negocio = relationship("Negocio", back_populates="alertas")
    licencia = relationship("Licencia", back_populates="alertas")


class QrNegocio(Base):
    __tablename__ = "qr_negocio"

    id = Column(Integer, primary_key=True, index=True)
    negocio_id = Column(Integer, ForeignKey("negocio.id", ondelete="RESTRICT"), unique=True, nullable=False)
    codigo_qr = Column(String(100), unique=True, nullable=False)
    url_publica = Column(Text, nullable=False)
    total_escaneos = Column(Integer, default=0)
    ultimo_escaneo = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    negocio = relationship("Negocio", back_populates="qr_negocio")


class Auditoria(Base):
    __tablename__ = "auditoria"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuario.id", ondelete="SET NULL"))
    tabla_afectada = Column(String(100), nullable=False)
    accion = Column(Enum(AccionAuditoria), nullable=False)
    datos_anteriores = Column(JSON)
    datos_nuevos = Column(JSON)
    ip_origen = Column(String(45))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    usuario = relationship("Usuario", back_populates="auditorias")


class Reporte(Base):
    __tablename__ = "reporte"

    id = Column(Integer, primary_key=True, index=True)
    generado_por = Column(Integer, ForeignKey("usuario.id", ondelete="RESTRICT"), nullable=False)
    tipo = Column(Enum(TipoReporte), nullable=False)
    archivo_url = Column(Text, nullable=False)
    filtros_aplicados = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    generador = relationship("Usuario", back_populates="reportes")


class ConsultaExterna(Base):
    __tablename__ = "consulta_externa"

    id = Column(Integer, primary_key=True, index=True)
    negocio_id = Column(Integer, ForeignKey("negocio.id", ondelete="RESTRICT"))
    fuente = Column(Enum(FuenteConsulta), nullable=False)
    parametro_consulta = Column(String(255))
    respuesta_raw = Column(JSON)
    exitosa = Column(Boolean, default=True)
    codigo_http = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    negocio = relationship("Negocio", back_populates="consultas")


class CodigoRecuperacion(Base):
    __tablename__ = "codigo_recuperacion"

    id = Column(Integer, primary_key=True, index=True)
    correo = Column(String(255), index=True, nullable=False)
    codigo = Column(String(6), nullable=False)
    expira_en = Column(DateTime(timezone=True), nullable=False)
    usado = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
