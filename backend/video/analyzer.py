"""
Video Analysis Crew - CrewAI agents for claim extraction and fact-checking.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from crewai import Agent, Crew, Process, Task
from dotenv import load_dotenv
from pydantic import BaseModel

from core.constants import EVIDENCE_MATCH_THRESHOLD
from core.llm import build_crewai_llm, media_llm_provider_order
from crew.tools.evidence_tool import EvidenceRetrieveTool
from video.schemas import VerifiedClaim, VideoAnalysisOutput

load_dotenv()

_CONFIG_DIR = Path(__file__).parent / "config"


def _strip_markdown_json(text: str) -> str:
    text = re.sub(r"```(?:json)?\s*", "", text).strip()
    return text.rstrip("`").strip()


def _parse_and_validate_agent_output(
    raw_text: str,
    model_class: type[BaseModel],
    *,
    is_list: bool = False,
) -> BaseModel | list[BaseModel]:
    clean = _strip_markdown_json(raw_text)
    try:
        data = json.loads(clean)
    except json.JSONDecodeError:
        pattern = r"\[.*\]" if is_list else r"\{.*\}"
        match = re.search(pattern, clean, re.DOTALL)
        if not match:
            raise ValueError(f"Could not extract JSON from agent output: {clean[:200]}...")
        data = json.loads(match.group())

    if is_list:
        if not isinstance(data, list):
            raise ValueError(f"Expected JSON array, got {type(data).__name__}")
        return [model_class(**item) for item in data]
    return model_class(**data)


def _load_configs() -> tuple[dict, dict]:
    import yaml

    agents_path = _CONFIG_DIR / "agents.yaml"
    tasks_path = _CONFIG_DIR / "tasks.yaml"
    with open(agents_path, "r", encoding="utf-8") as handle:
        agents_config = yaml.safe_load(handle)
    with open(tasks_path, "r", encoding="utf-8") as handle:
        tasks_config = yaml.safe_load(handle)
    return agents_config, tasks_config


def _run_agent_with_validation(
    crew: Crew,
    *,
    model_class: type[BaseModel],
    is_list: bool,
    agent: Agent,
    original_description: str,
    max_retries: int = 1,
):
    for attempt in range(max_retries + 1):
        result = crew.kickoff()
        raw_text = result.raw if hasattr(result, "raw") else str(result)
        try:
            return _parse_and_validate_agent_output(raw_text, model_class, is_list=is_list)
        except Exception as exc:
            if attempt >= max_retries:
                raise RuntimeError(
                    f"Agent output failed validation after {max_retries + 1} attempts: {exc}"
                ) from exc
            schema_hint = json.dumps(model_class.model_json_schema(), indent=2)
            strict_task = Task(
                description=(
                    f"{original_description}\n\nPREVIOUS ATTEMPT FAILED VALIDATION: {exc}\n"
                    f"You MUST return valid JSON matching this exact schema:\n{schema_hint}\n"
                    "No markdown fences. No commentary. ONLY the JSON."
                ),
                expected_output=f"Valid JSON matching schema: {model_class.__name__}",
                agent=agent,
            )
            crew = Crew(agents=[agent], tasks=[strict_task], process=Process.sequential, verbose=True)
    raise RuntimeError("Agent validation failed.")


def _build_claim_payload(analysis_output: VideoAnalysisOutput) -> str:
    claims_for_tool = [
        {
            "title": claim.claim_text,
            "description": claim.misleading_aspect,
            "label": "civic",
            "link": "",
        }
        for claim in analysis_output.claims
    ]
    return json.dumps(claims_for_tool, ensure_ascii=True)


def _run_video_analysis_once(
    transcript: str,
    *,
    agents_config: dict,
    tasks_config: dict,
    provider: str,
) -> tuple[VideoAnalysisOutput, list[VerifiedClaim], str]:
    llm = build_crewai_llm(provider, temperature=0.0)

    analyst_agent = Agent(
        **agents_config["video_analyst"],
        llm=llm,
        tools=[],
    )
    analyst_task = Task(
        description=tasks_config["analyze_video_task"]["description"].format(
            transcript=transcript[:3000]
        ),
        expected_output=tasks_config["analyze_video_task"]["expected_output"],
        agent=analyst_agent,
    )
    analyst_crew = Crew(
        agents=[analyst_agent],
        tasks=[analyst_task],
        process=Process.sequential,
        verbose=True,
    )
    analysis_output = _run_agent_with_validation(
        analyst_crew,
        model_class=VideoAnalysisOutput,
        is_list=False,
        agent=analyst_agent,
        original_description=analyst_task.description,
    )

    posts_json = _build_claim_payload(analysis_output)
    checker_agent = Agent(
        **agents_config["fact_checker"],
        llm=llm,
        tools=[EvidenceRetrieveTool()],
    )
    checker_task = Task(
        description=tasks_config["fact_check_task"]["description"].format(
            posts_json=posts_json,
            evidence_match_threshold=EVIDENCE_MATCH_THRESHOLD,
        ),
        expected_output=tasks_config["fact_check_task"]["expected_output"],
        agent=checker_agent,
    )
    checker_crew = Crew(
        agents=[checker_agent],
        tasks=[checker_task],
        process=Process.sequential,
        verbose=True,
    )
    verified_claims = _run_agent_with_validation(
        checker_crew,
        model_class=VerifiedClaim,
        is_list=True,
        agent=checker_agent,
        original_description=checker_task.description,
    )
    return analysis_output, verified_claims, provider


def run_video_analysis_crew(transcript: str) -> tuple[VideoAnalysisOutput, list[VerifiedClaim], str]:
    agents_config, tasks_config = _load_configs()
    last_error: Exception | None = None
    for provider in media_llm_provider_order():
        try:
            return _run_video_analysis_once(
                transcript,
                agents_config=agents_config,
                tasks_config=tasks_config,
                provider=provider,
            )
        except Exception as exc:
            last_error = exc
            continue
    raise RuntimeError(f"Video analysis failed across providers: {last_error}") from last_error
