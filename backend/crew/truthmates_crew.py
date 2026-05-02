"""
TruthMatesCrew — CrewAI crew that scrapes PIB and MyGov RSS feeds,
cleans the results, and returns a structured JSON list of civic posts.

LLM: Groq LLaMA 3.1 8B (groq/llama-3.1-8b-instant) for testing
Process: Sequential (fetch -> clean)
"""

import os
from pathlib import Path

from crewai import Agent, Crew, Process, Task, LLM
from crewai.project import CrewBase, agent, crew, task
from dotenv import load_dotenv

from crew.tools.rss_tool import RSSFetchTool
from crew.tools.clean_tool import CleanDedupTool

load_dotenv()

# -- Config paths -------------------------------------------------------------
_CONFIG_DIR = Path(__file__).parent / "config"


@CrewBase
class TruthMatesCrew:
    """
    Two-agent crew for civic RSS scraping:
      1. rss_scraper  -> fetches PIB + MyGov feeds
      2. data_cleaner -> cleans HTML, normalizes dates, deduplicates
    """

    agents_config = str(_CONFIG_DIR / "agents.yaml")
    tasks_config = str(_CONFIG_DIR / "tasks.yaml")

    # -- Shared LLM ------------------------------------------------------------

    def _llm(self) -> LLM:
        """Return a Groq LLaMA 3.3 70B LLM instance."""
        return LLM(
            model="groq/llama-3.1-8b-instant",
            api_key=os.environ["GROQ_API_KEY"],
            temperature=0.0,  # Deterministic for data tasks
        )

    # -- Agents ---------------------------------------------------------------

    @agent
    def rss_scraper(self) -> Agent:
        """Agent responsible for fetching RSS feeds."""
        return Agent(
            config=self.agents_config["rss_scraper"],
            llm=self._llm(),
            tools=[RSSFetchTool()],
            verbose=True,
        )

    @agent
    def data_cleaner(self) -> Agent:
        """Agent responsible for cleaning and deduplicating scraped data."""
        return Agent(
            config=self.agents_config["data_cleaner"],
            llm=self._llm(),
            tools=[CleanDedupTool()],
            verbose=True,
        )

    # -- Tasks ----------------------------------------------------------------

    @task
    def fetch_rss_task(self) -> Task:
        """Task: fetch both RSS feeds and return raw item list."""
        return Task(config=self.tasks_config["fetch_rss_task"])

    @task
    def clean_deduplicate_task(self) -> Task:
        """Task: clean HTML, normalize dates, deduplicate by link."""
        return Task(config=self.tasks_config["clean_deduplicate_task"])

    # -- Crew -----------------------------------------------------------------

    @crew
    def crew(self) -> Crew:
        """Assemble the sequential TruthMates crew."""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
