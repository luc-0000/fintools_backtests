from local_agents.fingenius.src.mcp.server import MCPServer
from local_agents.fingenius.src.tool import Terminate
from local_agents.fingenius.src.tool.sentiment import SentimentTool
from local_agents.fingenius.src.tool.web_search import WebSearch


class SentimentServer(MCPServer):
    def __init__(self, name: str = "SentimentServer"):
        super().__init__(name)

    def _initialize_standard_tools(self) -> None:
        self.tools.update(
            {
                "sentiment_tool": SentimentTool(),
                "web_search": WebSearch(),
                "terminate": Terminate(),
            }
        )
