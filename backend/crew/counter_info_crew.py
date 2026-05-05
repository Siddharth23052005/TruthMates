"""
CounterInfoCrew — CrewAI crew that generates counter-info corrections.
LLM: Groq LLaMA 3.3 70B (groq/llama-3.3-70b-versatile)
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

    def _llm(self) -> LLM:
        return LLM(
            model="groq/llama-3.3-70b-versatile",
            api_key=os.environ["GROQ_API_KEY"],
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
