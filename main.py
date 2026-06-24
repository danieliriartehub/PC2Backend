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
    try:
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
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.post("/api/negocios/registrar_galeria", response_model=schemas.UsuarioResponse, status_code=status.HTTP_201_CREATED)
def registrar_galeria(data: schemas.RegistroGaleriaCreate, db: Session = Depends(get_db)):
    try:
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
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

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

# --- Helper: Obtener usuario autenticado desde JWT ---
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
bearer_scheme = HTTPBearer(auto_error=False)

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme), db: Session = Depends(get_db)):
    if not credentials:
        raise HTTPException(status_code=401, detail="Token requerido")
    payload = security.verify_token(credentials.credentials)
    user_id = payload.get("sub")
    user = db.query(models.Usuario).filter(models.Usuario.id == int(user_id)).first()
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    return user

# --- DASHBOARD: Datos reales del vendedor ---
@app.get("/api/dashboard", response_model=schemas.DashboardResponse)
def get_dashboard(user: models.Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    negocios = db.query(models.Negocio).filter(models.Negocio.usuario_id == user.id).all()
    negocio_ids = [n.id for n in negocios]
    
    licencias = db.query(models.Licencia).filter(models.Licencia.negocio_id.in_(negocio_ids)).all() if negocio_ids else []
    trabajadores = db.query(models.Trabajador).filter(models.Trabajador.negocio_id.in_(negocio_ids)).all() if negocio_ids else []
    
    return schemas.DashboardResponse(
        usuario_id=user.id,
        nombre=user.nombre_completo,
        rol=user.rol.value,
        negocios=[schemas.NegocioDashboard.model_validate(n) for n in negocios],
        licencias=[schemas.LicenciaResponse.model_validate(l) for l in licencias],
        trabajadores=[schemas.TrabajadorResponse.model_validate(t) for t in trabajadores]
    )

# --- LICENCIAS ---
@app.get("/api/licencias", response_model=list[schemas.LicenciaResponse])
def listar_licencias(user: models.Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    negocio_ids = [n.id for n in db.query(models.Negocio).filter(models.Negocio.usuario_id == user.id).all()]
    if not negocio_ids:
        return []
    return db.query(models.Licencia).filter(models.Licencia.negocio_id.in_(negocio_ids)).all()

@app.post("/api/licencias", response_model=schemas.LicenciaResponse, status_code=201)
def crear_licencia(data: schemas.LicenciaCreate, user: models.Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        # Verificar que el negocio pertenece al usuario
        negocio = db.query(models.Negocio).filter(
            models.Negocio.id == data.negocio_id,
            models.Negocio.usuario_id == user.id
        ).first()
        if not negocio:
            raise HTTPException(status_code=403, detail="Negocio no encontrado o no autorizado")
        
        # Generar número de licencia peruano (formato municipal)
        import uuid
        year = datetime.now().year
        correlativo = str(uuid.uuid4().int)[:5]
        numero = f"LIC-{year}-{correlativo}"
        
        fecha_emision = datetime.now(timezone.utc)
        # Licencia provisional: 1 año / Definitiva: 5 años (normativa peruana)
        if data.tipo_licencia == models.TipoLicencia.provisional:
            fecha_vencimiento = fecha_emision + timedelta(days=365)
        else:
            fecha_vencimiento = fecha_emision + timedelta(days=365*5)
        
        nueva_licencia = models.Licencia(
            negocio_id=data.negocio_id,
            numero_licencia=numero,
            tipo_licencia=data.tipo_licencia,
            estado=models.EstadoLicencia.vigente,
            fecha_emision=fecha_emision,
            fecha_vencimiento=fecha_vencimiento,
            entidad_emisora=data.entidad_emisora
        )
        db.add(nueva_licencia)
        db.commit()
        db.refresh(nueva_licencia)
        return nueva_licencia
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

# --- TRABAJADORES ---
@app.get("/api/trabajadores", response_model=list[schemas.TrabajadorResponse])
def listar_trabajadores(user: models.Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    negocio_ids = [n.id for n in db.query(models.Negocio).filter(models.Negocio.usuario_id == user.id).all()]
    if not negocio_ids:
        return []
    return db.query(models.Trabajador).filter(
        models.Trabajador.negocio_id.in_(negocio_ids),
        models.Trabajador.estado == models.EstadoTrabajador.activo
    ).all()

@app.post("/api/trabajadores", response_model=schemas.TrabajadorResponse, status_code=201)
def agregar_trabajador(data: schemas.TrabajadorCreate, user: models.Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        negocio = db.query(models.Negocio).filter(
            models.Negocio.id == data.negocio_id,
            models.Negocio.usuario_id == user.id
        ).first()
        if not negocio:
            raise HTTPException(status_code=403, detail="Negocio no encontrado o no autorizado")
        
        # Verificar DNI duplicado en el mismo negocio
        existe = db.query(models.Trabajador).filter(
            models.Trabajador.negocio_id == data.negocio_id,
            models.Trabajador.dni == data.dni,
            models.Trabajador.estado == models.EstadoTrabajador.activo
        ).first()
        if existe:
            raise HTTPException(status_code=400, detail="Ya existe un trabajador activo con ese DNI en este negocio")
        
        nuevo = models.Trabajador(
            negocio_id=data.negocio_id,
            dni=data.dni,
            nombre_completo=data.nombre_completo,
            cargo=data.cargo,
            fecha_ingreso=datetime.now(timezone.utc),
            estado=models.EstadoTrabajador.activo
        )
        db.add(nuevo)
        db.commit()
        db.refresh(nuevo)
        return nuevo
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.delete("/api/trabajadores/{trabajador_id}")
def eliminar_trabajador(trabajador_id: int, user: models.Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    trabajador = db.query(models.Trabajador).filter(models.Trabajador.id == trabajador_id).first()
    if not trabajador:
        raise HTTPException(status_code=404, detail="Trabajador no encontrado")
    
    negocio = db.query(models.Negocio).filter(
        models.Negocio.id == trabajador.negocio_id,
        models.Negocio.usuario_id == user.id
    ).first()
    if not negocio:
        raise HTTPException(status_code=403, detail="No autorizado")
    
    trabajador.estado = models.EstadoTrabajador.inactivo
    trabajador.fecha_salida = datetime.now(timezone.utc)
    db.commit()
    return {"message": "Trabajador desactivado"}

# --- SOLICITUD DE RENOVACIÓN ---
@app.post("/api/solicitudes/renovacion", response_model=schemas.SolicitudRenovacionResponse, status_code=201)
def solicitar_renovacion(data: schemas.SolicitudRenovacionCreate, user: models.Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        negocio = db.query(models.Negocio).filter(
            models.Negocio.id == data.negocio_id,
            models.Negocio.usuario_id == user.id
        ).first()
        if not negocio:
            raise HTTPException(status_code=403, detail="Negocio no autorizado")
        
        licencia = db.query(models.Licencia).filter(
            models.Licencia.id == data.licencia_id,
            models.Licencia.negocio_id == data.negocio_id
        ).first()
        if not licencia:
            raise HTTPException(status_code=404, detail="Licencia no encontrada")
        
        # Verificar que no haya solicitud pendiente
        pendiente = db.query(models.SolicitudRenovacion).filter(
            models.SolicitudRenovacion.licencia_id == data.licencia_id,
            models.SolicitudRenovacion.estado == models.EstadoSolicitud.pendiente
        ).first()
        if pendiente:
            raise HTTPException(status_code=400, detail="Ya existe una solicitud de renovación pendiente")
        
        solicitud = models.SolicitudRenovacion(
            licencia_id=data.licencia_id,
            negocio_id=data.negocio_id,
            estado=models.EstadoSolicitud.pendiente,
            motivo=data.motivo
        )
        db.add(solicitud)
        db.commit()
        db.refresh(solicitud)
        return solicitud
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

# --- MI NEGOCIO (datos propios) ---
@app.get("/api/mi-negocio")
def mi_negocio(user: models.Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    negocio = db.query(models.Negocio).filter(models.Negocio.usuario_id == user.id).first()
    if not negocio:
        raise HTTPException(status_code=404, detail="No tienes un negocio registrado")
    return {
        "id": negocio.id,
        "nombre_negocio": negocio.nombre_negocio,
        "tipo": negocio.tipo.value,
        "rubro": negocio.rubro,
        "referencia_ubicacion": negocio.referencia_ubicacion,
        "galeria_nombre": negocio.galeria_nombre,
        "stand_numero": negocio.stand_numero,
        "estado": negocio.estado.value
    }
