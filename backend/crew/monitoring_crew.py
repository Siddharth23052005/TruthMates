"""
MonitoringCrew — CrewAI supervisor that reviews agent outputs.
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
class MonitoringCrew:
    """Supervisor crew that monitors other agents."""

    agents_config = str(_CONFIG_DIR / "monitor_agents.yaml")
    tasks_config = str(_CONFIG_DIR / "monitor_tasks.yaml")

    def _llm(self) -> LLM:
        return LLM(
            model="llama3.1-8b",
            api_key=os.environ["CEREBRAS_API_KEY"],
            base_url="https://api.cerebras.ai/v1",
            temperature=0.0,
        )

    @agent
    def supervisor(self) -> Agent:
        return Agent(
            config=self.agents_config["supervisor"],
            llm=self._llm(),
            verbose=True,
        )

    @task
    def monitor_task(self) -> Task:
        return Task(config=self.tasks_config["monitor_task"])

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
