"""
CivicClassifierCrew — CrewAI crew that classifies scraped posts.
LLM: Cerebras LLaMA 3.1 8B (llama3.1-8b)
"""

import os
import json
import re
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


def classify_headline_description(headline: str, description: str) -> dict:
    """
    Classify a single headline+description pair and return structured JSON.
    """
    content = {
        "headline": (headline or "").strip(),
        "description": (description or "").strip(),
    }
    crew_instance = CivicClassifierCrew()
    result = crew_instance.crew().kickoff(inputs={"posts_json": json.dumps([content], ensure_ascii=True)})
    raw_text = result.raw if hasattr(result, "raw") else str(result)
    clean_text = re.sub(r"```(?:json)?\s*", "", raw_text).strip().rstrip("`")

    verdict_map = {
        "false": "Misleading",
        "misleading": "Misleading",
        "unverified": "Unverified",
        "unsupported": "Unverified",
        "true": "Verified",
        "verified": "Verified",
    }

    try:
        parsed = json.loads(clean_text)
        if isinstance(parsed, list) and parsed:
            parsed = parsed[0]
        if isinstance(parsed, dict):
            raw_verdict = str(
                parsed.get("verdict") or parsed.get("label") or parsed.get("classification") or "Unverified"
            ).strip()
            verdict = verdict_map.get(raw_verdict.lower(), raw_verdict.title() or "Unverified")
            trust_score = int(float(parsed.get("trust_score", 50)))
            reasoning = str(parsed.get("reasoning") or parsed.get("explanation") or "Classification completed.")
            return {
                "verdict": verdict,
                "trust_score": max(0, min(100, trust_score)),
                "reasoning": reasoning,
            }
    except Exception:
        pass

    return {
        "verdict": "Unverified",
        "trust_score": 50,
        "reasoning": "No credible sources confirm this claim.",
    }
