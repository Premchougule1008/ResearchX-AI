from src.Pipelines.pipeline import run_research_pipeline


if __name__ == "__main__":
    topic = "The impact of AI on the job market in 2026"
    try:
        run_research_pipeline(topic)
    except Exception as exc:
        print(f"\nTerminal error: research pipeline failed for '{topic}'.")
        print(f"Details: {exc}")