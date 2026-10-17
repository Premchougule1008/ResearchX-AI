import re
import requests

from src.Agents.agents import (
    critic_chain,
    reader_agent,
    search_agent,
    writer_chain,
)
from src.Tools.tools import web_search


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_score(feedback: str) -> int:
    """Extract the numeric score from the critic's output. Returns 0 if missing."""
    match = re.search(r"Score:\s*(\d+)\s*/\s*10", feedback, re.IGNORECASE)
    return int(match.group(1)) if match else 0


def _extract_url(text: str) -> str | None:
    """Return the first HTTP(S) URL found in a block of text."""
    match = re.search(r"https?://[^\s\])}\"'>]+", text)
    return match.group(0).rstrip(".,)") if match else None


def _agent_output(result: dict) -> str:
    """Extract the text output from a LangGraph agent result dict."""
    messages = result.get("messages", [])
    if messages:
        return messages[-1].content
    return str(result)


def _parse_search_results(results: str) -> list[dict[str, str]]:
    """Extract source titles, URLs, and snippets from Tavily-style results."""
    pattern = re.compile(
        r"Title:\s*(.*?)\s+URL:\s*(.*?)\s+Snippet:\s*(.*?)"
        r"(?=\s*----\s*Title:|\s*\Z)",
        re.IGNORECASE | re.DOTALL,
    )
    parsed = []
    for title, url_text, snippet in pattern.findall(results):
        url = _extract_url(url_text)
        if url:
            parsed.append({
                "title": title.strip(),
                "url": url,
                "snippet": re.sub(r"\s+", " ", snippet).strip(),
            })
    return parsed


def _build_data_science_roadmap(sources: list[dict[str, str]]) -> str:
    """Organize only roadmap topics explicitly present in retrieved snippets."""
    phases = [
        (
            "Programming foundations",
            (
                "data structures", "lists", "dictionaries", "sets", "functions",
                "logical thinking", "program flow", "search and sorting algorithms",
                "object-oriented programming", "external libraries",
            ),
        ),
        (
            "Statistics",
            ("mean", "median", "distribution", "correlation"),
        ),
        (
            "Data analytics",
            ("collecting", "cleaning", "analyzing", "visualizing"),
        ),
        (
            "Machine learning",
            ("advanced machine learning", "machine learning"),
        ),
        (
            "Deployment and cloud",
            ("cloud integration", "real-world deployment", "deployment"),
        ),
    ]
    roadmap_steps = []

    for title, concepts in phases:
        matched = []
        citations = []
        for source_index, source in enumerate(sources, start=1):
            snippet = source["snippet"].lower()
            for concept in concepts:
                if re.search(rf"\b{re.escape(concept)}\b", snippet):
                    label = concept.capitalize()
                    if not any(concept in existing.lower() for existing in matched):
                        matched.append(label)
                    if source_index not in citations:
                        citations.append(source_index)
        if matched:
            references = ", ".join(f"[{index}]" for index in citations)
            roadmap_steps.append(
                f"{len(roadmap_steps) + 1}. **{title}** — "
                f"Focus on {', '.join(matched)}. {references}"
            )

    if not roadmap_steps:
        return ""
    return "## Learning roadmap\n" + "\n\n".join(roadmap_steps)


def _source_digest(topic: str, state: dict, reason: str) -> dict:
    """Return a readable, source-grounded brief when the AI model is unavailable."""
    if not state.get("search_results"):
        state["search_results"] = web_search.invoke({"query": topic})
    if not state["search_results"].strip():
        raise RuntimeError("Web search returned no results for the requested topic.")

    sources = _parse_search_results(state["search_results"])
    if not sources:
        state["search_results"] = web_search.invoke({"query": topic})
        sources = _parse_search_results(state["search_results"])
    if not sources:
        raise RuntimeError("Search results did not contain any usable source snippets.")

    source_list = "\n".join(
        f"- [{source['title']}]({source['url']})"
        for source in sources
    )
    if re.search(r"\broadmap\b", topic, re.IGNORECASE) and re.search(
        r"data\s*science", topic, re.IGNORECASE
    ):
        content = _build_data_science_roadmap(sources)
        if not content:
            content = "## Search findings\n" + "\n\n".join(
                f"{index}. **{source['title']}** — "
                f"{source['snippet'] or 'No search snippet was provided.'}"
                for index, source in enumerate(sources, start=1)
            )
        state["report"] = (
            f"# Data science roadmap\n\n"
            f"## Overview\n"
            f"A step-by-step learning sequence based on {len(sources)} "
            f"search sources for “{topic}”.\n\n"
            f"{content}\n\n"
            f"## Sources\n{source_list}"
        )
    else:
        findings = "\n\n".join(
            f"{index}. **{source['title']}**\n"
            f"   {source['snippet'] or 'No search snippet was provided.'}"
            for index, source in enumerate(sources, start=1)
        )
        state["report"] = (
            f"# Research brief: {topic}\n\n"
            f"## Overview\n"
            f"The search returned {len(sources)} sources related to this topic.\n\n"
            f"## Findings\n{findings}\n\n"
            f"## Sources\n{source_list}"
        )
    state["scraped_content"] = (
        "Full-page extraction was skipped because the AI service quota is "
        "unavailable. Use the source links in the report to read the articles."
    )
    state["feedback"] = (
        f"AI review unavailable — {reason} "
        "This brief contains search snippets only; verify findings against "
        "the linked sources."
    )
    state["fallback"] = True
    return state


