"""Nylas integration tools: email and calendar via Nylas API v3."""

from __future__ import annotations

import base64
import json
import mimetypes
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import httpx
from loguru import logger

from nanobot.agent.tools.base import Tool

if TYPE_CHECKING:
    from nanobot.config.schema import NylasConfig

_TIMEOUT = 30.0


def _base_url(region: str) -> str:
    region = (region or "us").lower()
    return f"https://api.{region}.nylas.com/v3"


def _headers(api_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def _ts(dt_str: str) -> int | None:
    """Parse ISO-8601 datetime string → Unix timestamp. Returns None on failure."""
    if not dt_str:
        return None
    dt_str = dt_str.strip()
    import re
    dt_str = re.sub(r"([+-]\d{2}):(\d{2})$", r"\1\2", dt_str)
    formats = [
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M%z",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%d",
    ]
    for fmt in formats:
        try:
            return int(datetime.strptime(dt_str, fmt).timestamp())
        except ValueError:
            continue
    try:
        from dateutil import parser as dtparser
        return int(dtparser.parse(dt_str).timestamp())
    except Exception:
        return None


def _clean_html(text: str) -> str:
    """Strip HTML tags and collapse whitespace."""
    import re
    import html as html_mod
    text = re.sub(r"<[^>]+>", " ", text)
    text = html_mod.unescape(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


# ── Email tools ───────────────────────────────────────────────────────────────

class NylasEmailListTool(Tool):
    """List recent emails, optionally filtered by sender or subject."""

    name = "nylas_email_list"
    description = (
        "Lists recent emails from the inbox. Optionally filter by sender address or subject keyword. "
        "Returns subject, sender, date, snippet and message ID for each email."
    )
    parameters = {
        "type": "object",
        "properties": {
            "limit": {"type": "integer", "description": "Max emails to return (default 10, max 50)", "minimum": 1, "maximum": 50},
            "from_filter": {"type": "string", "description": "Filter by sender email address"},
            "subject_filter": {"type": "string", "description": "Filter by subject keyword"},
        },
        "required": [],
    }

    def __init__(self, config: NylasConfig):
        self._config = config

    async def execute(self, limit: int = 10, from_filter: str | None = None, subject_filter: str | None = None, **kwargs: Any) -> str:
        params: dict[str, Any] = {"limit": min(limit, 50)}
        if from_filter:
            params["from"] = from_filter
        if subject_filter:
            params["subject"] = subject_filter

        url = f"{_base_url(self._config.api_region)}/grants/{self._config.grant_id}/messages"
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                r = await client.get(url, headers=_headers(self._config.api_key), params=params)
                r.raise_for_status()
            emails = r.json().get("data", [])
            if not emails:
                return "No emails found."
            lines = []
            for m in emails:
                sender = (m.get("from") or [{}])[0]
                ts = m.get("date") or 0
                date_str = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M") if ts else "?"
                lines.append(
                    f"ID: {m.get('id','?')}\n"
                    f"  From: {sender.get('name','')} <{sender.get('email','')}>\n"
                    f"  Subject: {m.get('subject','(no subject)')}\n"
                    f"  Date: {date_str}\n"
                    f"  Snippet: {(m.get('snippet') or '')[:120]}"
                )
            return f"Found {len(lines)} email(s):\n\n" + "\n\n".join(lines)
        except Exception as e:
            logger.error("nylas_email_list error: {}", e)
            return f"Error: {e}"


class NylasEmailSearchTool(Tool):
    """Search emails by free-text query."""

    name = "nylas_email_search"
    description = (
        "Searches emails using a free-text query (supports Gmail/Outlook native search syntax). "
        "Examples: 'factura enero', 'from:pepe@empresa.com', 'subject:reunión'. "
        "Returns subject, sender, date and message ID."
    )
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query (free text or provider-native syntax)"},
            "limit": {"type": "integer", "description": "Max results (default 10)", "minimum": 1, "maximum": 50},
        },
        "required": ["query"],
    }

    def __init__(self, config: NylasConfig):
        self._config = config

    async def execute(self, query: str, limit: int = 10, **kwargs: Any) -> str:
        url = f"{_base_url(self._config.api_region)}/grants/{self._config.grant_id}/messages"
        params = {"limit": min(limit, 50), "search_query_native": query}
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                r = await client.get(url, headers=_headers(self._config.api_key), params=params)
                r.raise_for_status()
            emails = r.json().get("data", [])
            if not emails:
                return f"No emails found for query: {query}"
            lines = []
            for m in emails:
                sender = (m.get("from") or [{}])[0]
                ts = m.get("date") or 0
                date_str = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M") if ts else "?"
                lines.append(
                    f"ID: {m.get('id','?')}\n"
                    f"  From: {sender.get('name','')} <{sender.get('email','')}>\n"
                    f"  Subject: {m.get('subject','(no subject)')}\n"
                    f"  Date: {date_str}\n"
                    f"  Snippet: {(m.get('snippet') or '')[:120]}"
                )
            return f"Found {len(lines)} email(s) for '{query}':\n\n" + "\n\n".join(lines)
        except Exception as e:
            logger.error("nylas_email_search error: {}", e)
            return f"Error: {e}"


