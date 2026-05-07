"""
CivicClassifierCrew — CrewAI crew that classifies scraped posts.
LLM: Cerebras LLaMA 3.1 8B (llama3.1-8b)
"""

import os
from pathlib import Path

from crewai import Agent, Crew, Process, Task, LLM
from crewai.project import CrewBase, agent, crew, task
from dotenv import load_dotenv

from crew.tools.classify_tool import CivicClassifyTool

load_dotenv()

_CONFIG_DIR = Path(__file__).parent / "config"


@CrewBase
class CivicClassifierCrew:
    """Single-agent crew for civic classification."""

    agents_config = str(_CONFIG_DIR / "classifier_agents.yaml")
    tasks_config = str(_CONFIG_DIR / "classifier_tasks.yaml")

    def _llm(self) -> LLM:
        return LLM(
            model="llama3.1-8b",
            api_key=os.environ["CEREBRAS_API_KEY"],
            base_url="https://api.cerebras.ai/v1",
            temperature=0.0,
        )

    @agent
    def civic_classifier(self) -> Agent:
        return Agent(
            config=self.agents_config["civic_classifier"],
            llm=self._llm(),
            tools=[CivicClassifyTool()],
            verbose=True,
        )

    @task
    def classify_posts_task(self) -> Task:
        return Task(config=self.tasks_config["classify_posts_task"])

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
