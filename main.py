from fastapi import FastAPI, HTTPException, status, Request, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, field_validator
import sqlite3
import re
from datetime import datetime
from typing import Optional, List
import csv
import io

app = FastAPI(title="API Laboratorio de Software", version="1.0.0")
DB_NAME = "laboratorio.db"

# Configuración de archivos estáticos y plantillas
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# --- UTILIDAD DE BASE DE DATOS ---
def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

# --- INICIALIZACIÓN DE TABLAS ---
def init_db():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alumnos (
                matricula TEXT PRIMARY KEY,
                nombre TEXT NOT NULL,
                carrera TEXT DEFAULT 'Ingeniería de Software',
                activo INTEGER DEFAULT 1
            );
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS registros_acceso (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                matricula TEXT NOT NULL,
                fecha TEXT NOT NULL,
                hora_entrada TEXT NOT NULL,
                hora_salida TEXT,
                FOREIGN KEY (matricula) REFERENCES alumnos (matricula)
            );
        """)
        conn.commit()

init_db()

# --- MODELOS PYDANTIC ---
class AlumnoBase(BaseModel):
    matricula: str
    nombre: str
    carrera: Optional[str] = "Ingeniería de Software"

    @field_validator("matricula")
    def validar_formato_plantel(cls, v):
        patron = r'^\d{2}-003-\d{4}$'
        if not re.match(patron, v):
            raise ValueError("La matrícula debe pertenecer al plantel 003 y tener formato xx-003-xxxx")
        return v

class RegistroAccesoRequest(BaseModel):
    matricula: str

# --- ENDPOINTS ---

# Ruta principal para cargar la página web
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    # Aquí está la corrección:
    return templates.TemplateResponse(request=request, name="index.html")

@app.get("/api/alumnos/buscar")
def buscar_alumnos(q: str = ""):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        query = """
            SELECT a.matricula, a.nombre, a.carrera,
                   CASE WHEN r.id IS NOT NULL THEN 'Dentro' ELSE 'Fuera' END as estado,
                   r.hora_entrada
            FROM alumnos a
            LEFT JOIN registros_acceso r ON a.matricula = r.matricula 
                 AND r.fecha = ? AND r.hora_salida IS NULL
            WHERE (a.matricula LIKE ? OR a.nombre LIKE ?) AND a.activo = 1
        """
        hoy = datetime.now().strftime("%Y-%m-%d")
        termino = f"%{q}%"
        cursor.execute(query, (hoy, termino, termino))
        resultados = [dict(row) for row in cursor.fetchall()]
        return resultados

@app.post("/api/accesos/registrar")
def registrar_acceso(payload: RegistroAccesoRequest):
    patron = r'^\d{2}-003-\d{4}$'
    if not re.match(patron, payload.matricula):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Matrícula no válida para el plantel 003."
        )

    ahora = datetime.now()
    fecha_hoy = ahora.strftime("%Y-%m-%d")
    hora_actual = ahora.strftime("%H:%M:%S")

    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Verificar si el alumno existe y está activo
        cursor.execute("SELECT matricula, nombre FROM alumnos WHERE matricula = ? AND activo = 1", (payload.matricula,))
        alumno = cursor.fetchone()
        if not alumno:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Alumno no autorizado o no registrado en la carrera."
            )

        # 2. Revisar si tiene una sesión abierta hoy (está dentro)
        cursor.execute("""
            SELECT id FROM registros_acceso 
            WHERE matricula = ? AND fecha = ? AND hora_salida IS NULL
        """, (payload.matricula, fecha_hoy))
        registro_activo = cursor.fetchone()

        if registro_activo:
            # Marcar salida
            cursor.execute("""
                UPDATE registros_acceso SET hora_salida = ? WHERE id = ?
            """, (hora_actual, registro_activo["id"]))
            conn.commit()
            return {"mensaje": f"Salida registrada para {alumno['nombre']}", "estado": "Fuera", "hora": hora_actual}
        else:
            # Marcar entrada
            cursor.execute("""
                INSERT INTO registros_acceso (matricula, fecha, hora_entrada) 
                VALUES (?, ?, ?)
            """, (payload.matricula, fecha_hoy, hora_actual))
            conn.commit()
            return {"mensaje": f"Entrada registrada para {alumno['nombre']}", "estado": "Dentro", "hora": hora_actual}

@app.post("/api/admin/alumnos", status_code=status.HTTP_201_CREATED)
def agregar_alumno(alumno: AlumnoBase):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO alumnos (matricula, nombre, carrera) 
                VALUES (?, ?, ?)
            """, (alumno.matricula, alumno.nombre, alumno.carrera))
            conn.commit()
            return {"mensaje": f"Alumno {alumno.nombre} agregado exitosamente"}
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=400, detail="La matrícula ya se encuentra registrada.")


# --- MÓDULO DE ADMINISTRADOR ---

class LoginRequest(BaseModel):
    password: str

@app.post("/api/admin/login")
def admin_login(payload: LoginRequest):
    """
    Verifica la contraseña del administrador.
    """
    # Contraseña por defecto para el laboratorio (puedes cambiarla después)
    if payload.password == "lab004admin":
        return {"mensaje": "Acceso autorizado"}
    raise HTTPException(status_code=401, detail="Contraseña incorrecta")

@app.post("/api/admin/importar-csv")
async def importar_csv(archivo: UploadFile = File(...)):
    """
    Recibe un archivo CSV, lee línea por línea y registra a los alumnos válidos.
    Ignora duplicados y matrículas que no sean del plantel 003.
    """
    if not archivo.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="El archivo debe tener extensión .csv")
    
    contenido = await archivo.read()
    texto = contenido.decode("utf-8-sig") # utf-8-sig evita problemas con caracteres especiales y BOM de Excel
    lector = csv.DictReader(io.StringIO(texto))
    
    agregados = 0
    omitidos = 0
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        for fila in lector:
            # Aseguramos de leer las columnas correctas sin espacios extra
            matricula = fila.get("matricula", "").strip()
            nombre = fila.get("nombre", "").strip()
            
            # Validar la regla de negocio del plantel 003
            if re.match(r'^\d{2}-003-\d{4}$', matricula) and nombre:
                try:
                    cursor.execute("""
                        INSERT INTO alumnos (matricula, nombre, carrera) 
                        VALUES (?, ?, 'Ingeniería de Software')
                    """, (matricula, nombre))
                    agregados += 1
                except sqlite3.IntegrityError:
                    # Si la matrícula ya existe, la contamos como omitida
                    omitidos += 1
            else:
                omitidos += 1
                
        conn.commit()
        
    return {"mensaje": f"Importación completa: {agregados} registrados, {omitidos} omitidos (duplicados/inválidos)."}