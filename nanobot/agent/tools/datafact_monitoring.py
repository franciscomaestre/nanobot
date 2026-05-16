"""DataFact monitoring tools — importadores, descargas SRI y scripts.

These are standalone tools that return pre-defined SQL queries for the agent
to understand. The actual SQL execution happens via the MCP mysql_query tool
which the agent calls separately.

In v0.2.0, tools use Tool.create(ctx) → cls() so they must not require
constructor arguments beyond what the base Tool provides.
"""

from __future__ import annotations

from typing import Any

from nanobot.agent.tools.base import Tool


class ObtenerAvancesImportadoresTool(Tool):
    """Retorna los últimos registros de avance de los procesos de importación."""

    name = "obtener_avances_importadores"
    description = (
        "Retorna los registros almacenados en la tabla de logs de la base de datos, "
        "donde se registran los avances de los procesos de importación. "
        "No requiere parámetros de entrada y devuelve una lista de registros con la "
        "información registrada por los importadores, incluyendo fecha, estado y posibles errores.\n\n"
        'Ejemplo: "Dime el estado actual de los procesos de importación."'
    )
    parameters: dict = {"type": "object", "properties": {}, "required": []}

    async def execute(self, **kwargs: Any) -> str:
        return (
            "[INSTRUCCIÓN INTERNA] Ejecuta mcp_data-fact_mysql_query con este SQL:\n\n"
            "SELECT * FROM auditoria_logs_bases ORDER BY fecha DESC LIMIT 16"
        )


class ObtenerAnalisisSistemaDescargasFacturasSRITool(Tool):
    """Análisis del comportamiento reciente del sistema de descargas de facturas del SRI."""

    name = "obtener_analisis_sistema_descargas_facturas_sri"
    description = (
        "Obtiene un análisis del comportamiento reciente del sistema de descargas de facturas del SRI. "
        "Devuelve cinco métricas clave:\n"
        "- total_actual_en_millones: total registrado en el último log disponible.\n"
        "- incremento_24_horas_en_millones: diferencia entre el total actual y el registrado ayer.\n"
        "- total_hace_un_mes_en_millones: total correspondiente exactamente a la fecha de hace un mes.\n"
        "- diferencia_para_misma_fecha_en_millones: diferencia entre el total actual y el de hace un mes.\n"
        "- incremento_24_48_horas_en_millones: diferencia entre el total registrado ayer y el de anteayer.\n\n"
        "Permite monitorear tendencias diarias y mensuales en las descargas del sistema, "
        "útil para detectar cambios, anomalías o mejoras en el rendimiento.\n\n"
        'Ejemplo: "Dime cómo va el sistema de descargas del SRI."'
    )
    parameters: dict = {"type": "object", "properties": {}, "required": []}

    _SQL = """
SELECT
  ROUND((
    SELECT total FROM auditoria_logs_descargas
    WHERE autor = 'CONTROL SEMILLAS'
    ORDER BY fecha DESC LIMIT 1
  ), 2) AS total_actual_en_millones,

  ROUND((
    (SELECT total FROM auditoria_logs_descargas
     WHERE autor = 'CONTROL SEMILLAS'
     ORDER BY fecha DESC LIMIT 1)
    -
    (SELECT total FROM auditoria_logs_descargas
     WHERE autor = 'CONTROL SEMILLAS'
       AND fecha <= NOW() - INTERVAL 29 HOUR
     ORDER BY fecha DESC LIMIT 1)
  ), 2) AS incremento_24_horas_en_millones,

  ROUND((
    SELECT total FROM auditoria_logs_descargas
    WHERE autor = 'CONTROL SEMILLAS'
      AND DATE(fecha) = CURDATE() - INTERVAL 1 MONTH
    ORDER BY fecha DESC LIMIT 1
  ), 2) AS total_hace_un_mes_en_millones,

  ROUND((
    (SELECT total FROM auditoria_logs_descargas
     WHERE autor = 'CONTROL SEMILLAS'
     ORDER BY fecha DESC LIMIT 1)
    -
    (SELECT total FROM auditoria_logs_descargas
     WHERE autor = 'CONTROL SEMILLAS'
       AND DATE(fecha) = CURDATE() - INTERVAL 1 MONTH
     ORDER BY fecha DESC LIMIT 1)
  ), 2) AS diferencia_para_misma_fecha_en_millones,

  ROUND((
    (SELECT total FROM auditoria_logs_descargas
     WHERE autor = 'CONTROL SEMILLAS'
       AND fecha <= NOW() - INTERVAL 29 HOUR
     ORDER BY fecha DESC LIMIT 1)
    -
    (SELECT total FROM auditoria_logs_descargas
     WHERE autor = 'CONTROL SEMILLAS'
       AND fecha <= NOW() - INTERVAL 52 HOUR
     ORDER BY fecha DESC LIMIT 1)
  ), 2) AS incremento_24_48_horas_en_millones
"""

    async def execute(self, **kwargs: Any) -> str:
        return (
            "[INSTRUCCIÓN INTERNA] Ejecuta mcp_data-fact_mysql_query con este SQL:\n\n"
            + self._SQL
        )


class ObtenerAnalisisFuncionamientoScriptsTool(Tool):
    """Logs de funcionamiento de los scripts ejecutados en los servidores."""

    name = "obtener_analisis_funcionamiento_scripts"
    description = (
        "Obtiene los logs de funcionamiento de los scripts que se están ejecutando en los servidores. "
        "Devuelve los registros de los últimos 2 días. "
        "Si no hay detalle de falla, el script ha funcionado correctamente.\n\n"
        'Ejemplo: "¿Los scripts están funcionando correctamente? Muéstrame el análisis."'
    )
    parameters: dict = {"type": "object", "properties": {}, "required": []}

    async def execute(self, **kwargs: Any) -> str:
        return (
            "[INSTRUCCIÓN INTERNA] Ejecuta mcp_data-fact_mysql_query con este SQL:\n\n"
            "SELECT * FROM auditoria_logs_scripts "
            "WHERE fecha_actualizacion > (CURDATE() - INTERVAL 2 DAY) "
            "ORDER BY fecha_actualizacion DESC"
        )