def _is_quota_error(error: Exception) -> bool:
    message = str(error).lower()
    return (
        "resource_exhausted" in message
        or "quota exceeded" in message
        or ("429" in message and "quota" in message)
    )


# ── Orchestrator ──────────────────────────────────────────────────────────────

def run_research_pipeline(topic: str) -> dict:
    """
    Full multi-agent research pipeline:

        Search Agent  ──►  Reader Agent  ──►  Writer Chain
                                                   │
                                            Critic Chain
                                                   │
                                  score < 7 ◄──────┘ (max 3 revisions)
                                       │
                                  Writer Chain  ──►  Final Report
    """
    state: dict = {}

    try:
        # ── Step 1 : Search Agent ─────────────────────────────────────────────
        print("\n" + "=" * 60)
        print("  STEP 1 — Search Agent: searching the web …")
        print("=" * 60)

        search_result = search_agent.invoke({
            "messages": [(
                "human",
                f"Search for comprehensive and recent information about: {topic}. "
                "Return all titles, URLs, and key snippets."
            )]
        })
        state["search_results"] = _agent_output(search_result)
        print("\n[Search results]\n", state["search_results"])

        # ── Step 2 : Reader Agent ─────────────────────────────────────────────
        print("\n" + "=" * 60)
        print("  STEP 2 — Reader Agent: extracting in-depth content …")
        print("=" * 60)

        url = _extract_url(state["search_results"])
        if url:
            reader_result = reader_agent.invoke({
                "messages": [(
                    "human",
                    f"Extract and summarise the key information from this URL: {url}"
                )]
            })
            state["scraped_content"] = _agent_output(reader_result)
        else:
            state["scraped_content"] = "No source URL was found in the search results."

        print("\n[Extracted content]\n", state["scraped_content"])

        # ── Steps 3 + 4 : Writer → Critic feedback loop ───────────────────────
        research_combined = (
            f"SEARCH RESULTS:\n{state['search_results']}\n\n"
            f"DETAILED CONTENT:\n{state['scraped_content']}"
        )

        MAX_ITERATIONS = 3
        iteration = 0
        critic_feedback_note = ""
        state["fallback"] = False

        while iteration < MAX_ITERATIONS:
            iteration += 1

            # ── Step 3 : Writer Chain ─────────────────────────────────────────
            print("\n" + "=" * 60)
            print(f"  STEP 3 — Writer Agent: drafting report (attempt {iteration}/{MAX_ITERATIONS}) …")
            print("=" * 60)

            try:
                state["report"] = writer_chain.invoke({
                    "topic": topic,
                    "research": research_combined,
                    "feedback": (
                        f"Critic feedback from previous draft — improve on these points:\n{critic_feedback_note}"
                        if critic_feedback_note
                        else ""
                    ),
                })
            except requests.exceptions.Timeout:
                return _source_digest(topic, state, "The AI model timed out.")

            print("\n[Draft report]\n", state["report"])

            # ── Step 4 : Critic Chain ─────────────────────────────────────────
            print("\n" + "=" * 60)
            print(f"  STEP 4 — Critic Agent: reviewing report (attempt {iteration}/{MAX_ITERATIONS}) …")
            print("=" * 60)

            state["feedback"] = critic_chain.invoke({"report": state["report"]})
            print("\n[Critic feedback]\n", state["feedback"])

            score = _parse_score(state["feedback"])
            print(f"\n  Critic score: {score}/10")

            if score >= 7:
                print(f"  ✅ Report approved with score {score}/10 — pipeline complete!")
                break
            elif iteration < MAX_ITERATIONS:
                print(f"  🔁 Score {score}/10 is below threshold — sending back for revision …")
                critic_feedback_note = state["feedback"]
            else:
                print(f"  ⚠️  Max iterations reached. Returning best available report.")

        return state

    except Exception as exc:
        if _is_quota_error(exc):
            print("\n  ⚠ Gemini quota exhausted — returning a source-based digest.")
            try:
                return _source_digest(
                    topic,
                    state,
                    "The Gemini API quota is exhausted.",
                )
            except Exception as fallback_exc:
                state["error"] = (
                    "Gemini quota is exhausted and source fallback failed: "
                    f"{fallback_exc}"
                )
                print(f"  ❌ Source fallback failed: {fallback_exc}")
                return state

        state["error"] = str(exc)
        print("\n  ❌ Terminal error — research pipeline failed.")
        print("  Check your API credentials and billing/quota settings.")
        print(f"  Details: {exc}")
        return state