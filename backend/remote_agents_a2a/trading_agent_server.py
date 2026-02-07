import uvicorn
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
)
from common.consts import Agents
from remote_agents_a2a.streaming_agent_executor import StreamingAgentExecutor


def run_trading_agent_server(agent_name):

    # This will be the public-facing agent card
    public_agent_card = AgentCard(
        name='Hello World Agent',
        description='Just a hello world agent',
        url='http://localhost:9999/',
        version='1.0.0',
        default_input_modes=['text'],
        default_output_modes=['text'],
        capabilities=AgentCapabilities(streaming=True),
        skills=[],  # Only the basic skill for the public card
        supports_authenticated_extended_card=True,
    )

    request_handler = DefaultRequestHandler(
        agent_executor=StreamingAgentExecutor(agent_name),
        task_store=InMemoryTaskStore(),
    )

    server = A2AStarletteApplication(
        agent_card=public_agent_card,
        http_handler=request_handler,
    )

    uvicorn.run(server.build(), host='0.0.0.0', port=9999)

    return


if __name__ == '__main__':
    agent_name = Agents.tauric
    run_trading_agent_server(agent_name)