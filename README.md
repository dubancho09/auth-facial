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

## Opcion A.1: Docker Compose para produccion (sin base de datos local)

Usa este modo cuando la base de datos PostgreSQL esta fuera de Compose (por ejemplo, RDS, Cloud SQL o un servidor dedicado).

1. Asegura en tu `.env` las variables de conexion a la base externa (`DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` o `DATABASE_URL`).
2. Levanta solo la app web:

```bash
docker compose -f docker-compose.prod.yml --env-file .env up -d --build
```

Ver logs:

```bash
docker compose -f docker-compose.prod.yml logs -f web
```

Detener:

```bash
docker compose -f docker-compose.prod.yml down
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
      let preopenedPopup = null;

      try {
         // Preabre popup en el click del usuario para evitar que el navegador lo abra como pestaña.
         preopenedPopup = window.FaceAuthPlugin.preopenPopup({
            width: 920,
            height: 760
         });

         // launchToken llega desde tu backend (nunca hardcodear api keys en frontend)
         const launchToken = await fetch("/api/mi-backend/plugin-launch-token").then(r => r.text());

         const result = await window.FaceAuthPlugin.open({
            pluginUrl: "http://127.0.0.1:5000/",
            launchToken,
            expectedOrigin: "http://127.0.0.1:5000",
            preopenedPopup,
            debug: true
         });

         console.log("Usuario autenticado:", result.user);
      } catch (error) {
         if (preopenedPopup && !preopenedPopup.closed) {
            preopenedPopup.close();
         }

         console.error("No se pudo autenticar:", error.message);
      }
   });
</script>
```

### Integracion embebida (dentro de tu pantalla)

Si quieres abrir el flujo facial dentro de la misma pantalla (por ejemplo en la vista de registrar asistencia), usa `mode: "embed"` y un contenedor:

```html
<script src="http://127.0.0.1:5000/static/face-auth-plugin.js"></script>
<button id="btnFaceLogin">Registrar asistencia</button>
<div id="faceAuthContainer"></div>

<script>
   document.getElementById("btnFaceLogin").addEventListener("click", async () => {
      try {
         const launchToken = await fetch("/api/mi-backend/plugin-launch-token").then(r => r.text());

         const result = await window.FaceAuthPlugin.open({
            pluginUrl: "http://127.0.0.1:5000/",
            launchToken,
            expectedOrigin: "http://127.0.0.1:5000",
            mode: "embed",
            container: "#faceAuthContainer",
            height: 760
         });

         if (result && result.cancelled) {
            console.log("Usuario cerro el flujo facial.");
            return;
         }

         console.log("Usuario autenticado:", result.user);
      } catch (error) {
         console.error("No se pudo autenticar:", error.message);
      }
   });
</script>
```

Nota: al cerrar manualmente el flujo, el SDK ahora devuelve `{ cancelled: true }` por defecto en lugar de lanzar error. Si prefieres comportamiento estricto, usa `rejectOnClose: true`.

Como funciona:

1. Tu app abre un popup con el plugin.
2. El usuario se autentica por rostro en el popup.
3. El plugin valida token y origen permitido.
4. El plugin envia el resultado a la ventana padre con postMessage.
5. El SDK resuelve la promesa con los datos del usuario autenticado.

## Integracion con Spring Boot MVC + Thymeleaf

Esta seccion documenta una implementacion de referencia para integrar el plugin facial en una app Java con Spring Boot MVC y Thymeleaf.

Arquitectura recomendada:

1. Tu frontend (Thymeleaf) nunca crea ni firma tokens.
2. Tu backend Spring solicita el launch token al servidor del plugin.
3. Tu frontend llama a un endpoint interno de Spring para obtener ese token.
4. Tu frontend abre el popup con FaceAuthPlugin y recibe el resultado de autenticacion.

### 1) Configuracion en application.yml

```yaml
face-plugin:
   base-url: http://127.0.0.1:5000
   token-endpoint: /api/plugin/token
   client-id: erp_portal
   api-key: ${FACE_PLUGIN_API_KEY}
   opener-origin: ${APP_PUBLIC_ORIGIN:http://localhost:8080}
```

### 2) Properties class

```java
package com.example.demo.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "face-plugin")
public class FacePluginProperties {
      private String baseUrl;
      private String tokenEndpoint;
      private String clientId;
      private String apiKey;
      private String openerOrigin;

      public String getBaseUrl() { return baseUrl; }
      public void setBaseUrl(String baseUrl) { this.baseUrl = baseUrl; }

      public String getTokenEndpoint() { return tokenEndpoint; }
      public void setTokenEndpoint(String tokenEndpoint) { this.tokenEndpoint = tokenEndpoint; }

      public String getClientId() { return clientId; }
      public void setClientId(String clientId) { this.clientId = clientId; }

      public String getApiKey() { return apiKey; }
      public void setApiKey(String apiKey) { this.apiKey = apiKey; }

      public String getOpenerOrigin() { return openerOrigin; }
      public void setOpenerOrigin(String openerOrigin) { this.openerOrigin = openerOrigin; }
}
```

Registra la clase en tu aplicacion:

