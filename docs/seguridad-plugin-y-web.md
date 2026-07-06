# Seguridad para plugin y uso web normal

Este documento explica como usar la seguridad del sistema en dos escenarios:

1. Aplicaciones externas usando el plugin popup.
2. Uso web normal (sin plugin).

## 1. Seguridad para aplicaciones externas (modo plugin)

En modo plugin, el acceso se protege con:

- Cliente autorizado (`client_id` + `api_key`).
- Token de lanzamiento firmado y temporal.
- Validacion de `origin` permitido.

### Variables de entorno requeridas

Define estas variables en tu entorno o en `.env`:

```env
SECRET_KEY=una-clave-larga-y-privada
PLUGIN_SECURITY_ENABLED=1
PLUGIN_TOKEN_TTL_SECONDS=120
PLUGIN_CLIENTS=erp_portal:erp-secret-key,crm_portal:crm-secret-key
```

Notas:

- `SECRET_KEY` firma los tokens. Cambiala en produccion.
- `PLUGIN_CLIENTS` usa formato `client_id:api_key` separados por coma.
- Si `PLUGIN_SECURITY_ENABLED=1`, el plugin exige token valido.

### Flujo recomendado (backend a backend)

1. Tu backend pide token al servicio facial.
2. El servicio valida `client_id` + `X-Plugin-Api-Key`.
3. El servicio devuelve `token` temporal.
4. Tu frontend abre popup con `launchToken`.
5. El plugin valida token y solo responde al `origin` permitido.

### Solicitar token de plugin

Endpoint:

- `POST /api/plugin/token`

Headers:

- `Content-Type: application/json`
- `X-Plugin-Api-Key: <api_key_del_cliente>`

Body:

```json
{
  "client_id": "erp_portal",
  "origin": "https://tu-app.com"
}
```

Respuesta esperada:

```json
{
  "ok": true,
  "data": {
    "token": "<launch_token>",
    "expires_in": 120
  }
}
```

### Abrir plugin desde frontend

Carga el SDK:

```html
<script src="https://tu-servidor-plugin/static/face-auth-plugin.js"></script>
```

Uso:

```js
const result = await window.FaceAuthPlugin.open({
  pluginUrl: "https://tu-servidor-plugin/",
  launchToken: tokenGeneradoPorTuBackend,
  expectedOrigin: "https://tu-servidor-plugin"
});

console.log(result.user);
```

### Reglas de seguridad importantes

- Nunca expongas `api_key` en frontend.
- El token debe pedirse desde tu backend.
- Usa HTTPS en produccion.
- Rota `api_key` periodicamente.
- Usa `PLUGIN_TOKEN_TTL_SECONDS` bajo (por ejemplo 60 a 180 segundos).

## 2. Seguridad para uso web normal (sin plugin)

En uso web normal, la app no usa token de plugin para abrir `GET /`.

Esto significa que debes proteger el acceso por capa de aplicacion o infraestructura.

### Recomendaciones minimas

1. Publicar solo por HTTPS.
2. Restringir red (VPN, allowlist IP o red interna).
3. Proteger acceso con autenticacion previa (SSO o login corporativo) delante del servicio.
4. Habilitar logs y auditoria de intentos.
5. Ejecutar detras de un reverse proxy (Nginx, Traefik o API Gateway).

### Patron recomendado para web normal

- Usuario entra a tu portal corporativo.
- Tu portal valida sesion (SSO).
- Solo usuarios autenticados pueden abrir el modulo facial.
- El servicio facial queda en red privada o protegido por gateway.

## 3. Checklist de produccion

- `SECRET_KEY` robusta y privada.
- `FLASK_DEBUG=0`.
- HTTPS habilitado.
- Base de datos con credenciales seguras.
- Rotacion de claves de cliente.
- Politica de logs y monitoreo.
- Backups de base de datos.

## 4. Pruebas rapidas

### Probar emision de token (ejemplo curl)

```bash
curl -X POST http://127.0.0.1:5000/api/plugin/token \
  -H "Content-Type: application/json" \
  -H "X-Plugin-Api-Key: erp-secret-key" \
  -d '{"client_id":"erp_portal","origin":"http://localhost:3000"}'
```

Si todo esta correcto, devuelve `ok: true` y un token.

### Probar bloqueo por cliente invalido

- Envia `X-Plugin-Api-Key` incorrecto.
- Debe responder `401` con error de cliente no autorizado.

## 5. Alcance actual

Actualmente el sistema implementa seguridad fuerte para el modo plugin.

Para uso web normal sin plugin, la proteccion recomendada depende de tu arquitectura (SSO, gateway, VPN o allowlist). Este repositorio documenta ese flujo y buenas practicas, pero no reemplaza un IdP corporativo.
