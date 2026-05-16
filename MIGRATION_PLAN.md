# Plan de Migración: asistente-francisco → upstream v0.2.0
## Actualizado 2026-05-16 10:05

## Resumen
- **Upstream**: v0.2.0 (c018c3fb) — 1,205 commits nuevos
- **Nuestro**: 81 commits propios sobre upstream antiguo
- **Estrategia**: Partir de upstream v0.2.0 y portar solo lo que falta

---

## ANÁLISIS POR SUBSISTEMA

### 1. TRANSCRIPCIÓN DE AUDIO

| Feature | Nuestro | Upstream | ¿Migrar? |
|---|---|---|---|
| OpenAI Whisper provider | ✅ | ✅ | ❌ Ya lo tiene |
| Groq Whisper provider | ✅ | ✅ | ❌ Ya lo tiene |
| **AssemblyAI provider** | ✅ | ❌ | ✅ **MIGRAR** — upstream solo tiene OpenAI y Groq |
| Config en base channel | Nuestro: en WhatsApp config | Upstream: en BaseChannel | ❌ Upstream es mejor (todos los canales lo heredan) |
| transcription_api_base configurable | ❌ | ✅ | ❌ Upstream es mejor |
| transcription_language configurable | ❌ | ✅ | ❌ Upstream es mejor |
| Retry con backoff en transcripción | ❌ | ✅ `_post_transcription_with_retry` | ❌ Upstream es mejor |
| Forwarded voice → "please summarize" | ✅ | ❌ | ✅ **MIGRAR** — útil para audios reenviados |

**Acción:** Portar AssemblyAI provider a transcription.py. Portar lógica de forwarded voice a whatsapp.py.

---

### 2. BRIDGE (Node.js Baileys) — Comunicación Francisco ↔ Claudio

| Feature | Nuestro | Upstream | ¿Migrar? |
|---|---|---|---|
| **startupTimestamp filter** | ✅ Drop msgs older than boot | ❌ No filtra | ✅ **MIGRAR** — sin esto, al reconectar se reenvían mensajes viejos |
| **chatStore in-memory** | ✅ 200 msgs/chat | ❌ | ⚠️ **EVALUAR** — lo usábamos para get_chats/get_messages que ahora hace WAHA. Pero podría ser útil como fallback |
| **connected flag** | ✅ | ❌ | ✅ **MIGRAR** — upstream no tiene flag de conexión en el bridge TS |
| **vCard parsing** | ✅ contactMessage + contactsArray | ❌ | ✅ **MIGRAR** — upstream ignora contactos compartidos |
| **isForwarded flag** | ✅ Detecta mensajes reenviados | ❌ | ✅ **MIGRAR** — necesario para la lógica de forwarded voice |
| wasMentioned | ❌ | ✅ | ❌ Upstream es mejor |
| normalizeJid | ❌ | ✅ | ❌ Upstream es mejor |
| Audio download | ✅ | ✅ | ❌ Ambos lo tienen |
| Image/video/document download | ✅ | ✅ | ❌ Ambos lo tienen |
| send_media command | ✅ | ✅ | ❌ Ambos lo tienen |

**Acción en bridge/src/whatsapp.ts:**
1. Añadir `startupTimestamp` filter (5 líneas)
2. Añadir `isForwarded` flag al evento (3 líneas)
3. Añadir vCard parsing (15 líneas)
4. El chatStore NO migrar — WAHA cubre esa función

**Acción en bridge/src/server.ts:**
- get_chats/get_messages/search_messages → NO migrar (WAHA MCP lo hace)
- El resto ya está en upstream

---

### 3. CANAL WHATSAPP (Python) — whatsapp.py

