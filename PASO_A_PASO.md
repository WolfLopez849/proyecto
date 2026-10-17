# Paso a paso: iniciar el asistente local

## Objetivo

Usar Hermes Desktop como aplicacion e interfaz, Qwen 2.5 como modelo local, y extenderlo con el plugin de organizacion de archivos ya presente en este repositorio. La prioridad es que el contenido y la inferencia permanezcan en el equipo.

No se construira otro chatbox ni otro ciclo de agente. Honcho se evaluara como una integracion opcional; no se levantara automaticamente.

## Estado inicial confirmado

- Hermes Desktop y su CLI estan instalados. El CLI se encontro en `%LOCALAPPDATA%\hermes\bin\hermes.exe`.
- Ollama ya tiene `qwen2.5-coder:7b` instalado y responde a una consulta local.
- El perfil que devolvio `hermes config get model` esta configurado con `anthropic/claude-opus-4.6` y OpenRouter. Eso es remoto; no se debe confundir con una configuracion offline.
- El plugin `plugins/file-organizer` pasa sus siete pruebas y `hermes plugins doctor`.
- Honcho CLI no esta instalado. No hay un perfil `.hermes` en `%USERPROFILE%`; se debe localizar el `HERMES_HOME` real del backend antes de instalar plugins.
- No se ha iniciado Docker, Honcho ni otro servicio nuevo.

## Fase 1: proteger la configuracion actual

1. Abrir Hermes Desktop y confirmar a que backend/perfil esta conectado. Los plugins Python se instalan en el backend que ejecuta Hermes, que puede ser distinto de la computadora donde esta abierta la interfaz.
2. No reemplazar el perfil actual de OpenRouter. Crear un perfil nuevo para las pruebas, por ejemplo `local-qwen`, y mantenerlo separado del perfil actual.
3. Localizar el `HERMES_HOME` que sirve a ese perfil/backend. No asumir `%USERPROFILE%\.hermes`: esa carpeta no existe en este equipo. Si Desktop esta conectado a un backend remoto, el plugin debe instalarse alli.
4. Registrar una copia de respaldo del `config.yaml` del perfil antes de cambiar proveedor, memoria o voz.

**Salida de la fase:** perfil de pruebas identificado, con su backend y directorio Hermes confirmados.

## Fase 2: conectar Qwen local a Hermes

1. Confirmar Ollama y el modelo:

   ```powershell
   ollama list
   ollama ps
   ollama run qwen2.5-coder:7b "Responde solamente: listo"
   ```

2. En una terminal fuera de una conversacion, iniciar el asistente de configuracion de modelo:

   ```powershell
   & "$env:LOCALAPPDATA\hermes\bin\hermes.exe" model
   ```

3. Elegir `Custom endpoint (self-hosted / VLLM / etc.)` y usar:
   - URL: `http://localhost:11434/v1`
   - API key: vacia; Ollama local no requiere clave.
   - Modelo: `qwen2.5-coder:7b`.
4. Aplicar el cambio solo al perfil `local-qwen`. Si el asistente de modelos no ofrece selector de perfil, detenerse y configurar el perfil mediante Hermes Desktop antes de escribir en `config.yaml`.
5. Revisar la ventana de contexto efectiva. Hermes requiere al menos 64.000 tokens para el flujo de agente con herramientas; Ollama puede arrancar con un contexto menor. No fijar un valor en Hermes que Ollama realmente no este sirviendo. Confirmar con `ollama ps` y los diagnosticos de Hermes. Si el contexto resulta menor, ajustar el contexto del modelo/servidor y reiniciarlo antes de continuar.
6. Probar en Hermes Desktop una pregunta general, una tarea sencilla de programacion y una llamada a herramienta inocua. Confirmar que responde el modelo local y que las llamadas a herramientas se ejecutan, no aparecen como JSON en el texto.
7. Si el modelo no llama herramientas con fiabilidad, registrar el resultado y detener el alcance agente: mantenerlo en chat de consulta hasta comparar otro modelo/runtime. No dar acceso a movimientos de archivos para compensar fallos de tool-calling.

**Salida de la fase:** Hermes completa chat y una llamada de herramienta con Qwen local; el perfil original sigue intacto.

## Fase 3: instalar el plugin de organizacion

1. Ejecutar la validacion del checkout:

   ```powershell
   & "$env:LOCALAPPDATA\hermes\bin\hermes.exe" plugins doctor "plugins/file-organizer" --ci
   ```

2. Copiar `plugins/file-organizer` a `<HERMES_HOME>\plugins\file-organizer` del backend/perfil local de pruebas. No instalarlo en la carpeta de la interfaz si Hermes esta ejecutandose en otro equipo.
3. Habilitarlo en ese perfil:

   ```powershell
   & "$env:LOCALAPPDATA\hermes\bin\hermes.exe" plugins enable file-organizer
   ```

