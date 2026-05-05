"""
OutputValidatorCrew — CrewAI crew that validates counter-info outputs.
LLM: Groq LLaMA 3.3 70B (groq/llama-3.3-70b-versatile)
"""

import os
from pathlib import Path

from crewai import Agent, Crew, Process, Task, LLM
from crewai.project import CrewBase, agent, crew, task
from dotenv import load_dotenv

from crew.tools.url_check_tool import UrlCheckTool

load_dotenv()

_CONFIG_DIR = Path(__file__).parent / "config"


@CrewBase
class OutputValidatorCrew:
    """Single-agent crew for counter-info output validation."""

    agents_config = str(_CONFIG_DIR / "validator_agents.yaml")
    tasks_config = str(_CONFIG_DIR / "validator_tasks.yaml")

    def _llm(self) -> LLM:
        return LLM(
            model="groq/llama-3.3-70b-versatile",
            api_key=os.environ["GROQ_API_KEY"],
            temperature=0.0,
        )

    @agent
    def output_validator(self) -> Agent:
        return Agent(
            config=self.agents_config["output_validator"],
            llm=self._llm(),
            tools=[UrlCheckTool()],
            verbose=True,
        )

    @task
    def validate_output_task(self) -> Task:
        return Task(config=self.tasks_config["validate_output_task"])

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
