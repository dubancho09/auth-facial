# OCR - Sistema de Registro y Autenticacion Facial

Este proyecto usa Flask + InsightFace para registrar usuarios y autenticarlos por rostro desde streaming de camara.

## Requisitos

- macOS
- Python 3.9+
- Camara web habilitada

## 1. Entrar al proyecto

```bash
cd /Users/areamovil/Desktop/ocr
```

## 2. Crear entorno virtual

```bash
python3 -m venv venv
```

## 3. Activar entorno virtual

```bash
source venv/bin/activate
```

Cuando este activo, veras `(venv)` al inicio de la terminal.

## 4. Actualizar pip (recomendado)

```bash
python -m pip install --upgrade pip
```

## 5. Instalar dependencias

```bash
pip install -r requirements.txt
```

## 6. Ejecutar el proyecto

```bash
python app.py
```

La aplicacion quedara disponible en:

- http://127.0.0.1:5000

## 7. Uso basico

1. Abre el navegador en http://127.0.0.1:5000
2. Permite acceso a la camara
3. En la pestaña Registrar:
   - Ingresa nombre y documento
   - Pulsa "Iniciar registro por streaming"
4. En la pestaña Autenticar:
   - Pulsa "Iniciar autenticacion"

## 8. Desactivar entorno virtual

Cuando termines:

```bash
deactivate
```

## Solucion de problemas comunes

### Error: command not found: python
Usa siempre `python3` para crear el entorno virtual y `python` despues de activar `venv`.

### InsightFace no detecta GPU
El proyecto ya tiene fallback automatico a CPU. Puede ser mas lento, pero funciona.

### Puerto ocupado
Si el puerto 5000 esta en uso, cierra el proceso anterior o cambia el puerto en `app.py`:

```python
app.run(debug=True, port=5001)
```