4. En Hermes Desktop, abrir los ajustes del plugin y configurar una carpeta de prueba dedicada como `Allowed folders`. Empezar con una carpeta que contenga copias, no con Descargas, Documentos ni el workspace real.
5. Probar `file_organizer_preview`. Confirmar que la herramienta solo lista archivos directos, que no cambia nada y que los destinos son los esperados.
6. Revisar la aprobacion humana que Hermes muestra para `file_organizer_apply`. Solo aceptar en la carpeta de prueba; verificar el movimiento y probar `file_organizer_undo` con su propia aprobacion.
7. Probar rutas fuera de la allowlist, colisiones y cambios de archivo posteriores a la vista previa. Todos deben rechazarse. No habilitar borrado permanente.

Prueba local del codigo, independiente de Hermes:

```powershell
python -m unittest discover -s tests -v
```

**Salida de la fase:** una organizacion pequena, aprobada y reversible funciona en una carpeta desechable.

## Fase 4: decidir la memoria antes de instalar Honcho

Hermes ya incluye memoria local basica (`MEMORY.md`, `USER.md` e historial de sesiones). Activarla primero es la opcion de menor complejidad y no requiere nuevos servicios.

Honcho local no equivale a un proceso unico: su documentacion de self-hosted indica que `honcho start --setup basic` inicia API, deriver, PostgreSQL y Redis con Docker. El asistente basico solicita una clave de proveedor LLM; la documentacion consultada no confirma que esa inferencia pueda apuntar exclusivamente a Ollama/Qwen.

1. Probar primero la memoria integrada de Hermes en el perfil `local-qwen`. Configurar aprobacion de escrituras de memoria durante la evaluacion.
2. Decidir explicitamente si cuatro servicios adicionales son aceptables y comprobar que Docker ya esta disponible. No iniciar el stack sin esta decision.
3. Si se acepta la prueba de Honcho, instalar solo su CLI y revisar `honcho start --help` y la guia actual de self-hosted antes de iniciar nada. No introducir una clave cloud para intentar cumplir el requisito offline.
4. Antes de conectar Hermes a Honcho, confirmar que el deriver, embeddings y dialectica usan un endpoint local compatible. Si la configuracion exige una API externa, detener la prueba y conservar la memoria local de Hermes.
5. Si el modo local pasa la revision, instalar el proveedor de Honcho para Hermes, seleccionar la URL local que informe `honcho status` y comprobar el flujo con datos ficticios. Para detener los servicios sin borrar datos, usar `honcho stop`; no usar `--wipe` salvo que se quiera borrar el volumen de PostgreSQL.
6. Probar con la red externa desconectada: guardar un dato, cerrar/abrir sesion, recuperarlo y borrar la memoria de prueba. Comprobar que API, deriver, DB y Redis siguen sanos y que no hay dependencia cloud.

**Decision gate:** si Honcho requiere inferencia remota o los servicios persistentes no compensan el beneficio, no se integra en el MVP. Usar la memoria integrada de Hermes y dejar Honcho como experimento opcional.

## Fase 5: habilitar voz local

1. Activar reconocimiento local en Hermes: proveedor STT `local` (faster-whisper) e idioma `es`.
2. Descargar previamente el modelo de voz necesario mientras hay conexion. Verificar que el motor STT esta disponible en la instalacion de Hermes; instalar extras solo desde el mecanismo de paquetes de Hermes, no con `pip` en el Python del sistema.
3. Configurar TTS local `piper` y descargar una voz espanola compatible.
4. Usar primero pulsar-para-hablar. Revisar la transcripcion antes de enviarla; probar tambien respuesta hablada, silenciamiento, permiso del microfono y boton para desactivar voz.
5. Medir VRAM/RAM mientras Qwen responde y Whisper transcribe. Ajustar descarga por inactividad si ambos compiten por la GPU.

**Salida de la fase:** voz de entrada y salida en espanol, con el microfono desactivable y sin servicios remotos.

## Fase 6: aceptar el MVP offline

Probar el siguiente flujo completo en el perfil de pruebas:

1. Reiniciar Hermes Desktop y conectar con Qwen desde Ollama.
2. Enviar una pregunta por texto y otra por voz.
3. Completar una tarea de lectura/programacion limitada al workspace.
4. Previsualizar una organizacion en carpeta de prueba, aprobarla y revertirla.
5. Confirmar memoria entre sesiones usando memoria integrada o Honcho self-hosted ya validado.
6. Desconectar la red externa y repetir los pasos que deben ser offline.
7. Revisar actividad de red y configuracion; confirmar que el perfil no vuelve a OpenRouter ni llama a endpoints cloud.

Solo despues de esta aceptacion se configura el perfil habitual. Mantener el perfil cloud como respaldo manual, no como fallback automatico, para que una caida local no envie prompts a un proveedor remoto sin consentimiento.

## Orden resumido

1. Perfil de pruebas y respaldo.
2. Qwen local en Hermes, incluido contexto y tool-calling.
3. Plugin de organizacion con allowlist y carpeta desechable.
4. Memoria local de Hermes; Honcho solo tras decision de servicios y prueba offline.
5. Whisper local y Piper local.
6. Aceptacion sin red y, finalmente, migracion de configuracion si se aprueba.
