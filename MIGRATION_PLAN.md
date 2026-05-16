# Plan de Migración: asistente-francisco → upstream v0.2.0

## Resumen
- **Upstream**: v0.2.0 (c018c3fb) — 1,205 commits nuevos
- **Nuestro**: 81 commits propios sobre upstream antiguo
- **Estrategia**: Partir de upstream v0.2.0 y portar solo lo que falta

---

## COMMITS QUE YA NO HAY QUE MIGRAR (upstream los tiene)

### ✅ Ya en upstream — Idéntico o mejor implementación

| # | Commit nuestro | Razón por la que NO hay que migrar |
|---|---|---|
| 1 | `ccbae4eb` feat: WhatsApp send media | ✅ Upstream tiene `send_media` en bridge y canal |
| 2 | `8780453d` feat: voice transcription | ✅ Upstream tiene transcription.py + integración WhatsApp |
| 3 | `a061f39b` feat: Firecrawl search | ✅ Upstream tiene Brave + DuckDuckGo + Olostep en web.py |
| 4 | `d0221224` fix: bridge download audio | ✅ Upstream bridge descarga audio |
| 5 | `93f2a8e6` fix: bridge fallbackContent | ✅ Upstream maneja fallback |
| 6 | `a0aa4b6e` fix: bridge drop old messages | ✅ Upstream tiene startupTimestamp filter |
| 7 | `65efe6f2` feat: WhatsApp proxy | ✅ REVERTIDO por nosotros mismos (`5618436d`) — no aplica |
| 8 | `a982fbcc` feat: proxy routing fix | ✅ REVERTIDO — no aplica |
| 9 | `ece4d784` feat: proxy relay | ✅ REVERTIDO — no aplica |
| 10 | `5618436d` revert: eliminar proxy | ✅ Ya revertido — no aplica |
| 11 | `8998838b` feat: vCard parse | ❌ Upstream NO tiene — pero ya no lo usamos (WAHA) |
| 12 | `5a1a9fac` fix: bridge read receipts | ✅ Upstream bridge maneja receipts |
| 13 | `f41ad35a` feat: per-MCP allowFrom | ✅ Upstream tiene pairing system (más completo) |
| 14 | `74544b22` feat: Firecrawl fetch | ✅ Upstream tiene Olostep + readability fallback |
| 15 | `1cd902dd` feat: Serper search | ✅ Upstream tiene Brave (mejor) |
| 16 | `038d30c0` fix: LID vs phone allowFrom | ✅ Upstream tiene LID handling en whatsapp.py |
| 17 | `130be8b4` fix: LID by JID suffix | ✅ Upstream tiene clasificación por JID suffix |
| 18 | `f73e5706` feat: timezone support | ✅ Upstream tiene timezone en context.py y cron |
| 19 | `c3d933b4` feat: heartbeat retention, shell zombie, group_policy | ✅ Upstream tiene group_policy y kill_process |
| 20 | `2476585a` feat: per-session locks, parallel tools, background memory | ✅ Upstream tiene concurrent_tools y session locks |
| 21 | `52beac11` feat: cron store scoped | ✅ Upstream tiene cron scoped a workspace |
| 22 | `3b90fdbc` refactor: replace litellm | ✅ Upstream eliminó litellm, tiene openai_compat_provider |
| 23 | `95342e9f` refactor: shared AgentRunner | ✅ Upstream tiene runner refactorizado |
| 24 | `83ccf560` fix: nullable MCP params | ✅ Upstream tiene `_extract_nullable_branch` en mcp.py |
| 25 | `088ccb8c` fix: orphan tool trimming | ✅ Upstream tiene `_find_legal_start` en loop.py |
| 26 | `245ef38a` fix: count all message fields | ✅ Upstream tiene token estimation mejorada |
| 27 | `474399ca` fix: preserve image paths | ✅ Upstream tiene `_meta.path` en images |
| 28 | `649a5c90` perf: Anthropic prompt cache | ✅ Upstream tiene `_apply_cache_control` en anthropic_provider |
| 29 | `bc7c224d` fix: MCP TCP probe | ✅ Upstream tiene `_probe_http_url` en mcp.py |
| 30 | `6e9d699d` fix: orphan tool trim v2 | ✅ Upstream tiene implementación equivalente |
| 31 | `fc2ea9d0` fix: skip duplicate runtime ctx | ✅ Upstream tiene `_RUNTIME_CONTEXT_END` tag |
| 32 | `8c7816c1` security: SSRF whitelist | ✅ Upstream tiene `configure_ssrf_whitelist` |
| 33 | `2ffa5aac` fix: providers retry, shell path | ✅ Upstream tiene retry y path handling |
| 34 | `99a5c5c5` feat: media dir, retry headers | ✅ Upstream tiene media handling |
| 35 | `fa661182` feat: memory history injection, adaptive thinking | ✅ Upstream tiene history injection y thinking |
| 36 | `cc7bb26a` feat: upstream sync low risk | ✅ Ya incluido en upstream |
| 37 | `f7f4fa0d` feat: upstream sync medium risk | ✅ Ya incluido en upstream |
| 38 | `ea85e95e` sync | ✅ Sync commit — no aplica |
| 39 | `7cdd121a` fix: pass BRIDGE_TOKEN to bridge | ✅ Upstream tiene `env["BRIDGE_TOKEN"]` |
| 40 | `abcd4be3` fix: bridge guard readMessages | ✅ Upstream tiene `_connected` flag |
| 41 | `5d49811c` fix: bridge close existing clients | ✅ Upstream bridge maneja reconexión |