| Feature | Nuestro | Upstream | ¿Migrar? |
|---|---|---|---|
| bridge_token management | ✅ | ✅ | ❌ Upstream lo tiene idéntico |
| LID ↔ phone mapping | ✅ | ✅ | ❌ Upstream lo tiene |
| group_policy (open/mention) | ✅ | ✅ | ❌ Upstream lo tiene |
| _connected flag + ConnectionError | ✅ | ✅ | ❌ Upstream lo tiene |
| send media con _resolve_media_path | ✅ (descarga URLs remotas) | ❌ (solo paths locales) | ✅ **MIGRAR** — sin esto, URLs de S3/web no se envían |
| _deferred_unlink (temp cleanup) | ✅ | ❌ | ✅ **MIGRAR** — va con _resolve_media_path |
| send_raw_message (para tools) | ✅ | ❌ | ⚠️ **EVALUAR** — ya no lo usamos (WAHA MCP envía) |
| get_chats/get_messages/search_messages | ✅ | ❌ | ❌ NO migrar — WAHA MCP lo hace |
| _query_bridge (request/response) | ✅ | ❌ | ❌ NO migrar — iba con get_chats etc |
| _process_vcards / _save_contact | ✅ | ❌ | ✅ **MIGRAR** — parsea vCards y guarda contactos |
| Forwarded voice → "please summarize" | ✅ | ❌ | ✅ **MIGRAR** — mejor manejo de audios reenviados |
| transcription config en WhatsApp | ✅ (redundante) | ✅ (en BaseChannel) | ❌ Upstream es mejor |

**Acción en nanobot/channels/whatsapp.py:**
1. Portar `_resolve_media_path` + `_deferred_unlink` (35 líneas)
2. Portar `_process_vcards` + `_save_contact` (30 líneas)
3. Portar lógica de `isForwarded` en voice transcription (5 líneas)
4. NO portar: get_chats, get_messages, search_messages, _query_bridge, send_raw_message

---

### 4. MEMORY / CONSOLIDACIÓN

| Feature | Nuestro | Upstream | ¿Migrar? |
|---|---|---|---|
| Multi-file consolidation | ✅ (MEMORY.md + HISTORY.md separados) | ✅ "Dream" system (2 fases) | ❌ **NO MIGRAR** — upstream reescribió completamente |
| Backup versioning | ✅ | ✅ `_next_legacy_backup_path` | ❌ Ya lo tiene |
| History pruning | ✅ | ✅ Dream phase 2 | ❌ Ya lo tiene |
| Reserve completion headroom | ✅ | ✅ Dream tiene su propio budget | ❌ Ya lo tiene |
| Consolidation trigger ratio | ✅ 0.92 | Upstream: diferente mecanismo | ❌ Configurar en runtime |

**Acción:** Usar el Dream system de upstream tal cual. Nuestros ajustes de ratio se configuran en config.json.

---

### 5. CRON

| Feature | Nuestro | Upstream | ¿Migrar? |
|---|---|---|---|
| Silent mode (no auto-deliver) | ✅ | ❌ | ✅ **MIGRAR** |
| lock_recipient | ✅ | ❌ | ✅ **MIGRAR** |
| Timezone support | ✅ | ✅ | ❌ Ya lo tiene |
| Cron store scoped to workspace | ✅ | ✅ | ❌ Ya lo tiene |

**Acción:** Portar `silent` flag y `lock_recipient` a cron types y service.

---

### 6. TOOLS

| Feature | Nuestro | Upstream | ¿Migrar? |
|---|---|---|---|
| datafact_monitoring.py | ✅ | ❌ | ✅ Ya portado ✅ |
| nylas.py (email/calendar) | ✅ | ❌ | ✅ Ya portado ✅ |
| media.py | ✅ | ❌ | ✅ Ya portado ✅ |
| MCP TCP probe | ✅ | ✅ | ❌ Ya lo tiene |
| MCP nullable params | ✅ | ✅ | ❌ Ya lo tiene |
| Shell zombie fix | ✅ | ✅ | ❌ Ya lo tiene |
| Message tool media description | ✅ | ⚠️ Verificar | Baja prioridad |

---

### 7. PROVIDERS

| Feature | Nuestro | Upstream | ¿Migrar? |
|---|---|---|---|
| custom_provider.py | ✅ | ✅ openai_compat_provider (mejor) | ❌ Upstream es mejor |
| litellm_provider.py | ✅ | ❌ (eliminaron litellm) | ❌ NO migrar — obsoleto |
| Anthropic prompt cache | ✅ | ✅ `_apply_cache_control` | ❌ Ya lo tiene |
| Truncate error body | ✅ | ⚠️ Verificar | Baja prioridad |

