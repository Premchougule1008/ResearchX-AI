import re
import requests

from src.Agents.agents import (
    critic_chain,
    reader_agent,
    search_agent,
    writer_chain,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_score(feedback: str) -> int:
    """Extract the numeric score from the critic's output. Returns 0 if missing."""
    match = re.search(r"Score:\s*(\d+)\s*/\s*10", feedback, re.IGNORECASE)
    return int(match.group(1)) if match else 0


def _extract_url(text: str) -> str | None:
    """Return the first HTTP(S) URL found in a block of text."""
    match = re.search(r"https?://[^\s,)\"'>]+", text)
    return match.group(0).rstrip(".,)\"'>") if match else None


def _agent_output(result: dict) -> str:
    """Extract the text output from a LangGraph agent result dict."""
    messages = result.get("messages", [])
    if messages:
        return messages[-1].content
    return str(result)


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
                state["report"] = (
                    "Quick source digest (AI report unavailable)\n\n"
                    "The AI model timed out. This is a digest of retrieved source "
                    "material, not an AI-generated synthesis.\n\n"
                    f"Search findings:\n{state['search_results']}\n\n"
                    f"Extracted source text:\n{state['scraped_content']}"
                )
                state["fallback"] = True
                state["feedback"] = (
                    "AI review unavailable — the model request timed out. "
                    "Please verify the findings against the linked sources."
                )
                return state

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
        state["error"] = str(exc)
        print("\n  ❌ Terminal error — research pipeline failed.")
        print("  Check your API credentials and billing/quota settings.")
        print(f"  Details: {exc}")
        return state