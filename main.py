from fastapi import FastAPI, Depends, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager

from database import engine, Base, get_db
import models
import schemas
import security

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Crear tablas si no existen
    models.Base.metadata.create_all(bind=engine)
    
    # Auto-migración básica para añadir nuevas columnas a la tabla negocio (si no existen)
    from sqlalchemy import text
    try:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE negocio ADD COLUMN IF NOT EXISTS galeria_nombre VARCHAR(255);"))
            conn.execute(text("ALTER TABLE negocio ADD COLUMN IF NOT EXISTS stand_numero VARCHAR(50);"))
            conn.commit()
    except Exception as e:
        print(f"Error en auto-migración: {e}")
        
    yield

app = FastAPI(title="FormalízaYa API - DevSecOps", lifespan=lifespan)

# Configurar CORS (DevSecOps: Solo permitir dominios de confianza)
origins = [
    "http://localhost:5173", # Frontend VITE
    "https://pc-2-frontend0503.vercel.app", # URL real de Vercel
    # "https://tu-dominio-produccion.com"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Middleware de Seguridad y Auditoría Básica (intercepta peticiones POST/PUT/DELETE)
@app.middleware("http")
async def audit_middleware(request: Request, call_next):
    # TODO: Implementar lógica de inserción en AUDITORIA si el método es modificador
    # y si hay usuario autenticado.
    response = await call_next(request)
    # DevSecOps: Headers de seguridad
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response

@app.get("/")
def read_root():
    return {"message": "FormalízaYa API conectada a PostgreSQL"}

# --- RUTAS DE AUTENTICACIÓN Y REGISTRO REAL ---
@app.post("/api/negocios/registrar_ambulante", response_model=schemas.UsuarioResponse, status_code=status.HTTP_201_CREATED)
def registrar_ambulante(data: schemas.RegistroAmbulanteCreate, db: Session = Depends(get_db)):
    # Validar correo único
    if db.query(models.Usuario).filter(models.Usuario.correo == data.correo).first():
        raise HTTPException(status_code=400, detail="El correo ya está registrado")
    # Validar DNI único
    if db.query(models.Usuario).filter(models.Usuario.dni == data.dni).first():
        raise HTTPException(status_code=400, detail="El DNI ya está registrado")
    
    # Crear Usuario
    hashed_password = security.get_password_hash(data.password)
    nuevo_usuario = models.Usuario(
        dni=data.dni,
        nombre_completo=f"Ambulante {data.dni}", # Idealmente viene de RENIEC
        correo=data.correo,
        password_hash=hashed_password,
        rol=models.RolUsuario.ambulante
    )
    db.add(nuevo_usuario)
    db.flush() # Para obtener el ID

    # Crear Negocio
    nuevo_negocio = models.Negocio(
        usuario_id=nuevo_usuario.id,
        nombre_negocio=data.negocio,
        tipo=models.TipoNegocio.ambulante,
        rubro=data.rubro,
        referencia_ubicacion=data.referencia
    )
    db.add(nuevo_negocio)
    db.commit()
    db.refresh(nuevo_usuario)
    return nuevo_usuario

@app.post("/api/negocios/registrar_galeria", response_model=schemas.UsuarioResponse, status_code=status.HTTP_201_CREATED)
def registrar_galeria(data: schemas.RegistroGaleriaCreate, db: Session = Depends(get_db)):
    if db.query(models.Usuario).filter(models.Usuario.correo == data.correo).first():
        raise HTTPException(status_code=400, detail="El correo ya está registrado")
    if db.query(models.Usuario).filter(models.Usuario.dni == data.dni).first():
        raise HTTPException(status_code=400, detail="El DNI ya está registrado")
    
    hashed_password = security.get_password_hash(data.password)
    nuevo_usuario = models.Usuario(
        dni=data.dni,
        nombre_completo=f"Galería {data.dni}",
        correo=data.correo,
        password_hash=hashed_password,
        rol=models.RolUsuario.galeria
    )
    db.add(nuevo_usuario)
    db.flush()

    nuevo_negocio = models.Negocio(
        usuario_id=nuevo_usuario.id,
        nombre_negocio=data.negocio,
        tipo=models.TipoNegocio.galeria,
        rubro=data.rubro,
        galeria_nombre=data.galeria_nombre,
        stand_numero=data.stand_numero
    )
    db.add(nuevo_negocio)
    db.commit()
    db.refresh(nuevo_usuario)
    return nuevo_usuario

@app.post("/api/auth/login")
def login(credentials: schemas.LoginCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.Usuario).filter(models.Usuario.correo == credentials.correo).first()
    if not db_user or not security.verify_password(credentials.password, db_user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales incorrectas")
    
    access_token = security.create_access_token(data={"sub": str(db_user.id)})
    
    return {
        "access_token": access_token, 
        "token_type": "bearer", 
        "rol": db_user.rol.value, 
        "nombre": db_user.nombre_completo
    }

import random
from datetime import datetime, timedelta, timezone

@app.post("/api/auth/recuperar_password")
def recuperar_password(data: schemas.RecoverRequest, db: Session = Depends(get_db)):
    user = db.query(models.Usuario).filter(models.Usuario.correo == data.correo).first()
    if not user:
        # DevSecOps: Retornar 200 siempre para evitar enumeración de correos
        return {"message": "Si el correo existe, se ha enviado un código."}
    
    codigo = f"{random.randint(100000, 999999)}"
    expiracion = datetime.now(timezone.utc) + timedelta(minutes=15)
    
    nuevo_codigo = models.CodigoRecuperacion(
        correo=data.correo,
        codigo=codigo,
        expira_en=expiracion
    )
    db.add(nuevo_codigo)
    db.commit()
    
    # MOCK ENVÍO CORREO
    print(f"\\n[{datetime.now()}] 📧 SIMULACIÓN ENVÍO DE CORREO:")
    print(f"Para: {data.correo}")
    print(f"Código de recuperación: {codigo}\\n")
    
    return {"message": "Si el correo existe, se ha enviado un código."}

@app.post("/api/auth/reset_password")
def reset_password(data: schemas.ResetPasswordRequest, db: Session = Depends(get_db)):
    # Buscar el último código no usado para ese correo
    registro_codigo = db.query(models.CodigoRecuperacion).filter(
        models.CodigoRecuperacion.correo == data.correo,
        models.CodigoRecuperacion.codigo == data.codigo,
        models.CodigoRecuperacion.usado == False
    ).order_by(models.CodigoRecuperacion.created_at.desc()).first()
    
    if not registro_codigo:
        raise HTTPException(status_code=400, detail="Código inválido o ya usado")
        
    if registro_codigo.expira_en < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="El código ha expirado")
        
    user = db.query(models.Usuario).filter(models.Usuario.correo == data.correo).first()
    if not user:
        raise HTTPException(status_code=400, detail="Usuario no encontrado")
        
    user.password_hash = security.get_password_hash(data.new_password)
    registro_codigo.usado = True
    db.commit()
    
    return {"message": "Contraseña actualizada exitosamente"}
