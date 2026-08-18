from fastapi import FastAPI, HTTPException, status, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, field_validator
import sqlite3
import re
from datetime import datetime
from typing import Optional, List

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
    return templates.TemplateResponse("index.html", {"request": request})


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