# Copyright (c) Microsoft. All rights reserved.

"""This sample code demonstrates how to use an existing APO algorithm to tune the prompts."""
import logging
import os
from typing import Tuple, cast
from openai import AsyncOpenAI
from agentlightning import Trainer, configure_logger
from agentlightning.adapter import TraceToMessages
from agentlightning.algorithm.apo import APO
from agentlightning.types import Dataset
from dotenv import load_dotenv

from local_agents.fingenius.apo.fin_agent import FinAgentTask, prompt_template_baseline, load_fin_agent_tasks, \
    run_fin_agent

load_dotenv()


def load_train_val_dataset() -> Tuple[Dataset[FinAgentTask], Dataset[FinAgentTask]]:
    dataset_full = load_fin_agent_tasks()
    train_split = len(dataset_full) // 2
    dataset_train = [dataset_full[i] for i in range(train_split)]
    dataset_val = [dataset_full[i] for i in range(train_split, len(dataset_full))]
    return cast(Dataset[FinAgentTask], dataset_train), cast(Dataset[FinAgentTask], dataset_val)


def setup_apo_logger(file_path: str = "apo.log") -> None:
    """Dump a copy of all the logs produced by APO algorithm to a file."""

    file_handler = logging.FileHandler(file_path)
    file_handler.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] (Process-%(process)d %(name)s)   %(message)s")
    file_handler.setFormatter(formatter)
    logging.getLogger("agentlightning.algorithm.apo").addHandler(file_handler)


def fin_apo_main() -> None:
    configure_logger()
    setup_apo_logger()

    openai_client = AsyncOpenAI(api_key=os.environ.get('DEEPSEEK_API_KEY'), base_url=os.environ.get('DEEPSEEK_BASE_URL'))

    algo = APO[FinAgentTask](
        openai_client,
        val_batch_size=8,
        gradient_batch_size=4,
        beam_width=1,
        branch_factor=1,
        beam_rounds=1,
        _poml_trace=True,
        gradient_model="deepseek-chat",
        apply_edit_model="deepseek-chat",
    )
    trainer = Trainer(
        algorithm=algo,
        # Increase the number of runners to run more rollouts in parallel
        n_runners=1,
        # APO algorithm needs a baseline
        # Set it either here or in the algo
        initial_resources={
            # The resource key can be arbitrary
            "prompt_template": prompt_template_baseline()
        },
        # APO algorithm needs an adapter to process the traces produced by rollouts
        # Use this adapter to convert spans to messages
        adapter=TraceToMessages(),
    )
    dataset_train, dataset_val = load_train_val_dataset()
    trainer.fit(agent=run_fin_agent, train_dataset=dataset_train, val_dataset=dataset_val)


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.set_start_method('fork', force=True)
    fin_apo_main()
