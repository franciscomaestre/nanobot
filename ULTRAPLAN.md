# ULTRAPLAN — Migración nanobot v2
## Generado: 2026-05-16 10:12 | Estimado: 2.5h

---

## FASE 1: Bridge whatsapp.ts (30 min)

### 1.1 startupTimestamp filter
- **Archivo**: `bridge/src/whatsapp.ts`
- **Ubicación**: Dentro de `async connect()`, justo antes de `this.sock = makeWASocket(...)`
- **Código**: Declarar `const startupTimestamp = Math.floor(Date.now() / 1000);`
- **Ubicación 2**: Dentro del handler `messages.upsert`, al inicio del for loop
- **Código**: `const msgTimestamp = msg.messageTimestamp as number; if (msgTimestamp && msgTimestamp < startupTimestamp) continue;`
- **Por qué**: Sin esto, al reconectar Baileys reenvía mensajes históricos y Claudio los procesa como nuevos

### 1.2 isForwarded flag
- **Archivo**: `bridge/src/whatsapp.ts`
- **Ubicación**: Donde se construye el objeto de evento que se emite
- **Código**: Extraer `msg.message?.extendedTextMessage?.contextInfo?.isForwarded || false` y añadirlo al payload
- **Por qué**: Necesario para que el canal Python distinga audios reenviados de audios directos

### 1.3 vCard parsing
- **Archivo**: `bridge/src/whatsapp.ts`
- **Ubicación**: Dentro del handler de mensajes, después de document/video/audio checks
- **Código**: Detectar `unwrapped.contactMessage` y `unwrapped.contactsArrayMessage`, extraer displayName + vcard text, incluirlo en content
- **Por qué**: Sin esto, cuando alguien comparte un contacto por WhatsApp, Claudio no lo ve

---

## FASE 2: Canal WhatsApp Python (45 min)

### 2.1 _resolve_media_path
- **Archivo**: `nanobot/channels/whatsapp.py`
- **Ubicación**: Nuevo método en la clase WhatsAppChannel
- **Función**: Recibe un path (local o URL). Si es URL http/https, descarga a tempfile y devuelve (local_path, True). Si es local, devuelve (path, False).
- **Por qué**: Sin esto, cuando un tool genera una imagen en S3 o cualquier URL remota, el bridge no puede enviarla (solo acepta paths locales)

### 2.2 _deferred_unlink
- **Archivo**: `nanobot/channels/whatsapp.py`
- **Ubicación**: Método estático en WhatsAppChannel
- **Función**: `asyncio.sleep(30)` + `os.unlink(path)`. Se lanza como `asyncio.create_task()` después de enviar media temporal.
- **Por qué**: Si borras el temp file inmediatamente, el bridge aún no lo ha leído → ENOENT → imagen nunca llega

### 2.3 Integrar resolve + deferred en send()
- **Archivo**: `nanobot/channels/whatsapp.py`
- **Ubicación**: Dentro de `async def send()`, en el loop de `msg.media`
- **Cambio**: Antes de enviar cada media, llamar `_resolve_media_path`. Si es temp, programar `_deferred_unlink` en finally.

### 2.4 _process_vcards + _save_contact
- **Archivo**: `nanobot/channels/whatsapp.py`
- **Ubicación**: Nuevos métodos en WhatsAppChannel
- **Función**: Parsear vCard text (BEGIN:VCARD...END:VCARD), extraer FN, TEL, EMAIL. Guardar en workspace/CONTACTS.md
- **Trigger**: Llamar desde `_handle_bridge_message` cuando content contiene vCard data

### 2.5 Forwarded voice handling
- **Archivo**: `nanobot/channels/whatsapp.py`
- **Ubicación**: Dentro del bloque de voice transcription (donde dice `content == "[Voice Message]"`)
- **Cambio**: Si `isForwarded` es True, envolver transcripción en `[Forwarded voice message — please summarize]\n\n{transcription}` en vez de solo `{transcription}`
- **Por qué**: Un audio reenviado no es una instrucción del usuario, es contenido a resumir

