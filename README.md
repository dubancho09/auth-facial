# OCR - Sistema de Registro y Autenticacion Facial

Este proyecto usa Flask + InsightFace para registrar usuarios y autenticarlos por rostro desde streaming de camara.

## Requisitos

- macOS
- Python 3.9+
- Docker Desktop (para PostgreSQL y despliegue por Compose)
- Camara web habilitada

## Variables de entorno

1. Copia el archivo de ejemplo:

```bash
cp .env.example .env
```

2. Edita credenciales si lo necesitas:

```env
DB_ENGINE=postgres
DB_HOST=localhost
DB_PORT=5432
DB_NAME=ocr
DB_USER=ocr_user
DB_PASSWORD=ocr_password
```

Nota: Si defines DATABASE_URL, esa variable tiene prioridad sobre DB_ENGINE y DB_*. 

## Opcion A: Ejecutar con Docker Compose (recomendado)

Desde la carpeta del proyecto:

```bash
docker compose --env-file .env up -d --build
```

Para ver logs:

```bash
docker compose logs -f web
```

Aplicacion:

- http://127.0.0.1:5000

Detener servicios:

```bash
docker compose down
```

Detener y borrar volumen de PostgreSQL:

```bash
docker compose down -v
```

## Opcion B: Ejecutar local con entorno virtual + PostgreSQL

### 1. Entrar al proyecto

```bash
cd /Users/areamovil/Desktop/ocr
```

### 2. Crear entorno virtual

```bash
python3 -m venv venv
```

### 3. Activar entorno virtual

```bash
source venv/bin/activate
```

### 4. Instalar dependencias

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 5. Exportar variables de entorno

```bash
export DB_ENGINE=postgres
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=ocr
export DB_USER=ocr_user
export DB_PASSWORD=ocr_password
```

### 6. Ejecutar la aplicacion

```bash
python app.py
```

Aplicacion:

- http://127.0.0.1:5000

## Uso basico

1. Abre http://127.0.0.1:5000
2. Permite acceso a la camara
3. En Registrar:
    - Ingresa nombre y documento
    - Pulsa Iniciar registro por streaming
4. En Autenticar:
    - Pulsa Iniciar autenticacion

## Panel admin con login por API key

El sistema incluye un panel para gestionar usuarios con CRUD (crear, listar, editar, eliminar), protegido por login de API key en sesion.

### 1. Primer acceso (bootstrap)

En tu `.env` agrega:

```env
ADMIN_PANEL_API_KEY=tu-api-key-admin-segura
```

Esta key funciona como respaldo para el primer acceso.

### 2. Crear API keys seguras desde backend

Una vez dentro del panel, crea API keys desde backend usando:

- `POST /admin/api/apikeys`

Payload ejemplo (misma key para admin y plugin):

```json
{
   "name": "admin-plugin-main",
   "scopes": ["admin:login", "plugin:token"],
   "client_id": "erp_portal",
   "expires_in_days": 365
}
```

La respuesta devuelve `api_key` una sola vez (guardala de forma segura).

Scopes disponibles:

- `admin:login` para entrar al panel `/admin/login`
- `plugin:token` para consumir `/api/plugin/token`

Endpoints de gestion:

- `GET /admin/api/apikeys` lista metadata de keys (sin secreto).
- `POST /admin/api/apikeys/<id>/revoke` revoca una key.

### 2.1 Invalidar la API key bootstrap de `.env` (despues del primer uso)

Recomendado: una vez creada al menos una API key administrada por backend, invalida la key legacy de entorno.

Pasos:

1. Crea una API key nueva con scope `admin:login`.
2. Verifica que puedes entrar al panel con la nueva key.
3. Edita `.env` y elimina `ADMIN_PANEL_API_KEY` o cambiala por un valor aleatorio no usado.
4. Reinicia servicios para aplicar el cambio.

Con Docker Compose:

```bash
docker compose --env-file .env up -d --force-recreate
```

Nota:

- Mientras `ADMIN_PANEL_API_KEY` tenga un valor valido, el fallback legacy seguira aceptandolo.

### 3. Abrir login de panel

- http://127.0.0.1:5000/admin/login

### 4. Funcionalidades del panel

- Crear usuario: captura frame facial desde camara + nombre + documento.
- Listar usuarios registrados.
- Editar nombre y documento.
- Eliminar usuario.

Nota: El alta desde panel reutiliza la misma validacion biometrica del registro facial principal.

## Plugin popup para otra aplicacion

El proyecto incluye un SDK frontend para abrir el plugin en una ventana y recibir la autenticacion.

Archivo SDK:

- /static/face-auth-plugin.js

### Seguridad del plugin (obligatoria)

Para evitar que cualquier aplicacion use el plugin, ahora el modo plugin exige token de lanzamiento firmado y con expiracion.

Configura seguridad del plugin:

```env
PLUGIN_SECURITY_ENABLED=1
PLUGIN_TOKEN_TTL_SECONDS=120
# Legado opcional (fallback):
PLUGIN_CLIENTS=erp_portal:erp-secret-key
```

Recomendado: usar API keys creadas por backend con scope `plugin:token` en lugar de `PLUGIN_CLIENTS`.

Flujo seguro:

1. Tu backend pide token a POST /api/plugin/token enviando client_id, origin y header X-Plugin-Api-Key.
2. El backend de plugin responde token temporal.
3. Tu frontend abre popup con FaceAuthPlugin.open usando launchToken.
4. El plugin valida token y solo envia resultados al origin incluido en ese token.

### Integracion minima en otra app web

Primero, tu backend debe pedir el token (ejemplo pseudo-codigo):

```js
// Backend de tu aplicacion, no en browser.
const response = await fetch("http://127.0.0.1:5000/api/plugin/token", {
   method: "POST",
   headers: {
      "Content-Type": "application/json",
      "X-Plugin-Api-Key": process.env.FACE_PLUGIN_API_KEY
   },
   body: JSON.stringify({
      client_id: "erp_portal",
      origin: "https://tu-app.com"
   })
});

const { data } = await response.json();
return data.token;
```

Luego, en frontend, abres el popup con ese token:

```html
<script src="http://127.0.0.1:5000/static/face-auth-plugin.js"></script>
<button id="btnFaceLogin">Login facial</button>

<script>
   document.getElementById("btnFaceLogin").addEventListener("click", async () => {
      try {
         // launchToken llega desde tu backend (nunca hardcodear api keys en frontend)
         const launchToken = await fetch("/api/mi-backend/plugin-launch-token").then(r => r.text());

         const result = await window.FaceAuthPlugin.open({
            pluginUrl: "http://127.0.0.1:5000/",
            launchToken,
            expectedOrigin: "http://127.0.0.1:5000"
         });

         console.log("Usuario autenticado:", result.user);
      } catch (error) {
         console.error("No se pudo autenticar:", error.message);
      }
   });
</script>
```

Como funciona:

1. Tu app abre un popup con el plugin.
2. El usuario se autentica por rostro en el popup.
3. El plugin valida token y origen permitido.
4. El plugin envia el resultado a la ventana padre con postMessage.
5. El SDK resuelve la promesa con los datos del usuario autenticado.

## Solucion de problemas

### command not found: python
Usa python3 para crear el entorno virtual y python despues de activarlo.

### InsightFace no detecta GPU
El proyecto tiene fallback automatico a CPU.

### Puerto 5000 ocupado
Cambia APP_PORT por variable de entorno o libera el puerto.
