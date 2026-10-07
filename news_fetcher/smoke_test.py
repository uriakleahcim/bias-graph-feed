"""Run the bounded Bias Graph Feed ingestion profile as a one-shot service."""

from news_fetcher.scheduler import run_all_fetches


if __name__ == "__main__":
    run_all_fetches(run_full_pipeline=True, ingestion_profile="smoke")
