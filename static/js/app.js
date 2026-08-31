/**
 * app.js - Lógica del Frontend para el Control de Acceso
 * Maneja la búsqueda en tiempo real y la comunicación con el backend (FastAPI).
 */

const buscadorInput = document.getElementById('buscador');
const tablaResultados = document.getElementById('tabla-resultados');

/**
 * Escucha el evento de escritura en la barra de búsqueda.
 * Realiza una petición GET a la API y actualiza la tabla de resultados.
 */
buscadorInput.addEventListener('input', async (e) => {
    const query = e.target.value.trim();
    
    // Si el buscador está vacío, limpiar la tabla
    if (query.length === 0) {
        tablaResultados.innerHTML = `
            <tr>
                <td colspan="4" class="p-8 text-center text-gray-500 text-lg">
                    Esperando búsqueda... Ingresa una matrícula o nombre arriba.
                </td>
            </tr>`;
        return;
    }

    try {
        // Petición al endpoint de búsqueda de FastAPI
        const response = await fetch(`/api/alumnos/buscar?q=${query}`);
        const alumnos = await response.json();
        renderizarTabla(alumnos);
    } catch (error) {
        console.error("Error al buscar alumnos:", error);
    }
});

/**
 * Dibuja las filas en la tabla HTML basándose en los datos recibidos del servidor.
 * 
 * @param {Array} alumnos - Lista de objetos de alumnos devuelta por la API.
 */
function renderizarTabla(alumnos) {
    tablaResultados.innerHTML = ''; // Limpiar la tabla antes de inyectar datos

    if (alumnos.length === 0) {
        tablaResultados.innerHTML = `
            <tr>
                <td colspan="4" class="p-4 text-center text-red-500 font-semibold">
                    No se encontraron alumnos registrados con esos datos.
                </td>
            </tr>`;
        return;
    }

    alumnos.forEach(alumno => {
        // Cambiar colores dependiendo de si el alumno está Dentro o Fuera
        const estadoColor = alumno.estado === 'Dentro' ? 'text-green-700 bg-green-100' : 'text-gray-600 bg-gray-100';
        const horaTexto = alumno.estado === 'Dentro' ? `<br><span class="text-xs text-gray-500 font-normal">Ingreso: ${alumno.hora_entrada}</span>` : '';

        const fila = document.createElement('tr');
        fila.className = 'border-b hover:bg-gray-50 transition';
        fila.innerHTML = `
            <td class="p-4 font-mono text-gray-700">${alumno.matricula}</td>
            <td class="p-4 font-semibold text-gray-800">${alumno.nombre}</td>
            <td class="p-4 text-center">
                <span class="px-3 py-1 rounded-full text-sm font-bold ${estadoColor}">
                    ${alumno.estado}
                </span>
                ${horaTexto}
            </td>
            <td class="p-4 text-center">
                <button onclick="registrarAcceso('${alumno.matricula}')" 
                        class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded shadow transition font-semibold">
                    Cambiar Estado
                </button>
            </td>
        `;
        tablaResultados.appendChild(fila);
    });
}

/**
 * Envía una petición POST al servidor para registrar la entrada o salida de un alumno.
 * Actualiza la tabla visualmente si el registro es exitoso.
 * 
 * @param {string} matricula - La matrícula del alumno a registrar (Formato xx-003-xxxx).
 */
async function registrarAcceso(matricula) {
    try {
        const response = await fetch('/api/accesos/registrar', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ matricula: matricula })
        });

        const resultado = await response.json();

        if (response.ok) {
            // Si el acceso se registró, volvemos a disparar la búsqueda para que la tabla se actualice sola
            const query = buscadorInput.value;
            const res = await fetch(`/api/alumnos/buscar?q=${query}`);
            const alumnos = await res.json();
            renderizarTabla(alumnos);
        } else {
            alert(`Acceso Denegado: ${resultado.detail}`);
        }
    } catch (error) {
        console.error("Error al registrar acceso:", error);
        alert("Ocurrió un error al comunicarse con la base de datos.");
    }
}

// ==========================================
// MÓDULO DE ADMINISTRADOR
// ==========================================

const btnAdmin = document.getElementById('btn-admin');
const modalLogin = document.getElementById('modal-login');
const modalAdmin = document.getElementById('modal-admin');

// Abrir modal de login al hacer clic en "Acceso Admin"
btnAdmin.addEventListener('click', () => {
    modalLogin.classList.remove('hidden');
    document.getElementById('input-password').value = ''; // Limpiar campo
});

/**
 * Cierra cualquier modal indicando su ID.
 * @param {string} modalId - El ID del modal a cerrar.
 */
function cerrarModal(modalId) {
    document.getElementById(modalId).classList.add('hidden');
}

/**
 * Verifica la contraseña ingresada haciendo una petición al backend.
 * Si es correcta, oculta el login y muestra el panel de control.
 */
async function verificarPassword() {
    const password = document.getElementById('input-password').value;
    
    try {
        const response = await fetch('/api/admin/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ password: password })
        });

        if (response.ok) {
            cerrarModal('modal-login');
            modalAdmin.classList.remove('hidden');
        } else {
            alert("Contraseña incorrecta. Acceso denegado.");
        }
    } catch (error) {
        console.error("Error al verificar contraseña:", error);
        alert("Error de conexión con el servidor.");
    }
}

/**
 * Envía los datos de un alumno nuevo capturados manualmente al servidor.
 */
async function agregarAlumnoManual() {
    const matInput = document.getElementById('admin-mat');
    const nomInput = document.getElementById('admin-nom');
    
    const matricula = matInput.value.trim();
    const nombre = nomInput.value.trim();

    if (!matricula || !nombre) {
        alert("Por favor llena ambos campos.");
        return;
    }

    try {
        const response = await fetch('/api/admin/alumnos', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ matricula: matricula, nombre: nombre, carrera: "Ingeniería de Software" })
        });

        const resultado = await response.json();

        if (response.ok) {
            alert(resultado.mensaje);
            matInput.value = ''; // Limpiar campos
            nomInput.value = '';
        } else {
            // Extraer el mensaje dependiendo de si es un string o un arreglo de validación de FastAPI
            let mensajeError = resultado.detail;
            if (Array.isArray(mensajeError)) {
                mensajeError = mensajeError[0].msg; 
            }
            alert(`Error: ${mensajeError}`);
        }
    } catch (error) {
        console.error("Error al agregar alumno:", error);
    }
}

/**
 * Lee el archivo CSV seleccionado y lo envía al servidor usando FormData.
 */
async function subirCSV() {
    const fileInput = document.getElementById('archivo-csv');
    
    if (fileInput.files.length === 0) {
        alert("Por favor selecciona un archivo .csv primero.");
        return;
    }

    const formData = new FormData();
    formData.append("archivo", fileInput.files[0]);

    try {
        const response = await fetch('/api/admin/importar-csv', {
            method: 'POST',
            body: formData // No enviamos 'Content-Type', fetch lo configura automáticamente con FormData
        });

        const resultado = await response.json();

        if (response.ok) {
            alert(resultado.mensaje);
            fileInput.value = ''; // Limpiar el input file
        } else {
            alert(`Error: ${resultado.detail}`);
        }
    } catch (error) {
        console.error("Error al subir archivo:", error);
        alert("Ocurrió un error al enviar el archivo al servidor.");
    }
}