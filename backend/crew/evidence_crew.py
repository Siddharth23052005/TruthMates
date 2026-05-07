"""
EvidenceRetrieverCrew — CrewAI crew that retrieves evidence for claims.
LLM: Cerebras LLaMA 3.1 8B (llama3.1-8b)
"""

import os
from pathlib import Path

from crewai import Agent, Crew, Process, Task, LLM
from crewai.project import CrewBase, agent, crew, task
from dotenv import load_dotenv

from crew.tools.evidence_tool import EvidenceRetrieveTool

load_dotenv()

_CONFIG_DIR = Path(__file__).parent / "config"


@CrewBase
class EvidenceRetrieverCrew:
    """Single-agent crew for evidence retrieval."""

    agents_config = str(_CONFIG_DIR / "evidence_agents.yaml")
    tasks_config = str(_CONFIG_DIR / "evidence_tasks.yaml")

    def __init__(self, llm_provider: str = "cerebras") -> None:
        self._llm_provider = llm_provider

    def _llm(self) -> LLM:
        if self._llm_provider == "together":
            return LLM(
                model="meta-llama/Llama-3.3-70B-Instruct-Turbo",
                api_key=os.environ["TOGETHER_API_KEY"],
                base_url="https://api.together.xyz/v1",
                temperature=0.0,
            )
        return LLM(
            model="llama3.1-8b",
            api_key=os.environ["CEREBRAS_API_KEY"],
            base_url="https://api.cerebras.ai/v1",
            temperature=0.0,
        )

    @agent
    def evidence_retriever(self) -> Agent:
        return Agent(
            config=self.agents_config["evidence_retriever"],
            llm=self._llm(),
            tools=[EvidenceRetrieveTool()],
            verbose=True,
        )

    @task
    def retrieve_evidence_task(self) -> Task:
        return Task(config=self.tasks_config["retrieve_evidence_task"])

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
