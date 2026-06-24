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
    # En Railway es mejor usar Alembic para migraciones, pero para simplificar
    # la primera inicialización podemos usar create_all.
    models.Base.metadata.create_all(bind=engine)
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

# --- RUTAS DE AUTENTICACIÓN ---
@app.post("/api/auth/register", response_model=schemas.UsuarioResponse, status_code=status.HTTP_201_CREATED)
def register_user(user: schemas.UsuarioCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.Usuario).filter(models.Usuario.correo == user.correo).first()
    if db_user:
        raise HTTPException(status_code=400, detail="El correo ya está registrado")
    
    hashed_password = security.get_password_hash(user.password)
    new_user = models.Usuario(
        dni=user.dni,
        ruc=user.ruc,
        nombre_completo=user.nombre_completo,
        celular=user.celular,
        correo=user.correo,
        password_hash=hashed_password,
        rol=user.rol
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/api/auth/login")
def login(user_credentials: schemas.UsuarioCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.Usuario).filter(models.Usuario.correo == user_credentials.correo).first()
    if not db_user or not security.verify_password(user_credentials.password, db_user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales incorrectas")
    
    access_token = security.create_access_token(data={"sub": str(db_user.id)})
    refresh_token = security.create_refresh_token(data={"sub": str(db_user.id)})
    
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

# --- RUTAS MOCK SUNAT/RENIEC ---
@app.get("/api/mock/sunat/{ruc}")
def mock_sunat(ruc: str):
    """Simulación de la API de SUNAT para DevSecOps."""
    if len(ruc) != 11:
        raise HTTPException(status_code=400, detail="RUC inválido")
    return {
        "ruc": ruc,
        "razon_social": "NEGOCIO DE PRUEBA E.I.R.L",
        "estado": "ACTIVO",
        "condicion": "HABIDO"
    }

@app.get("/api/mock/reniec/{dni}")
def mock_reniec(dni: str):
    """Simulación de la API de RENIEC."""
    if len(dni) != 8:
        raise HTTPException(status_code=400, detail="DNI inválido")
    return {
        "dni": dni,
        "nombres": "JUAN PEREZ",
        "apellido_paterno": "MARTINEZ",
        "apellido_materno": "GARCIA"
    }

# --- RUTAS DE PRUEBA DE CONEXIÓN FRONTEND (TEMPORALES) ---
@app.post("/api/vendedores")
def test_vendedores_connection(data: dict):
    """
    Ruta temporal para verificar que Vercel se comunica con Railway.
    El frontend generado por Lovable hace POST a /vendedores.
    """
    return {"message": "¡Conexión exitosa desde Vercel a Railway!", "data_recibida": data}
