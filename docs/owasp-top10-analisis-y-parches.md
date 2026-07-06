# Analisis de vulnerabilidades (OWASP Top 10) y parches aplicados

Fecha: 2026-07-05

## Resumen ejecutivo

Se realizo una revision de seguridad del servicio de registro/autenticacion facial y del flujo plugin popup. Se aplicaron parches para reducir exposicion en autenticacion de integraciones, abuso de endpoints, configuraciones inseguras y filtrado de errores internos.

## Hallazgos por OWASP Top 10

## A01: Broken Access Control

Riesgo identificado:

- El endpoint de registro podia quedar abierto sin control adicional.
- El plugin podia ser invocado por terceros si conocian la URL (sin capa robusta inicial).

Parches aplicados:

- Se agrego `REGISTER_API_KEY` opcional para proteger `POST /api/stream/register` con header `X-Register-Api-Key`.
- El modo plugin exige token firmado temporal cuando `PLUGIN_SECURITY_ENABLED=1`.
- Se valida cliente autorizado por `client_id` + `X-Plugin-Api-Key` en `POST /api/plugin/token`.
- Se valida `origin` del token y allowlist opcional (`PLUGIN_ALLOWED_ORIGINS`).

## A02: Cryptographic Failures

Riesgo identificado:

- Secreto por defecto debil en ambientes no configurados.

Parches aplicados:

- Se centraliza uso de `SECRET_KEY` para firma de token plugin.
- Se documenta configuracion obligatoria de secreto fuerte en `.env`.

## A03: Injection

Riesgo identificado:

- Bajo en SQL por uso ORM.
- Riesgo de entrada no validada en campos de usuario y payloads.

Parches aplicados:

- Validacion de `nombre` (longitud) y `identificacion` con regex controlada.
- Validacion fuerte de `origin` con `urlparse`.

## A04: Insecure Design

Riesgo identificado:

- No habia controles anti abuso por diseno (fuerza bruta y flooding de endpoints).

Parches aplicados:

- Rate limiting en memoria por IP para:
  - Emision de token plugin.
  - Registro.
  - Autenticacion.
- Limite de tamano de body (`MAX_CONTENT_LENGTH`).
- Limite de tamano de frame base64 en decodificacion.

## A05: Security Misconfiguration

Riesgo identificado:

- Debug habilitable por defecto.
- Faltaban headers de hardening.

Parches aplicados:

- `FLASK_DEBUG=0` recomendado por defecto en `.env.example`.
- Headers de seguridad en todas las respuestas (si `SECURITY_HEADERS_ENABLED=1`):
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `Referrer-Policy: no-referrer`
  - `Content-Security-Policy` restrictiva
  - `Strict-Transport-Security` en HTTPS y sin debug

## A06: Vulnerable and Outdated Components

Riesgo identificado:

- Requiere proceso continuo de actualizacion de dependencias.

Estado:

- No se automatizo escaneo de CVE en este parche.

Recomendacion:

- Integrar `pip-audit` o escaneo SCA en CI/CD.

## A07: Identification and Authentication Failures

Riesgo identificado:

- Integracion plugin sin autenticacion fuerte inicial.

Parches aplicados:

- Token temporal firmado para lanzamiento plugin.
- Comparacion de API key en tiempo constante (`hmac.compare_digest`).

## A08: Software and Data Integrity Failures

Riesgo identificado:

- Sin mecanismo de firma/verificacion para integracion plugin inicialmente.

Parches aplicados:

- Token firmado con `itsdangerous` y expiracion.

## A09: Security Logging and Monitoring Failures

Riesgo identificado:

- Errores internos podian devolverse al cliente, con baja trazabilidad segura.

Parches aplicados:

- Manejo de errores con mensajes controlados al cliente.
- Logging de excepciones internas en servidor (`logger.exception`).

## A10: Server-Side Request Forgery (SSRF)

Riesgo identificado:

- No se detectaron llamadas server-side a URLs de usuario en este flujo.

Estado:

- Sin cambios requeridos para SSRF en esta iteracion.

## Archivos modificados en el hardening

- `app.py`
- `config.py`
- `routes/auth_routes.py`
- `services/face_auth_service.py`
- `services/rate_limiter.py`
- `.env.example`

## Riesgos residuales

- El rate limit actual es en memoria (por proceso). En despliegues multi-replica se recomienda Redis.
- Para uso web normal sin plugin, se recomienda capa de autenticacion corporativa (SSO/gateway).
- Se recomienda rotacion periodica de claves de clientes (`PLUGIN_CLIENTS`).

## Verificacion recomendada

1. Probar que `POST /api/plugin/token` retorna 401 con API key invalida.
2. Probar que plugin sin token retorna 403.
3. Probar que un `origin` fuera de allowlist es rechazado.
4. Probar que exceso de intentos retorna 429.
5. Probar que errores internos no exponen stack trace al cliente.