### ✅ Ya en upstream — Tests y docs que no aplican
| # | Commit | Razón |
|---|---|---|
| 42 | `ca5c2d7f` Python 3.9 compat | ✅ Upstream requiere 3.11+ |
| 43 | `1b076963` Revert Python 3.9 | ✅ No aplica |
| 44 | `23c39a0c` pre-release smoke tests | ⚠️ Nuestros tests — evaluar si portar |
| 45 | `85f5c4a3` Anthropic + bridge tests | ⚠️ Nuestros tests — evaluar si portar |
| 46 | `7bed76b6` docs: sync status | ✅ Doc obsoleto |
| 47 | `ae2e651f` docs: sync strategy | ✅ Doc obsoleto |
| 48 | `e0ffa677` .gitignore | ✅ Upstream tiene su propio .gitignore |

---

## COMMITS QUE SÍ HAY QUE MIGRAR

### 🔴 CRÍTICOS — Sin esto no funciona el día a día

| # | Commit | Qué portar | Complejidad |
|---|---|---|---|
| C1 | `063fd13f` datafact_monitoring tools | Copiar archivo (ya hecho ✅) | Baja |
| C2 | `8d8554df` + `fd141763` + `28716c6d` + `c332d622` + `90979dd1` Nylas tools | Copiar archivo (ya hecho ✅) | Baja |
| C3 | `32755af7` SECURITY.md template | Copiar archivo (ya hecho ✅) | Baja |
| C4 | `8498b7ac` ORG.md + TAREAS.md templates | Copiar archivo (ya hecho ✅) | Baja |
| C5 | BOOTSTRAP_FILES ampliado | Editar context.py (ya hecho ✅) | Baja |

### 🟡 IMPORTANTES — Mejoras nuestras que upstream no tiene

| # | Commit | Qué portar | Complejidad | Detalle |
|---|---|---|---|---|
| I1 | `60d339e7` memory multi-file consolidation | Evaluar diff con upstream memory.py | **Alta** | Upstream reescribió memory.py completamente (1087 líneas vs nuestras 658). Tiene "dream" system. Nuestro multi-file consolidation puede no ser compatible. **RECOMENDACIÓN: Usar upstream y evaluar si dream cubre lo mismo.** |
| I2 | `1d74bbec` + `b81f9476` silent cron mode | Verificar si upstream cron lo soporta | Media | Upstream cron NO tiene silent mode. Portar la lógica de `silent` flag en cron types y service. |
| I3 | `634d8944` log truncation cada 3h | Script operacional | Baja | Copiar script `nanobot-rotate-logs` (ya hecho ✅) |
| I4 | `e478a2aa` clear heartbeat session | Verificar si upstream heartbeat tiene overflow protection | Baja | Upstream heartbeat no tiene clear explícito. Portar si sigue siendo necesario. |
| I5 | `35293698` message send retry | Verificar si upstream base channel tiene retry | Baja | Upstream tiene retry mencionado en base.py. Verificar si es suficiente. |
| I6 | `6a55f5b0` custom_provider truncate error | **NO PORTAR** — upstream usa openai_compat_provider | N/A | Nuestro custom_provider es redundante. |
| I7 | `36f6c24c` memory reserve completion headroom | Verificar si upstream dream tiene esto | Baja | Probablemente cubierto por el nuevo dream system. |

