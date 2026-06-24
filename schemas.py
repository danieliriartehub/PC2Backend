from pydantic import BaseModel, EmailStr, ConfigDict, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from models import (
    RolUsuario, TipoNegocio, EstadoNegocio, TipoLicencia, EstadoLicencia, 
    EstadoSolicitud, EstadoTrabajador, EstadoSunat, TipoAlerta, CanalAlerta, 
    AccionAuditoria, TipoReporte, FuenteConsulta
)

# --- Usuario ---
class UsuarioBase(BaseModel):
    dni: str = Field(..., min_length=8, max_length=8, pattern=r"^\d{8}$", description="DNI exacto de 8 dígitos")
    ruc: Optional[str] = Field(None, min_length=11, max_length=11, pattern=r"^\d{11}$")
    nombre_completo: str = Field(..., min_length=2, max_length=100)
    celular: Optional[str] = Field(None, min_length=9, max_length=15)
    correo: EmailStr
    rol: RolUsuario = RolUsuario.ambulante

class UsuarioCreate(UsuarioBase):
    password: str = Field(..., min_length=6, description="Contraseña mínimo 6 caracteres")

class UsuarioResponse(UsuarioBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# --- Negocio ---
class NegocioBase(BaseModel):
    nombre_negocio: str = Field(..., min_length=2, max_length=150)
    tipo: TipoNegocio
    rubro: Optional[str] = Field(None, max_length=100)
    descripcion_rubro: Optional[str] = Field(None, max_length=255)
    referencia_ubicacion: Optional[str] = Field(None, max_length=255)
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    galeria_nombre: Optional[str] = Field(None, max_length=150)
    stand_numero: Optional[str] = Field(None, max_length=20)
    stand_piso: Optional[str] = Field(None, max_length=20)
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

# --- Registro Combinado (Frontend) ---
class RegistroAmbulanteCreate(BaseModel):
    dni: str = Field(..., min_length=8, max_length=8, pattern=r"^\d{8}$")
    correo: EmailStr
    password: str = Field(..., min_length=6)
    negocio: str = Field(..., min_length=2, max_length=150)
    rubro: str
    referencia: str = Field(..., min_length=4)

class RegistroGaleriaCreate(BaseModel):
    dni: str = Field(..., min_length=8, max_length=8, pattern=r"^\d{8}$")
    correo: EmailStr
    password: str = Field(..., min_length=6)
    negocio: str = Field(..., min_length=2, max_length=150)
    rubro: str
    galeria_nombre: str = Field(..., min_length=2)
    stand_numero: str

# --- Login & Recover ---
class LoginCreate(BaseModel):
    correo: EmailStr
    password: str

class RecoverRequest(BaseModel):
    correo: EmailStr

class ResetPasswordRequest(BaseModel):
    correo: EmailStr
    codigo: str = Field(..., min_length=6, max_length=6)
    new_password: str = Field(..., min_length=6)