---

## FASE 3: Transcripción AssemblyAI (20 min)

### 3.1 AssemblyAI provider
- **Archivo**: `nanobot/providers/transcription.py`
- **Ubicación**: Nueva clase al final del archivo
- **Código**: Copiar `AssemblyAITranscriptionProvider` de nuestro transcription.py. Usa `assemblyai` SDK, transcribe sync en thread executor.
- **Config**: Se activa con `transcription_provider: "assemblyai"` + `ASSEMBLYAI_API_KEY`

### 3.2 Registrar en base channel
- **Archivo**: `nanobot/channels/base.py`
- **Ubicación**: En `transcribe_audio()`, añadir elif para "assemblyai"
- **Código**: `elif self.transcription_provider == "assemblyai": from ...transcription import AssemblyAITranscriptionProvider; provider = AssemblyAITranscriptionProvider(api_key=...)`

---

## FASE 4: Cron silent mode (30 min)

### 4.1 Silent flag en types
- **Archivo**: `nanobot/cron/types.py`
- **Ubicación**: En la dataclass/model del job
- **Cambio**: Añadir campo `silent: bool = False`
- **Por qué**: Jobs silenciosos ejecutan la tarea pero no auto-entregan la respuesta al canal

### 4.2 lock_recipient en types
- **Archivo**: `nanobot/cron/types.py`
- **Cambio**: Añadir campo `lock_recipient: str | None = None` (chat_id fijo para el job)

### 4.3 Silent mode en service
- **Archivo**: `nanobot/cron/service.py`
- **Ubicación**: En el método que ejecuta el job cuando se dispara
- **Cambio**: Si `job.silent`, ejecutar el agente pero NO enviar la respuesta al canal. El agente puede usar `message` tool explícitamente si necesita notificar.

### 4.4 Exponer en cron tool
- **Archivo**: `nanobot/agent/tools/cron.py`
- **Ubicación**: En los parámetros del tool
- **Cambio**: Añadir `silent` como parámetro opcional. Pasarlo al crear el job.

---

## FASE 5: Scripts (15 min)

### 5.1 Pre-release tests en nanobot-restart
- **Archivo**: `scripts/nanobot-restart`
- **Cambio**: Antes de detener nanobot, ejecutar `.venv/bin/python -m pytest tests/ -x -q`. Si falla, abortar restart.

---

## FASE 6: Verificación (30 min)

### 6.1 Instalar bridge deps
- `cd bridge && npm install`

### 6.2 Copiar workspace
- Copiar `~/.nanobot/workspace/` (memory, config.json, skills)
- Ajustar config.json si hay campos nuevos

### 6.3 Test de arranque
- `.venv/bin/python -m nanobot` — verificar que arranca sin errores

### 6.4 Test WhatsApp
- Enviar mensaje → verificar recepción
- Enviar audio → verificar transcripción
- Enviar imagen → verificar que llega

---

## CHECKLIST DE EJECUCIÓN

- [ ] 1.1 startupTimestamp en bridge
- [ ] 1.2 isForwarded en bridge
- [ ] 1.3 vCard parsing en bridge
- [ ] 2.1 _resolve_media_path
- [ ] 2.2 _deferred_unlink
- [ ] 2.3 Integrar en send()
- [ ] 2.4 _process_vcards + _save_contact
- [ ] 2.5 Forwarded voice handling
- [ ] 3.1 AssemblyAI provider
- [ ] 3.2 Registrar en base channel
- [ ] 4.1 Silent flag en cron types
- [ ] 4.2 lock_recipient en cron types
- [ ] 4.3 Silent mode en cron service
- [ ] 4.4 Exponer en cron tool
- [ ] 5.1 Pre-release tests
- [ ] 6.1 npm install bridge
- [ ] 6.2 Copiar workspace
- [ ] 6.3 Test arranque
- [ ] 6.4 Test WhatsApp
