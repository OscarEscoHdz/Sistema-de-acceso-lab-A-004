import cv2
from pyzbar.pyzbar import decode
import requests
import time
import winsound
import numpy as np

# URL de la API local
API_URL = "http://127.0.0.1:8000/api/accesos/registrar"

def procesar_codigo(matricula):
    """
    Envía la matrícula escaneada a la API para registrar el acceso.
    """
    try:
        respuesta = requests.post(API_URL, json={"matricula": matricula})
        
        if respuesta.status_code == 200:
            datos = respuesta.json()
            print(f"✅ Éxito: {datos['mensaje']}")
            # Emitir un pitido agudo (frecuencia, duración en ms)
            winsound.Beep(1000, 300) 
        else:
            error_msg = respuesta.json().get('detail', 'Error desconocido')
            print(f"❌ Error: {error_msg}")
            # Emitir un pitido grave de error
            winsound.Beep(400, 500)
    except requests.exceptions.RequestException as e:
         print(f"⚠️ Error de conexión con el servidor: {e}")

def iniciar_escaner():
    """
    Inicia la cámara web y decodifica códigos de barras/QR en tiempo real.
    """
    print("Iniciando escáner de credenciales...")
    # 0 suele ser la cámara web integrada
    cap = cv2.VideoCapture(0)
    
    # Tiempo de espera para no saturar el servidor con lecturas continuas del mismo código
    ultimo_escaneo = 0
    tiempo_espera = 3  # segundos

    while True:
        # Capturar frame a frame
        ret, frame = cap.read()
        
        if not ret:
            print("No se pudo acceder a la cámara.")
            break

        # Decodificar códigos en el frame actual
        codigos = decode(frame)
        
        for codigo in codigos:
            # Extraer el texto del código y dibujar un rectángulo
            texto = codigo.data.decode('utf-8')
            
            # Convertir los puntos a un arreglo de NumPy que OpenCV entienda
            if codigo.polygon:
                pts = np.array([[p.x, p.y] for p in codigo.polygon], np.int32)
                cv2.polylines(frame, [pts], True, (0, 255, 0), 3)
            
            # Solo procesar si ha pasado el tiempo de espera desde el último escaneo
            tiempo_actual = time.time()
            if tiempo_actual - ultimo_escaneo > tiempo_espera:
                print(f"\nCódigo detectado: {texto}")
                procesar_codigo(texto)
                ultimo_escaneo = tiempo_actual

        # Mostrar la ventana de video
        cv2.imshow('Escáner de Credenciales - Presiona "q" para salir', frame)

        # Salir del bucle si se presiona la tecla 'q'
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Liberar recursos
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    iniciar_escaner()