class NylasEmailGetTool(Tool):
    """Get the full body of an email by message ID."""

    name = "nylas_email_get"
    description = (
        "Retrieves the full content of an email given its message ID. "
        "Use nylas_email_list or nylas_email_search first to get the ID."
    )
    parameters = {
        "type": "object",
        "properties": {
            "message_id": {"type": "string", "description": "The Nylas message ID"},
        },
        "required": ["message_id"],
    }

    def __init__(self, config: NylasConfig):
        self._config = config

    async def execute(self, message_id: str, **kwargs: Any) -> str:
        url = f"{_base_url(self._config.api_region)}/grants/{self._config.grant_id}/messages/{message_id}"
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                r = await client.get(url, headers=_headers(self._config.api_key))
                r.raise_for_status()
            m = r.json().get("data", {})
            sender = (m.get("from") or [{}])[0]
            ts = m.get("date") or 0
            date_str = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M") if ts else "?"
            body = _clean_html(m.get("body") or m.get("snippet") or "(empty)")
            body = body[:8000]
            return (
                f"From: {sender.get('name','')} <{sender.get('email','')}>\n"
                f"Subject: {m.get('subject','(no subject)')}\n"
                f"Date: {date_str}\n\n"
                f"{body}"
            )
        except Exception as e:
            logger.error("nylas_email_get error: {}", e)
            return f"Error: {e}"


class NylasAttachmentMetadataTool(Tool):
    """Get metadata for all attachments in a message."""

    name = "nylas_attachment_get_metadata"
    description = (
        "Returns metadata (id, filename, content_type, size) for all attachments "
        "in a given email message. Use nylas_email_get first to confirm the message has attachments."
    )
    parameters = {
        "type": "object",
        "properties": {
            "message_id": {"type": "string", "description": "The Nylas message ID"},
        },
        "required": ["message_id"],
    }

    def __init__(self, config: NylasConfig):
        self._config = config

    async def execute(self, message_id: str, **kwargs: Any) -> str:
        url = f"{_base_url(self._config.api_region)}/grants/{self._config.grant_id}/messages/{message_id}"
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                r = await client.get(url, headers=_headers(self._config.api_key))
                r.raise_for_status()
            m = r.json().get("data", {})
            attachments = m.get("attachments") or []
            if not attachments:
                return "No attachments found in this message."
            lines = []
            for att in attachments:
                size_kb = round(att.get("size", 0) / 1024, 1)
                lines.append(
                    f"ID: {att.get('id', '?')}\n"
                    f"  Filename: {att.get('filename', '(unnamed)')}\n"
                    f"  Type: {att.get('content_type', '?')}\n"
                    f"  Size: {size_kb} KB"
                )
            return f"Found {len(lines)} attachment(s):\n\n" + "\n\n".join(lines)
        except Exception as e:
            logger.error("nylas_attachment_get_metadata error: {}", e)
            return f"Error: {e}"


