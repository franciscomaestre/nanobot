"""DataFact monitoring tools — importadores, descargas SRI y scripts.

Estas tools envuelven queries MySQL específicas usando el MCP de mysql
(mcp_mysql_mysql_query) que ya está registrado en el agente.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from nanobot.agent.tools.base import Tool

if TYPE_CHECKING:
    from nanobot.agent.tools.registry import ToolRegistry


class ObtenerAvancesImportadoresTool(Tool):
    """Retorna los últimos registros de avance de los procesos de importación."""

    name = "obtener_avances_importadores"
    description = (
        "Retorna los registros almacenados en la tabla de logs de la base de datos, "
        "donde se registran los avances de los procesos de importación. "
        "No requiere parámetros de entrada y devuelve una lista de registros con la "
        "información registrada por los importadores, incluyendo fecha, estado y posibles errores.\n\n"
        "Ejemplo: \"Dime el estado actual de los procesos de importación.\""
    )
    parameters: dict = {"type": "object", "properties": {}, "required": []}

    def __init__(self, registry: "ToolRegistry"):
        self._registry = registry

    async def execute(self, **kwargs: Any) -> str:
        tool = self._registry.get("mcp_mysql_mysql_query")
        if not tool:
            return "Error: mcp_mysql_mysql_query no disponible."
        return await tool.execute(
            sql="SELECT * FROM auditoria_logs_bases ORDER BY fecha DESC LIMIT 16"
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
        "Ejemplo: \"Dime cómo va el sistema de descargas del SRI.\""
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

    def __init__(self, registry: "ToolRegistry"):
        self._registry = registry

    async def execute(self, **kwargs: Any) -> str:
        tool = self._registry.get("mcp_mysql_mysql_query")
        if not tool:
            return "Error: mcp_mysql_mysql_query no disponible."
        return await tool.execute(sql=self._SQL)


class ObtenerAnalisisFuncionamientoScriptsTool(Tool):
    """Logs de funcionamiento de los scripts ejecutados en los servidores."""

    name = "obtener_analisis_funcionamiento_scripts"
    description = (
        "Obtiene los logs de funcionamiento de los scripts que se están ejecutando en los servidores. "
        "Devuelve los registros de los últimos 2 días. "
        "Si no hay detalle de falla, el script ha funcionado correctamente.\n\n"
        "Ejemplo: \"¿Los scripts están funcionando correctamente? Muéstrame el análisis.\""
    )
    parameters: dict = {"type": "object", "properties": {}, "required": []}

    def __init__(self, registry: "ToolRegistry"):
        self._registry = registry

    async def execute(self, **kwargs: Any) -> str:
        tool = self._registry.get("mcp_mysql_mysql_query")
        if not tool:
            return "Error: mcp_mysql_mysql_query no disponible."
        return await tool.execute(
            sql=(
                "SELECT * FROM auditoria_logs_scripts "
                "WHERE fecha_actualizacion > (CURDATE() - INTERVAL 2 DAY) "
                "ORDER BY fecha_actualizacion DESC"
            )
        )