### 🟢 MENORES — Nice to have

| # | Commit | Qué portar | Complejidad |
|---|---|---|---|
| M1 | `cd615658` mejoras email/whatsapp/fecha | Revisar qué queda sin cubrir | Baja |
| M2 | `19d1ee37` identity: empleado digital | Personalización de SOUL.md (workspace, no código) | N/A |
| M3 | `ae488660` Claudio identity | Personalización de SOUL.md (workspace, no código) | N/A |
| M4 | `4774dac9` templates: email rules | Personalización de AGENTS.md (workspace, no código) | N/A |
| M5 | `7f874c87` + `b2439fe7` scripts nanobot-restart/logs | Ya copiados ✅ | Baja |
| M6 | `416a3cf8` reinstall deps on restart | Verificar si nanobot-restart lo necesita | Baja |
| M7 | `8631a93d` pytest via .venv | Verificar si nanobot-restart lo necesita | Baja |
| M8 | `67aaf118` + `7bde1667` pre-release tests on restart | Portar a nanobot-restart si queremos | Baja |
| M9 | `f7a0b504` message tool media description | Verificar si upstream ya lo tiene | Baja |

### ❌ NO PORTAR — Obsoletos o revertidos

| # | Commit | Razón |
|---|---|---|
| X1 | `731972e9` remove wa_bridge tools | Ya no aplica — usamos WAHA MCP |
| X2 | `7e18af23` wa_bridge_enviar_mensaje tool | Ya no aplica — usamos WAHA MCP |
| X3 | `4605e487` WhatsApp read/search via bridge | Ya no aplica — usamos WAHA MCP |
| X4 | `ed3cb637` store propio en bridge | Ya no aplica — usamos WAHA MCP |
| X5 | WhatsApp proxy (3 commits + revert) | Revertido por nosotros mismos |
| X6 | `6df68cdf` merge upstream v0.1.4.post5 | Merge commit — no aplica |
| X7 | `ff1d6684` upstream sync non-conflicting | Sync commit — ya incluido |

---

## RESUMEN EJECUTIVO

| Categoría | Total commits | Acción |
|---|---|---|
| ✅ Ya en upstream | **48** | No hacer nada |
| ✅ Ya portados | **5** (C1-C5) | Hecho en primer commit |
| 🟡 Portar | **5** (I1-I5) | Trabajo pendiente |
| ❌ No portar | **7** (X1-X7) | Obsoletos |
| 🟢 Menores | **9** (M1-M9) | Opcional, workspace config |
| **TOTAL** | **81** | |

### Trabajo real pendiente:
1. **I2: Silent cron mode** — Añadir flag `silent` a cron types y service (~30 min)
2. **I1: Memory consolidation** — Evaluar si el "dream" system de upstream cubre nuestras necesidades. Si no, adaptar (~2-3h)
3. **I4: Heartbeat session clear** — Pequeño fix (~15 min)
4. **I5: Message retry** — Verificar si upstream ya lo cubre (~15 min)
5. **M6-M8: Scripts restart** — Actualizar nanobot-restart (~30 min)

### Features NUEVAS que ganamos de upstream:
- 🆕 **Goals / Long Tasks** — Tareas de larga duración con estado persistente
- 🆕 **Pairing** — Control de acceso por pairing code
- 🆕 **WebUI** — Interfaz web para chat
- 🆕 **Brave Search** — Mejor que Serper/Firecrawl
- 🆕 **Dream System** — Consolidación de memoria más sofisticada
- 🆕 **Atomic Chat** — Provider local OpenAI-compatible
- 🆕 **Prompt templates** — Sistema de templates Jinja2
- 🆕 **v0.2.0** — Wheel packaging, mejor CI
