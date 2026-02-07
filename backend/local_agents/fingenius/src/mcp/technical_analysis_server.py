from local_agents.fingenius.src.mcp.server import MCPServer
from local_agents.fingenius.src.tool import Terminate
from local_agents.fingenius.src.tool.technical_analysis import TechnicalAnalysisTool


class TechnicalAnalysisServer(MCPServer):
    def __init__(self, name: str = "TechnicalAnalysisServer"):
        super().__init__(name)

    def _initialize_standard_tools(self) -> None:
        self.tools.update(
            {
                "technical_analysis_tool": TechnicalAnalysisTool(),
                "terminate": Terminate(),
            }
        )