class NylasAttachmentDownloadTool(Tool):
    """Download an attachment from an email and save it to the workspace."""

    name = "nylas_attachment_download"
    description = (
        "Downloads an email attachment by its attachment ID and saves it to the workspace. "
        "Use nylas_attachment_get_metadata first to get the attachment ID. "
        "Returns the local file path where the attachment was saved."
    )
    parameters = {
        "type": "object",
        "properties": {
            "attachment_id": {"type": "string", "description": "The attachment ID (from nylas_attachment_get_metadata)"},
            "message_id": {"type": "string", "description": "The Nylas message ID that contains the attachment"},
            "save_path": {"type": "string", "description": "Optional: local path to save the file. Defaults to workspace/downloads/<filename>"},
        },
        "required": ["attachment_id", "message_id"],
    }

    def __init__(self, config: NylasConfig, workspace_path: str | None = None):
        self._config = config
        self._workspace_path = workspace_path

    async def execute(self, attachment_id: str, message_id: str, save_path: str | None = None, **kwargs: Any) -> str:
        import urllib.parse

        # First get metadata to know the filename
        meta_url = f"{_base_url(self._config.api_region)}/grants/{self._config.grant_id}/messages/{message_id}"
        filename = "attachment"
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                r = await client.get(meta_url, headers=_headers(self._config.api_key))
                r.raise_for_status()
            m = r.json().get("data", {})
            for att in (m.get("attachments") or []):
                if att.get("id") == attachment_id:
                    filename = att.get("filename") or filename
                    break
        except Exception as e:
            logger.warning("Could not fetch attachment metadata: {}", e)

        # Build download URL — URL-encode the attachment_id to handle special chars
        encoded_id = urllib.parse.quote(attachment_id, safe="")
        download_url = (
            f"{_base_url(self._config.api_region)}/grants/{self._config.grant_id}"
            f"/attachments/{encoded_id}/download"
        )
        params = {"message_id": message_id}

        # Determine save path
        if save_path:
            dest = Path(save_path)
        else:
            base = Path(self._workspace_path).expanduser() if self._workspace_path else Path.home() / ".nanobot" / "workspace"
            dest = base / "downloads" / filename
        dest.parent.mkdir(parents=True, exist_ok=True)

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                r = await client.get(
                    download_url,
                    headers={k: v for k, v in _headers(self._config.api_key).items() if k != "Content-Type"},
                    params=params,
                )
                r.raise_for_status()
            dest.write_bytes(r.content)
            size_kb = round(len(r.content) / 1024, 1)
            return f"Attachment saved to: {dest}\nFilename: {filename}\nSize: {size_kb} KB"
        except Exception as e:
            logger.error("nylas_attachment_download error: {}", e)
            return f"Error downloading attachment: {e}"


