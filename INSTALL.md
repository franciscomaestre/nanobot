# Guía de Instalación — data-fact-nanobot

Versión personalizada de [nanobot](https://github.com/HKUDS/nanobot) con soporte para WhatsApp, Nylas (email + calendario), MCPs de Ecuador APIs y MySQL, transcripción de audio, y personalidad configurable vía SOUL.md.

---

## Requisitos previos

| Componente | Versión mínima |
|---|---|
| Python | 3.11+ |
| Node.js | 18+ |
| npm | 9+ |
| git | cualquiera |

---

## 1. Clonar el repositorio

```bash
git clone https://bitbucket.org/data-fact/data-fact-nanobot.git
cd data-fact-nanobot
git checkout claudio   # rama con todas las personalizaciones
```

---

## 2. Instalar dependencias Python

```bash
pip install -e .
```

Esto instala el paquete `nanobot-ai` en modo editable junto con todas sus dependencias (litellm, pydantic, websockets, httpx, openai, mcp, etc.).

Dependencias adicionales usadas por los MCPs y el canal WhatsApp:

```bash
pip install requests boto3 fastmcp httpx
```

---

## 3. Compilar el bridge de WhatsApp (Node.js)

El bridge conecta nanobot con WhatsApp Web vía Baileys.

```bash
cd bridge
npm install
npm run build
cd ..
```

Esto genera `bridge/dist/` con los archivos compilados.

---

## 4. Configurar nanobot

### 4.1 Crear el directorio de configuración

```bash
mkdir -p ~/.nanobot/workspace/memory
mkdir -p ~/.nanobot/workspace/skills
```

### 4.2 Crear `~/.nanobot/config.json`

Copia la plantilla y rellena con tus credenciales:

```json
{
  "agents": {
    "defaults": {
      "workspace": "~/.nanobot/workspace",
      "model": "anthropic/claude-sonnet-4-6",
      "provider": "anthropic",
      "maxTokens": 8192,
      "contextWindowTokens": 100000,
      "temperature": 0.1,
      "maxToolIterations": 40,
      "reasoningEffort": null,
      "fallbackModel": "anthropic/claude-haiku-4-5",
      "consolidationModel": "anthropic/claude-haiku-4-5"
    }
  },
  "channels": {
    "sendProgress": true,
    "sendToolHints": false,
    "whatsapp": {
      "enabled": true,
      "bridgeUrl": "ws://localhost:3001",
      "bridgeToken": "",
      "allowFrom": ["+593XXXXXXXXX"],
      "transcriptionProvider": "assemblyai",
      "transcriptionApiKey": "TU_ASSEMBLYAI_KEY"
    },
    "telegram": {
      "enabled": false,
      "token": "",
      "allowFrom": []
    },
    "email": {
      "enabled": false,
      "consentGranted": true,
      "imapHost": "outlook.office365.com",
      "imapPort": 993,
      "imapUsername": "tu@correo.com",
      "imapPassword": "TU_PASSWORD",
      "imapUseSsl": true,
      "smtpHost": "smtp.office365.com",
      "smtpPort": 587,
      "smtpUsername": "tu@correo.com",
      "smtpPassword": "TU_PASSWORD",
      "smtpUseTls": true,
      "smtpUseSsl": false,
      "fromAddress": "tu@correo.com",
      "autoReplyEnabled": true,
      "pollIntervalSeconds": 30,
      "allowFrom": ["@tudominio.com"]
    }
  },
  "providers": {
    "anthropic": {
      "apiKey": "sk-ant-..."
    },
    "openai": {
      "apiKey": "sk-proj-..."
    }
  },
  "gateway": {
    "host": "0.0.0.0",
    "port": 18790,
    "heartbeat": {
      "enabled": true,
      "intervalS": 1800
    }
  },
  "tools": {
    "web": {
      "search": {
        "provider": "firecrawl",
        "apiKey": "fc-...",
        "maxResults": 5
      }
    },
    "exec": {
      "timeout": 60
    },
    "restrictToWorkspace": false,
    "nylas": {
      "grantId": "TU_NYLAS_GRANT_ID",
      "apiKey": "nyk_v0_...",
      "apiRegion": "us"
    },
    "mcpServers": {
      "ecuador-apis": {
        "type": "stdio",
        "command": "python3",
        "args": ["/RUTA/ABSOLUTA/data-fact-mcp-iniciativas/server.py"],
        "enabledTools": ["*"],
        "toolTimeout": 60
      }
    }
  }
}
```

> ⚠️ Protege el archivo: `chmod 600 ~/.nanobot/config.json`

---

## 5. Instalar el MCP de Ecuador APIs

```bash
git clone https://bitbucket.org/data-fact/data-fact-mcp-iniciativas.git
cd data-fact-mcp-iniciativas
pip install -r requirements.txt
```

Luego actualiza la ruta en `config.json`:

```json
"args": ["/ruta/a/data-fact-mcp-iniciativas/server.py"]
```

---

## 6. Configurar el workspace

### 6.1 Archivos de identidad y comportamiento

Al iniciar por primera vez, nanobot crea automáticamente los archivos base en `~/.nanobot/workspace/`. Puedes editarlos antes o después del primer arranque:

| Archivo | Propósito |
|---|---|
| `AGENTS.md` | Instrucciones de comportamiento del agente |
| `SOUL.md` | **Personalidad e identidad** (ver sección 7) |
| `USER.md` | Perfil del usuario (nombre, correo, preferencias) |
| `TOOLS.md` | Notas de uso de herramientas |
| `HEARTBEAT.md` | Tareas periódicas automáticas |
| `memory/MEMORY.md` | Memoria de largo plazo (el agente escribe aquí) |
| `memory/HISTORY.md` | Log de interacciones (append-only) |

### 6.2 Primer arranque (onboarding)

```bash
nanobot onboard
```

Esto crea la estructura de workspace con los templates por defecto.

---

## 7. Personalizar el SOUL.md (identidad del agente)

El archivo `~/.nanobot/workspace/SOUL.md` define quién es el agente: su nombre, propósito, personalidad y estilo de comunicación. **Es el archivo más importante para personalizar la experiencia.**

### Edición manual

```bash
nano ~/.nanobot/workspace/SOUL.md
```

### Edición desde el chat

El agente tiene acceso a sus propios archivos de workspace mediante las herramientas `write_file` y `edit_file`. Puedes pedirle directamente:

> *"Modifica tu SOUL.md para que te presentes como [nombre] y trabajes para [empresa]"*

El agente leerá el archivo actual, aplicará los cambios y los guardará. Los cambios toman efecto en el **siguiente mensaje** (el SOUL.md se carga en cada conversación).

### Ejemplo de SOUL.md personalizado

```markdown
# Soul

Mi nombre es [Nombre]. Trabajo como asistente personal de [Empresa/Persona].

## Identidad
- **Nombre**: [Nombre]
- **Correo**: correo@empresa.com
- **Rol**: Asistente de [descripción]

## Propósito
Apoyar a las personas que me contactan en sus tareas diarias.

## Personalidad
- Amable y directo
- Proactivo
- Preciso

## Estilo de comunicación
- Respondo en el idioma del usuario
- Tono profesional pero cercano
```

> **Nota**: Los cambios al SOUL.md son persistentes entre reinicios. No se necesita reiniciar nanobot para que tomen efecto — se aplican desde el siguiente mensaje.

---

## 8. Instalar scripts de gestión

El repo incluye dos scripts en `scripts/` que facilitan la operación diaria:

```bash
cp scripts/nanobot-restart scripts/nanobot-logs ~/.local/bin/
chmod +x ~/.local/bin/nanobot-restart ~/.local/bin/nanobot-logs
```

Asegúrate de que `~/.local/bin` está en el PATH (en `~/.zshrc` o `~/.bashrc`):

```bash
export PATH="$HOME/.local/bin:$PATH"
```

**`nanobot-restart`** — para bridge + gateway juntos (único comando para reinicios):
```bash
nanobot-restart           # restart normal
nanobot-restart --force   # reinstala pip + recompila bridge
nanobot-restart --logs    # muestra logs en vivo tras arrancar
```

**`nanobot-logs`** — monitoriza los logs en tiempo real:
```bash
nanobot-logs          # gateway + bridge en paralelo (coloreado)
nanobot-logs gateway  # solo nanobot
nanobot-logs bridge   # solo el bridge de WhatsApp
```

---

## 9. Arrancar nanobot

### Primera vez (escanear QR de WhatsApp)

La primera vez hay que arrancar el bridge manualmente para ver el QR:

```bash
cd /ruta/a/data-fact-nanobot/bridge
node dist/index.js
```

Escanea el QR con WhatsApp → Dispositivos vinculados. Luego Ctrl+C y usa `nanobot-restart` para el arranque normal.

### Arranque normal (y cualquier reinicio posterior)

```bash
nanobot-restart
```

Esto inicia el bridge y el gateway en el orden correcto, con logs en `~/.nanobot/logs/`.

---

## 9. Verificar que funciona

Envía un mensaje de WhatsApp desde el número configurado en `allowFrom`. Deberías recibir respuesta.

Para verificar el estado:

```bash
nanobot status
```

---

## 10. Estructura de directorios resultante

```
~/.nanobot/
├── config.json                  # Configuración principal (credenciales, canales, modelos)
├── bridge/                      # Sesión de WhatsApp (auth de Baileys)
│   └── auth/
└── workspace/
    ├── AGENTS.md                # Instrucciones del agente
    ├── SOUL.md                  # Identidad y personalidad ← editar aquí
    ├── USER.md                  # Perfil del usuario
    ├── TOOLS.md                 # Guía de herramientas
    ├── HEARTBEAT.md             # Tareas periódicas
    ├── memory/
    │   ├── MEMORY.md            # Memoria de largo plazo
    │   └── HISTORY.md           # Log de interacciones
    └── skills/
        ├── email/SKILL.md
        ├── whatsapp-proxy/SKILL.md
        └── ...

/ruta/a/data-fact-nanobot/       # Código fuente (rama claudio)
/ruta/a/data-fact-mcp-iniciativas/  # MCP Ecuador APIs
```

---

## 11. Solución de problemas comunes

### WhatsApp no conecta
- Verificar que el bridge esté corriendo antes de `nanobot gateway`
- Revisar que `bridgeUrl` en config.json apunte a `ws://localhost:3001`
- Si el QR expiró, reiniciar el bridge

### Mensajes no llegan
- Verificar que el número esté en `allowFrom` (con y sin `+` si es necesario)
- Revisar logs del bridge y de nanobot

### MCP no carga
- Verificar que la ruta en `args` sea absoluta y correcta
- Probar manualmente: `python3 /ruta/server.py`
- Verificar que las dependencias del MCP estén instaladas

### Error de modelo
- Verificar que la API key de Anthropic esté correcta en `providers.anthropic.apiKey`
- El modelo `anthropic/claude-sonnet-4-6` requiere acceso a la API de Anthropic

---

## 12. Actualizar desde upstream

```bash
git checkout main
git pull upstream main
git checkout claudio
git rebase main
```

Ver `SYNC.md` para el proceso completo de sincronización.
