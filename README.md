
# Sistema de Acceso - Laboratorio de Software (Plantel San Lorenzo Tezonco)
# Contraseña del sistema: lab004admin
Este proyecto es una plataforma web local desarrollada para gestionar, controlar y registrar el acceso de los alumnos de Ingeniería de Software al laboratorio. Fue creado como proyecto de servicio social y está diseñado para ser heredado, mantenido y escalado por futuras generaciones.

## Características Principales
* **Búsqueda en tiempo real:** Filtrado de alumnos autorizados por nombre o matrícula.
* **Control de Accesos:** Registro exacto de hora de entrada y salida mediante base de datos local (SQLite).
* **Validación Estricta:** Bloqueo de matrículas ajenas a la estructura `xx-003-xxxx`.
* **Panel de Administración:** Gestión de usuarios, alta de alumnos e importación de listas.

## Stack Tecnológico
* **Backend:** Python 3.x con FastAPI (Framework asíncrono y de alto rendimiento).
* **Frontend:** HTML5, CSS puro / Tailwind (por definir) y JavaScript (Vanilla).
* **Base de Datos:** SQLite (No requiere instalación de servidor externo).

## Instalación y Despliegue Local (Para Desarrolladores)

1. **Clonar el repositorio**
   ```bash
   git clone https://github.com/OscarEscoHdz/Sistema-de-acceso-lab-A-004.git
   cd "Sistema de acceso a lab 004 - Web"
   
2. **Crear un entorno virtual
    python -m venv venv

   **En Windows:
     venv\Scripts\activate

    ** En Linux/Kubuntu:
     source venv/bin/activate

 **Instalar dependecias
   pip install -r requirements.txt

# Iniciar el servidor
uvicorn main:app --reload

## Módulo de Escáner por Webcam (Visión por Computadora)

El sistema incluye un script independiente en Python que utiliza la cámara web para leer códigos QR de las credenciales y registrar automáticamente los accesos en el backend.

## **Dependencias requeridas:**
```bash
pip install opencv-python pyzbar requests numpy qrcode[pil]


## Activar el entorno virtual
.\venv\Scripts\activate

##Iniciar servidor web y base de datos
uvicorn main:app --reload

##Direccion
[http://127.0.0.1:8000](http://127.0.0.1:8000)

##Iniciar camara
python escaner.py