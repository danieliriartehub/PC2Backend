from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from models import (
    RolUsuario, TipoNegocio, EstadoNegocio, TipoLicencia, EstadoLicencia, 
    EstadoSolicitud, EstadoTrabajador, EstadoSunat, TipoAlerta, CanalAlerta, 
    AccionAuditoria, TipoReporte, FuenteConsulta
)

# --- Usuario ---
class UsuarioBase(BaseModel):
    dni: Optional[str] = None
    ruc: Optional[str] = None
    nombre_completo: str
    celular: Optional[str] = None
    correo: EmailStr
    rol: RolUsuario = RolUsuario.ambulante

class UsuarioCreate(UsuarioBase):
    password: str

class UsuarioResponse(UsuarioBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# --- Negocio ---
class NegocioBase(BaseModel):
    nombre_negocio: str
    tipo: TipoNegocio
    rubro: Optional[str] = None
    descripcion_rubro: Optional[str] = None
    referencia_ubicacion: Optional[str] = None
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    galeria_nombre: Optional[str] = None
    stand_numero: Optional[str] = None
    stand_piso: Optional[str] = None
    estado: EstadoNegocio = EstadoNegocio.activo
    qr_code_url: Optional[str] = None

class NegocioCreate(NegocioBase):
    pass

class NegocioResponse(NegocioBase):
    id: int
    usuario_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# --- JWT Tokens ---
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class TokenPayload(BaseModel):
    sub: Optional[str] = None
    type: Optional[str] = None

# Aquí se pueden seguir añadiendo los demás esquemas (Licencia, Alerta, etc)