def _format_body(body: str) -> str:
    """
    Convert plain text body to clean HTML email.
    - Blank lines → paragraph breaks
    - Single line breaks → <br>
    - '•' bullet lines → <ul><li>
    - No decorative borders, footers or branding
    """
    import re

    body = body.replace("\r\n", "\n").replace("\r", "\n")
    paragraphs = re.split(r"\n{2,}", body.strip())

    html_parts = []
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        lines = para.split("\n")
        # Bullet block: all lines start with bullet chars
        if all(l.strip().startswith(("•", "-", "*")) for l in lines if l.strip()):
            items = "".join(
                f'<li style="margin-bottom:5px">{l.lstrip("•-* ").strip()}</li>'
                for l in lines if l.strip()
            )
            html_parts.append(f'<ul style="padding-left:20px;margin:8px 0">{items}</ul>')
        else:
            # Bold if line is short and all caps (section header)
            formatted_lines = []
            for l in lines:
                if re.match(r"^[A-ZÁÉÍÓÚÑ\s\-_:]{4,}$", l.strip()) and len(l.strip()) < 60:
                    formatted_lines.append(f"<strong>{l}</strong>")
                else:
                    formatted_lines.append(l)
            para_html = "<br>\n".join(formatted_lines)
            html_parts.append(f'<p style="margin:0 0 14px 0;line-height:1.7">{para_html}</p>')

    content = "\n".join(html_parts)

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="font-family:Arial,sans-serif;font-size:14px;color:#222222;
             max-width:680px;margin:0 auto;padding:24px">
{content}
</body>
</html>"""


class NylasEmailSendTool(Tool):
    """Send an email to any address via Nylas."""

    name = "nylas_email_send"
    description = (
        "Sends an email to one or more recipients via Nylas. "
        "Can send proactively to any address (not just replies). "
        "Optionally include CC recipients or reply to an existing thread. "
        "IMPORTANT: The body must be well structured with proper line breaks and paragraphs. "
        "Use blank lines to separate sections. Use '•' for bullet points. "
        "Start with a greeting (e.g. 'Hola [nombre],'), then the content in clear paragraphs, "
        "and end with a closing (e.g. 'Saludos,'). Never send body as a single block of text."
    )
    parameters = {
        "type": "object",
        "properties": {
            "to": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "email": {"type": "string"},
                    },
                    "required": ["email"],
                },
                "description": "List of recipients: [{\"name\": \"...\", \"email\": \"...\"}]",
            },
            "subject": {"type": "string", "description": "Email subject"},
            "body": {
                "type": "string",
                "description": (
                    "Email body as plain text with proper formatting. "
                    "Use blank lines between paragraphs. "
                    "Use '•' for bullet lists. "
                    "Use ALL CAPS lines for section headers (e.g. 'RESUMEN', 'PRÓXIMOS PASOS'). "
                    "Always include greeting and sign-off."
                )
            },
            "cc": {
                "type": "array",
                "items": {"type": "object", "properties": {"name": {"type": "string"}, "email": {"type": "string"}}, "required": ["email"]},
                "description": "Optional CC recipients",
            },
            "reply_to_message_id": {"type": "string", "description": "Optional: Nylas message ID to reply to (maintains thread)"},
            "attachments": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional: list of local file paths to attach to the email",
            },
        },
        "required": ["to", "subject", "body"],
    }

    def __init__(self, config: NylasConfig):
        self._config = config

    async def execute(
        self,
        to: list[dict],
        subject: str,
        body: str,
        cc: list[dict] | None = None,
        reply_to_message_id: str | None = None,
        attachments: list[str] | None = None,
        **kwargs: Any,
    ) -> str:
        url = f"{_base_url(self._config.api_region)}/grants/{self._config.grant_id}/messages/send"
        html_body = _format_body(body)
        payload: dict[str, Any] = {"to": to, "subject": subject, "body": html_body}
        if cc:
            payload["cc"] = cc
        if reply_to_message_id:
            payload["reply_to_message_id"] = reply_to_message_id
        if attachments:
            encoded: list[dict[str, str]] = []
            skipped: list[str] = []
            for file_path in attachments:
                p = Path(file_path)
                if not p.exists():
                    skipped.append(file_path)
                    logger.warning("Nylas attachment not found: {}", file_path)
                    continue
                mime_type, _ = mimetypes.guess_type(str(p))
                content_type = mime_type or "application/octet-stream"
                encoded.append({
                    "filename": p.name,
                    "content_type": content_type,
                    "content": base64.b64encode(p.read_bytes()).decode("utf-8"),
                })
            if encoded:
                payload["attachments"] = encoded
            if skipped:
                logger.warning("Skipped missing attachments: {}", skipped)
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                r = await client.post(url, headers=_headers(self._config.api_key), json=payload)
                r.raise_for_status()
            msg_id = r.json().get("data", {}).get("id", "?")
            recipients = ", ".join(f"{t.get('name','')} <{t['email']}>" for t in to)
            attached_info = f" with {len(payload.get('attachments', []))} attachment(s)" if payload.get("attachments") else ""
            return f"Email sent successfully to {recipients}{attached_info}. Message ID: {msg_id}"
        except Exception as e:
            logger.error("nylas_email_send error: {}", e)
            return f"Error: {e}"


# ── Calendar tools ────────────────────────────────────────────────────────────

class NylasCalendarListEventsTool(Tool):
    """List calendar events between two dates."""

    name = "nylas_calendar_list_events"
    description = (
        "Lists Google Calendar events between two dates. "
        "Dates in ISO 8601 format with timezone (e.g. 2026-03-16T00:00:00-05:00) or YYYY-MM-DD. "
        "Returns title, start/end time, location, attendees and event ID."
    )
    parameters = {
        "type": "object",
        "properties": {
            "start": {"type": "string", "description": "Start datetime (ISO 8601 or YYYY-MM-DD)"},
            "end": {"type": "string", "description": "End datetime (ISO 8601 or YYYY-MM-DD)"},
            "calendar_id": {"type": "string", "description": "Calendar ID (default: 'primary')"},
        },
        "required": ["start", "end"],
    }

    def __init__(self, config: NylasConfig):
        self._config = config

    async def execute(self, start: str, end: str, calendar_id: str = "primary", **kwargs: Any) -> str:
        start_ts = _ts(start)
        end_ts = _ts(end)
        if not start_ts or not end_ts:
            return "Error: could not parse start or end datetime."
        if start_ts >= end_ts:
            return "Error: start must be before end."

        url = f"{_base_url(self._config.api_region)}/grants/{self._config.grant_id}/events"
        params = {"calendar_id": calendar_id, "start": start_ts, "end": end_ts}
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                r = await client.get(url, headers=_headers(self._config.api_key), params=params)
                r.raise_for_status()
            events = r.json().get("data", [])
            if not events:
                return f"No events found between {start} and {end}."
            lines = []
            for ev in events:
                when = ev.get("when", {})
                s = datetime.fromtimestamp(when.get("start_time", 0)).strftime("%Y-%m-%d %H:%M") if when.get("start_time") else "?"
                e = datetime.fromtimestamp(when.get("end_time", 0)).strftime("%Y-%m-%d %H:%M") if when.get("end_time") else "?"
                participants = ", ".join(p.get("email", "") for p in (ev.get("participants") or []))
                lines.append(
                    f"ID: {ev.get('id','?')}\n"
                    f"  Title: {ev.get('title','(no title)')}\n"
                    f"  Start: {s}  End: {e}\n"
                    f"  Location: {ev.get('location') or '-'}\n"
                    f"  Attendees: {participants or '-'}"
                )
            return f"Found {len(lines)} event(s):\n\n" + "\n\n".join(lines)
        except Exception as e:
            logger.error("nylas_calendar_list_events error: {}", e)
            return f"Error: {e}"


class NylasCalendarCreateEventTool(Tool):
    """Create a new calendar event."""

    name = "nylas_calendar_create_event"
    description = (
        "Creates a new event in Google Calendar. "
        "Dates in ISO 8601 format with timezone (e.g. 2026-03-20T10:00:00-05:00). "
        "Attendees receive an invitation email."
    )
    parameters = {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Event title"},
            "start": {"type": "string", "description": "Start datetime (ISO 8601)"},
            "end": {"type": "string", "description": "End datetime (ISO 8601)"},
            "description": {"type": "string", "description": "Optional event description"},
            "location": {"type": "string", "description": "Optional location"},
            "attendees": {
                "type": "array",
                "items": {"type": "object", "properties": {"name": {"type": "string"}, "email": {"type": "string"}}, "required": ["email"]},
                "description": "Optional list of attendees: [{\"name\": \"...\", \"email\": \"...\"}]",
            },
            "calendar_id": {"type": "string", "description": "Calendar ID (default: 'primary')"},
        },
        "required": ["title", "start", "end"],
    }

    def __init__(self, config: NylasConfig):
        self._config = config

    async def execute(
        self,
        title: str,
        start: str,
        end: str,
        description: str | None = None,
        location: str | None = None,
        attendees: list[dict] | None = None,
        calendar_id: str = "primary",
        **kwargs: Any,
    ) -> str:
        start_ts = _ts(start)
        end_ts = _ts(end)
        if not start_ts or not end_ts:
            return "Error: could not parse start or end datetime."

        payload: dict[str, Any] = {
            "title": title,
            "when": {"start_time": start_ts, "end_time": end_ts},
        }
        if description:
            payload["description"] = description
        if location:
            payload["location"] = location
        if attendees:
            payload["participants"] = [{"name": a.get("name", ""), "email": a["email"]} for a in attendees]

        url = f"{_base_url(self._config.api_region)}/grants/{self._config.grant_id}/events"
        params = {"calendar_id": calendar_id}
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                r = await client.post(url, headers=_headers(self._config.api_key), params=params, json=payload)
                r.raise_for_status()
            ev = r.json().get("data", {})
            return f"Event created: '{title}' (ID: {ev.get('id','?')}). Start: {start}, End: {end}."
        except Exception as e:
            logger.error("nylas_calendar_create_event error: {}", e)
            return f"Error: {e}"


class NylasCalendarUpdateEventTool(Tool):
    """Update an existing calendar event."""

    name = "nylas_calendar_update_event"
    description = (
        "Updates an existing calendar event by ID. "
        "Only the fields you provide will be changed. "
        "Use nylas_calendar_list_events to get the event ID first."
    )
    parameters = {
        "type": "object",
        "properties": {
            "event_id": {"type": "string", "description": "The Nylas event ID"},
            "calendar_id": {"type": "string", "description": "Calendar ID (default: 'primary')"},
            "title": {"type": "string", "description": "New title"},
            "start": {"type": "string", "description": "New start datetime (ISO 8601)"},
            "end": {"type": "string", "description": "New end datetime (ISO 8601)"},
            "description": {"type": "string", "description": "New description"},
            "location": {"type": "string", "description": "New location"},
        },
        "required": ["event_id"],
    }

    def __init__(self, config: NylasConfig):
        self._config = config

    async def execute(
        self,
        event_id: str,
        calendar_id: str = "primary",
        title: str | None = None,
        start: str | None = None,
        end: str | None = None,
        description: str | None = None,
        location: str | None = None,
        **kwargs: Any,
    ) -> str:
        payload: dict[str, Any] = {}
        if title:
            payload["title"] = title
        if description:
            payload["description"] = description
        if location:
            payload["location"] = location
        if start or end:
            when: dict[str, Any] = {}
            if start:
                ts = _ts(start)
                if ts:
                    when["start_time"] = ts
            if end:
                ts = _ts(end)
                if ts:
                    when["end_time"] = ts
            if when:
                payload["when"] = when

        if not payload:
            return "Error: no fields to update provided."

        url = f"{_base_url(self._config.api_region)}/grants/{self._config.grant_id}/events/{event_id}"
        params = {"calendar_id": calendar_id}
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                r = await client.put(url, headers=_headers(self._config.api_key), params=params, json=payload)
                r.raise_for_status()
            return f"Event {event_id} updated successfully."
        except Exception as e:
            logger.error("nylas_calendar_update_event error: {}", e)
            return f"Error: {e}"


class NylasCalendarDeleteEventTool(Tool):
    """Delete a calendar event."""

    name = "nylas_calendar_delete_event"
    description = (
        "Deletes a calendar event by ID. This action is irreversible. "
        "Use nylas_calendar_list_events to get the event ID first."
    )
    parameters = {
        "type": "object",
        "properties": {
            "event_id": {"type": "string", "description": "The Nylas event ID to delete"},
            "calendar_id": {"type": "string", "description": "Calendar ID (default: 'primary')"},
        },
        "required": ["event_id"],
    }

    def __init__(self, config: NylasConfig):
        self._config = config

    async def execute(self, event_id: str, calendar_id: str = "primary", **kwargs: Any) -> str:
        url = f"{_base_url(self._config.api_region)}/grants/{self._config.grant_id}/events/{event_id}"
        params = {"calendar_id": calendar_id}
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                r = await client.delete(url, headers=_headers(self._config.api_key), params=params)
                r.raise_for_status()
            return f"Event {event_id} deleted successfully."
        except Exception as e:
            logger.error("nylas_calendar_delete_event error: {}", e)
            return f"Error: {e}"


# ── Factory ───────────────────────────────────────────────────────────────────

def make_nylas_tools(config: NylasConfig, workspace_path: str | None = None) -> list[Tool]:
    """Return all Nylas tools configured with the given config."""
    return [
        NylasEmailListTool(config),
        NylasEmailSearchTool(config),
        NylasEmailGetTool(config),
        NylasEmailSendTool(config),
        NylasAttachmentMetadataTool(config),
        NylasAttachmentDownloadTool(config, workspace_path=workspace_path),
        NylasCalendarListEventsTool(config),
        NylasCalendarCreateEventTool(config),
        NylasCalendarUpdateEventTool(config),
        NylasCalendarDeleteEventTool(config),
    ]
