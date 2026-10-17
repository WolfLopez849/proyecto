# Asistente local de programacion y organizacion

Primer incremento del asistente Windows basado en Hermes Desktop, Ollama y Qwen 2.5. El repositorio comienza con un plugin Hermes para previsualizar, aplicar y deshacer una organizacion segura de archivos.

La secuencia completa para iniciar y validar el asistente esta en [PASO_A_PASO.md](PASO_A_PASO.md).

## Estado

- Hermes Desktop es la interfaz y el agente base; no se replica su chat ni su ciclo de herramientas.
- Ollama ya tiene `qwen2.5-coder:7b` disponible en el equipo de desarrollo. Aun falta probarlo desde una sesion real de Hermes.
- El plugin `file-organizer` esta implementado y pasa las pruebas unitarias y `hermes plugins doctor`.
- Honcho local sigue pendiente. No se ha iniciado Docker ni ningun servicio nuevo. La documentacion consultada describe el stack local oficial mediante Docker; antes de usarlo se comprobara si puede apuntar a Ollama y funcionar sin conexiones externas.

## Plugin de organizacion

`plugins/file-organizer` proporciona tres herramientas:

- `file_organizer_preview` inspecciona solo archivos directamente dentro de una carpeta permitida y devuelve un plan; no mueve ni escribe archivos.
- `file_organizer_apply` mueve los archivos del plan aprobado a carpetas por tipo. Hermes solicita confirmacion humana antes de ejecutar esta herramienta.
- `file_organizer_undo` restaura una operacion registrada y tambien requiere confirmacion humana.

Solo se aceptan carpetas configuradas expresamente en **Settings > Plugins > File Organizer > Allowed folders**. Los subdirectorios, archivos ocultos, enlaces y destinos existentes se omiten o rechazan. Los planes expiran a los 15 minutos. No se implementa borrado.

El plugin se valida con el CLI de Hermes instalado en Windows:

```powershell
& "$env:LOCALAPPDATA\hermes\bin\hermes.exe" plugins doctor "plugins/file-organizer" --ci
```

Para instalar una copia local en el perfil predeterminado:

```powershell
$plugins = Join-Path $env:USERPROFILE ".hermes\plugins"
New-Item -ItemType Directory -Force -Path $plugins | Out-Null
Copy-Item -Recurse -Force "plugins/file-organizer" (Join-Path $plugins "file-organizer")
& "$env:LOCALAPPDATA\hermes\bin\hermes.exe" plugins doctor (Join-Path $plugins "file-organizer") --ci
& "$env:LOCALAPPDATA\hermes\bin\hermes.exe" plugins enable file-organizer
```

La instalacion no configura carpetas permitidas. Agregalas desde los ajustes del plugin en Hermes Desktop antes de usar la vista previa.

## Desarrollo y pruebas

```powershell
python -m unittest discover -s tests -v
```

El nucleo de las operaciones esta en `plugins/file-organizer/tools.py` y se puede probar sin instalar Hermes.

## Honcho local

No arrancar Honcho ni Docker automaticamente. Siguiente tarea: probar si el despliegue local de Honcho puede usar el endpoint de Ollama y funcionar sin red externa. Si requiere servicios o inferencia remota adicionales, conservar temporalmente la memoria local incluida en Hermes o comparar una alternativa local mas ligera antes de desplegarlo.