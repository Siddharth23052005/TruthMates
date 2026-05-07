"""
CounterInfoCrew — CrewAI crew that generates counter-info corrections.
LLM: Cerebras LLaMA 3.1 8B (llama3.1-8b)
"""

import os
from pathlib import Path

from crewai import Agent, Crew, Process, Task, LLM
from crewai.project import CrewBase, agent, crew, task
from dotenv import load_dotenv

load_dotenv()

_CONFIG_DIR = Path(__file__).parent / "config"


@CrewBase
class CounterInfoCrew:
    """Single-agent crew for counter-info generation."""

    agents_config = str(_CONFIG_DIR / "counter_agents.yaml")
    tasks_config = str(_CONFIG_DIR / "counter_tasks.yaml")

    def __init__(self, llm_provider: str = "cerebras") -> None:
        self._llm_provider = llm_provider

    def _llm(self) -> LLM:
        if self._llm_provider == "together":
            return LLM(
                model="meta-llama/Llama-3.3-70B-Instruct-Turbo",
                api_key=os.environ["TOGETHER_API_KEY"],
                base_url="https://api.together.xyz/v1",
                temperature=0.2,
            )
        return LLM(
            model="llama3.1-8b",
            api_key=os.environ["CEREBRAS_API_KEY"],
            base_url="https://api.cerebras.ai/v1",
            temperature=0.2,
        )

    @agent
    def counter_info_generator(self) -> Agent:
        return Agent(
            config=self.agents_config["counter_info_generator"],
            llm=self._llm(),
            verbose=True,
        )

    @task
    def generate_counter_info_task(self) -> Task:
        return Task(config=self.tasks_config["generate_counter_info_task"])

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
