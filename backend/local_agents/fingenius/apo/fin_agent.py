# Copyright (c) Microsoft. All rights reserved.

import asyncio
import json
import random
from typing import List, Optional, Tuple, TypedDict, cast
from openai import OpenAI
from pydantic import BaseModel, Field
from rich.console import Console
from agentlightning.adapter import TraceToMessages
from agentlightning.litagent import rollout
from agentlightning.reward import find_final_reward
from agentlightning.runner import LitAgentRunner
from agentlightning.store import InMemoryLightningStore
from agentlightning.tracer.agentops import AgentOpsTracer
from agentlightning.types import Dataset, PromptTemplate
from dotenv import load_dotenv
from local_agents.fingenius.main import fingenius_main
from local_agents.fingenius.src.prompt.mcp import NEXT_STEP_PROMPT_ZN, set_next_step_prompt

load_dotenv()

console = Console()


class JudgeResponse(BaseModel):
    reason: str = Field(description="The reason for the score. No more than 100 characters.")
    score: float = Field(description="The score for the match on a 0-1 scale. Be critical.")

class FinAgentRequirement(TypedDict):
    stock_code: str
    analysis_time: str
    total_tool_calls: int
    total_llm_calls: int
    research_summary: dict

class FinAgentTask(TypedDict):
    id: str
    task_input: FinAgentRequirement
    trade_return: float


def prompt_template_baseline() -> PromptTemplate:
    return PromptTemplate(
        template=NEXT_STEP_PROMPT_ZN,
        engine="f-string",
    )


def fin_agent_grader(final_decision: Optional[bool], trading_return: float) -> float:
    score = 1.0
    score = random.random()
    # if final_decision == True and trading_return > 0:
    #     score = 1.0
    return score


@rollout
def run_fin_agent(task: FinAgentTask, prompt_template: PromptTemplate) -> float:
    set_next_step_prompt(prompt_template.template)
    stock_code = task.get('task_input').get('stock_code')
    trading_return = task.get('trading_return')
    result = fingenius_main_mock(stock_code)
    reward = fin_agent_grader(result, trading_return)
    return reward

def fingenius_main_mock(stock_code):
    return True


def load_fin_agent_tasks() -> Dataset[FinAgentTask]:
    tasks: List[FinAgentTask] = []
    for line in open("../data_process/data/apo_output.jsonl"):
        task = json.loads(line)
        tasks.append(FinAgentTask(**task))
    return cast(Dataset[FinAgentTask], tasks)


async def debug_fin_agent(limit: int = 1):
    # Prepare all the components to run the agent
    runner = LitAgentRunner[FinAgentTask](AgentOpsTracer())
    store = InMemoryLightningStore()
    prompt_template = prompt_template_baseline()
    tasks = load_fin_agent_tasks()
    with runner.run_context(agent=run_fin_agent, store=store):
        for task in tasks:
            console.print("[bold green]=== Task ===[/bold green]", task, sep="\n")
            # Run the agent
            rollout = await runner.step(task, resources={"main_prompt": prompt_template})
            # Get the spans and convert them to messages
            # Useful for debugging and analysis
            spans = await store.query_spans(rollout.rollout_id)
            adapter = TraceToMessages()
            messages = adapter.adapt(spans)
            for message_idx, message in enumerate(messages):
                console.print(f"[bold purple]=== Postmortem Message #{message_idx} ===[/bold purple]")
                console.print(json.dumps(message))
            reward = find_final_reward(spans)
            console.print("[bold purple]=== Postmortem Reward ===[/bold purple]", reward, sep="\n")


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.set_start_method('fork', force=True)
    asyncio.run(debug_fin_agent())