---

### 8. TEMPLATES Y CONFIG

| Feature | Nuestro | Upstream | ¿Migrar? |
|---|---|---|---|
| SECURITY.md template | ✅ | ❌ | ✅ Ya portado ✅ |
| ORG.md template | ✅ | ❌ | ✅ Ya portado ✅ |
| TAREAS.md template | ✅ | ❌ | ✅ Ya portado ✅ |
| BOOTSTRAP_FILES ampliado | ✅ | ❌ | ✅ Ya portado ✅ |
| SOUL.md (Claudio identity) | Workspace config | N/A | Configurar al instalar |
| AGENTS.md (reglas custom) | Workspace config | N/A | Configurar al instalar |

---

### 9. SCRIPTS OPERACIONALES

| Feature | Nuestro | Upstream | ¿Migrar? |
|---|---|---|---|
| nanobot-restart | ✅ | ❌ | ✅ Ya portado ✅ |
| nanobot-logs | ✅ | ❌ | ✅ Ya portado ✅ |
| nanobot-rotate-logs | ✅ | ❌ | ✅ Ya portado ✅ |
| launchd plists | ✅ | ❌ | ✅ Ya portado ✅ |
| Pre-release tests on restart | ✅ | ❌ | 🟡 Portar a nanobot-restart |

---

### 10. SEGURIDAD Y RED

| Feature | Nuestro | Upstream | ¿Migrar? |
|---|---|---|---|
| SSRF whitelist | ✅ | ✅ | ❌ Ya lo tiene |
| Think-block strip | ✅ | ✅ | ❌ Ya lo tiene |
| Prompt injection protection | ✅ (SECURITY.md) | ❌ | ✅ Ya portado ✅ |

---

## PLAN DE EJECUCIÓN — ORDENADO POR PRIORIDAD

### Fase 1: Bridge (30 min) — SIN ESTO NO FUNCIONA
1. `bridge/src/whatsapp.ts`: Añadir startupTimestamp filter
2. `bridge/src/whatsapp.ts`: Añadir isForwarded flag
3. `bridge/src/whatsapp.ts`: Añadir vCard parsing

### Fase 2: Canal WhatsApp (45 min) — MEJORAS IMPORTANTES
4. `channels/whatsapp.py`: Portar _resolve_media_path + _deferred_unlink
5. `channels/whatsapp.py`: Portar _process_vcards + _save_contact
6. `channels/whatsapp.py`: Portar lógica forwarded voice

### Fase 3: Transcripción (20 min)
7. `providers/transcription.py`: Añadir AssemblyAI provider

### Fase 4: Cron (30 min)
8. `cron/types.py`: Añadir silent flag y lock_recipient
9. `cron/service.py`: Implementar silent mode
10. `agent/tools/cron.py`: Exponer silent en el tool

### Fase 5: Scripts (15 min)
11. `scripts/nanobot-restart`: Añadir pre-release tests

### Fase 6: Verificación (30 min)
12. Instalar bridge deps (npm install)
13. Copiar workspace actual (memory, config.json)
14. Test de arranque
15. Test de envío/recepción WhatsApp

---

## RESUMEN FINAL

| Categoría | Commits | Estado |
|---|---|---|
| ✅ Ya en upstream (no migrar) | 48 | Hecho |
| ✅ Ya portados (primer commit) | 5 | Hecho |
| ❌ No portar (obsoletos/revertidos) | 7 | Descartados |
| ❌ No portar (upstream es mejor) | 10 | Descartados |
| ✅ Migrar | 11 | **Pendiente — ~2.5 horas** |

### Features NUEVAS que ganamos gratis de upstream:
- 🆕 Goals / Long Tasks
- 🆕 Pairing (control de acceso)
- 🆕 WebUI
- 🆕 Brave Search + DuckDuckGo
- 🆕 Dream System (consolidación de memoria avanzada)
- 🆕 Prompt templates Jinja2
- 🆕 wasMentioned (group_policy mejorado)
- 🆕 normalizeJid
- 🆕 Transcription retry con backoff
- 🆕 transcription_language configurable
- 🆕 Matrix, Weixin channels
- 🆕 v0.2.0 wheel packaging
