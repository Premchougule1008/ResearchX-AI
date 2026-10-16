import re

import requests

from src.Agents.agents import writer_chain
from src.Tools.tools import scrape_url, web_search


def run_research_pipeline(topic: str) -> dict:
    state = {}

    try:
        print("\n" + " =" * 50)
        print("step 1 - searching the web ...")
        print("=" * 50)

        state["search_results"] = web_search.invoke({"query": topic})

        print("\n search result ", state["search_results"])

        print("\n" + " =" * 50)
        print("step 2 - reading a relevant source ...")
        print("=" * 50)

        url_match = re.search(r"URL:\s*(https?://\S+)", state["search_results"])
        state["scraped_content"] = (
            scrape_url.invoke({"url": url_match.group(1)})
            if url_match
            else "No source URL was returned by web search."
        )

        print("\nscraped content: \n", state['scraped_content'])

        print("\n" + " =" * 50)
        print("step 3 - writing a concise report ...")
        print("=" * 50)

        research_combined = (
            f"SEARCH RESULTS : \n {state['search_results']} \n\n"
            f"DETAILED SCRAPED CONTENT : \n {state['scraped_content']}"
        )

        try:
            state["report"] = writer_chain.invoke({
                "topic": topic,
                "research": research_combined
            })
            state["fallback"] = False
            state["feedback"] = "Review skipped to return your research faster."
        except requests.exceptions.Timeout:
            state["report"] = (
                "Quick source digest (AI report unavailable)\n\n"
                "The AI model timed out, so this is a digest of retrieved source material, "
                "not an AI-generated synthesis. Check the source excerpts below before relying "
                "on any conclusion.\n\n"
                f"Search findings:\n{state['search_results']}\n\n"
                f"Extracted source text:\n{state['scraped_content']}"
            )
            state["fallback"] = True
            state["feedback"] = (
                "AI review unavailable because the model request timed out. "
                "Please verify the findings against the linked sources."
            )

        print("\n Final Report\n", state['report'])
        return state

    except Exception as exc:
        state["error"] = str(exc)
        print("\nTerminal error: the research pipeline failed.")
        print("Check your API credentials and billing/quota settings.")
        print(f"Details: {exc}")
        return state