```java
@SpringBootApplication
@EnableConfigurationProperties(FacePluginProperties.class)
public class DemoApplication {
      public static void main(String[] args) {
            SpringApplication.run(DemoApplication.class, args);
      }
}
```

### 3) Cliente de infraestructura para pedir launch token

```java
package com.example.demo.plugin;

import com.example.demo.config.FacePluginProperties;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

import java.util.Map;

@Component
public class FacePluginTokenClient {

      private final FacePluginProperties props;
      private final RestClient restClient;

      public FacePluginTokenClient(FacePluginProperties props, RestClient.Builder builder) {
            this.props = props;
            this.restClient = builder.baseUrl(props.getBaseUrl()).build();
      }

      public String issueLaunchToken() {
            Map<String, Object> body = Map.of(
                  "client_id", props.getClientId(),
                  "origin", props.getOpenerOrigin()
            );

            Map<?, ?> response = restClient.post()
                  .uri(props.getTokenEndpoint())
                  .contentType(MediaType.APPLICATION_JSON)
                  .header("X-Plugin-Api-Key", props.getApiKey())
                  .body(body)
                  .retrieve()
                  .body(Map.class);

            if (response == null || !Boolean.TRUE.equals(response.get("ok"))) {
                  throw new IllegalStateException("No se pudo obtener token de lanzamiento");
            }

            Map<?, ?> data = (Map<?, ?>) response.get("data");
            if (data == null || data.get("token") == null) {
                  throw new IllegalStateException("Respuesta invalida al solicitar token");
            }

            return data.get("token").toString();
      }
}
```

### 4) Controller MVC + endpoint interno para token

```java
package com.example.demo.web;

import com.example.demo.plugin.FacePluginTokenClient;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.ResponseBody;

import java.util.Map;

@Controller
public class AttendanceController {

      private final FacePluginTokenClient tokenClient;

      public AttendanceController(FacePluginTokenClient tokenClient) {
            this.tokenClient = tokenClient;
      }

      @GetMapping("/asistencia")
      public String attendancePage() {
            return "attendance";
      }

      @PostMapping("/asistencia/plugin-launch-token")
      @ResponseBody
      public ResponseEntity<?> launchToken() {
            String token = tokenClient.issueLaunchToken();
            return ResponseEntity.ok(Map.of("token", token));
      }
}
```

### 5) Vista Thymeleaf (attendance.html)

```html
<!doctype html>
<html lang="es" xmlns:th="http://www.thymeleaf.org">
<head>
   <meta charset="UTF-8">
   <meta name="viewport" content="width=device-width, initial-scale=1.0">
   <title>Registro de Asistencia</title>
</head>
<body>
   <h1>Registrar Asistencia</h1>

   <button id="btn_reg" type="button">Autenticar con rostro</button>
   <pre id="auth_result"></pre>

   <script src="http://127.0.0.1:5000/static/face-auth-plugin.js?v=20260811"></script>
   <script th:src="@{/js/attendance-plugin.js}"></script>
</body>
</html>
```

### 6) JavaScript del cliente (attendance-plugin.js)

```js
const btnReg = document.getElementById("btn_reg");
const resultBox = document.getElementById("auth_result");

btnReg.addEventListener("click", async () => {
   const sdk = window.FaceAuthPlugin;
   let preopenedPopup = null;

   try {
      if (!sdk || typeof sdk.open !== "function") {
         throw new Error("SDK FaceAuthPlugin no disponible");
      }

      if (typeof sdk.preopenPopup === "function") {
         preopenedPopup = sdk.preopenPopup({ width: 920, height: 760 });
      }

      const tokenResp = await fetch("/asistencia/plugin-launch-token", {
         method: "POST",
         headers: { "Content-Type": "application/json" }
      });

      if (!tokenResp.ok) {
         throw new Error("No se pudo obtener launchToken");
      }

      const tokenBody = await tokenResp.json();
      const launchToken = tokenBody.token;

      const pluginUrl = "http://127.0.0.1:5000/";
      const result = await sdk.open({
         pluginUrl,
         launchToken,
         expectedOrigin: new URL(pluginUrl).origin,
         preopenedPopup,
         closeGraceMs: 2000,
         debug: true
      });

      if (result?.cancelled) {
         resultBox.textContent = "Flujo cancelado por el usuario.";
         return;
      }

      resultBox.textContent = JSON.stringify(result.user, null, 2);
   } catch (error) {
      if (preopenedPopup && !preopenedPopup.closed) {
         try { preopenedPopup.close(); } catch (_) {}
      }

      resultBox.textContent = `Error: ${error.message || error}`;
   }
});
```

### 7) Recomendaciones operativas

1. No hardcodear launchToken ni API keys en frontend.
2. Siempre pedir launchToken a Spring en cada click.
3. Definir APP_PUBLIC_ORIGIN con el dominio real de tu app.
4. Mantener versionado del SDK en la URL para evitar cache viejo.
5. Si el navegador abre pestaña en lugar de popup, la autenticacion igual debe resolverse y cerrar al exito.

## Solucion de problemas

### command not found: python
Usa python3 para crear el entorno virtual y python despues de activarlo.

### InsightFace no detecta GPU
El proyecto tiene fallback automatico a CPU.

### Puerto 5000 ocupado
Cambia APP_PORT por variable de entorno o libera el puerto.
