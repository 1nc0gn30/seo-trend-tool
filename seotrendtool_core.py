import random
import time
from pathlib import Path
from typing import Callable

import pandas as pd
from pytrends.request import TrendReq


def load_keywords(input_path: str) -> list[str]:
    """Load keywords from TXT or CSV, remove blanks, keep order, dedupe."""
    path = Path(input_path)
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    if path.suffix.lower() == ".csv":
        df = pd.read_csv(path, header=None)
        raw = df.iloc[:, 0].dropna().astype(str).tolist()
    else:
        raw = path.read_text(encoding="utf-8").splitlines()

    cleaned = [k.strip() for k in raw if str(k).strip()]
    return list(dict.fromkeys(cleaned))


def _normalize_growth_col(df: pd.DataFrame) -> pd.DataFrame:
    tmp = df.copy()
    tmp["Growth_Value"] = pd.to_numeric(tmp["value"], errors="coerce")
    tmp = tmp.dropna(subset=["Growth_Value"])
    tmp["Growth_Value"] = tmp["Growth_Value"].astype(int)
    tmp["Growth_%"] = tmp["Growth_Value"].astype(str) + "%"
    return tmp


def fetch_rising_keywords(
    keywords: list[str],
    timeframe: str = "today 12-m",
    geo: str = "US",
    growth_threshold: int = 400,
    max_keywords: int | None = None,
    min_sleep: float = 4.0,
    max_sleep: float = 8.0,
    retries: int = 2,
    on_progress: Callable[[int, int, str], None] | None = None,
    on_sleep: Callable[[float], None] | None = None,
) -> pd.DataFrame:
    """
    Query Google Trends rising keywords for each seed term.
    Returns a normalized dataframe with one row per recommendation.
    """
    if max_keywords is not None and max_keywords > 0:
        keywords = keywords[:max_keywords]

    pytrend = TrendReq(hl="en-US", tz=360)
    results: list[pd.DataFrame] = []
    total = len(keywords)

    for i, kw in enumerate(keywords):
        if on_progress:
            on_progress(i + 1, total, kw)

        last_error = None
        for attempt in range(retries + 1):
            try:
                pytrend.build_payload([kw], cat=0, timeframe=timeframe, geo=geo, gprop="")
                related_queries = pytrend.related_queries()
                keyword_data = related_queries.get(kw) if related_queries else None

                if keyword_data and keyword_data.get("rising") is not None:
                    rising_df = _normalize_growth_col(keyword_data["rising"])
                    hot = rising_df[rising_df["Growth_Value"] >= growth_threshold].copy()

                    if not hot.empty:
                        hot["Seed_Keyword"] = kw
                        final_df = hot[["Seed_Keyword", "query", "Growth_Value", "Growth_%"]].copy()
                        final_df.rename(columns={"query": "Recommended_Long_Tail"}, inplace=True)
                        results.append(final_df)
                break
            except Exception as exc:
                last_error = exc
                if attempt < retries:
                    backoff = min_sleep + random.uniform(0.5, 1.5) * (attempt + 1)
                    time.sleep(backoff)
                else:
                    raise RuntimeError(f"Failed keyword '{kw}': {last_error}") from last_error

        if i < total - 1:
            sleep_for = random.uniform(min_sleep, max_sleep)
            if on_sleep:
                on_sleep(sleep_for)
            time.sleep(sleep_for)

    if not results:
        return pd.DataFrame(
            columns=["Seed_Keyword", "Recommended_Long_Tail", "Growth_Value", "Growth_%"]
        )

    master = pd.concat(results, ignore_index=True)
    master = (
        master.sort_values(["Growth_Value", "Seed_Keyword"], ascending=[False, True])
        .drop_duplicates(subset=["Seed_Keyword", "Recommended_Long_Tail"], keep="first")
        .reset_index(drop=True)
    )
    return master


def export_csv(dataframe: pd.DataFrame, output_path: str) -> None:
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    dataframe.to_csv(output_path, index=False)


def rank_opportunities(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Add lightweight ranking fields and sort by priority score."""
    if dataframe.empty:
        return dataframe.copy()

    df = dataframe.copy()
    growth = pd.to_numeric(df.get("Growth_Value"), errors="coerce")
    if growth.isna().all():
        growth = pd.to_numeric(
            df.get("Growth_%", "").astype(str).str.replace("%", "", regex=False),
            errors="coerce",
        )
    growth = growth.fillna(0).astype(int)

    phrases = df.get("Recommended_Long_Tail", "").astype(str)
    word_count = phrases.str.split().str.len().fillna(0).astype(int)
    char_count = phrases.str.len().fillna(0).astype(int)

    df["Growth_Value"] = growth
    df["Long_Tail_Words"] = word_count
    df["Long_Tail_Chars"] = char_count
    # Small, transparent heuristic tuned for quick-win prioritization.
    df["Priority_Score"] = (df["Growth_Value"] * 1.0) + (df["Long_Tail_Words"] * 12)
    return df.sort_values("Priority_Score", ascending=False).reset_index(drop=True)


def summarize_by_seed(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Aggregate top-line stats for each seed keyword."""
    if dataframe.empty or "Seed_Keyword" not in dataframe.columns:
        return pd.DataFrame(columns=["Seed_Keyword", "Opportunities", "Avg_Growth", "Max_Growth"])

    ranked = rank_opportunities(dataframe)
    out = (
        ranked.groupby("Seed_Keyword", as_index=False)
        .agg(
            Opportunities=("Recommended_Long_Tail", "count"),
            Avg_Growth=("Growth_Value", "mean"),
            Max_Growth=("Growth_Value", "max"),
        )
        .sort_values(["Opportunities", "Max_Growth"], ascending=[False, False])
        .reset_index(drop=True)
    )
    out["Avg_Growth"] = out["Avg_Growth"].round(1)
    return out


def generate_title_ideas(dataframe: pd.DataFrame, top_n: int = 20) -> pd.DataFrame:
    """Generate simple, non-AI content titles from top-ranked opportunities."""
    if dataframe.empty:
        return pd.DataFrame(columns=["Seed_Keyword", "Recommended_Long_Tail", "Title_Idea"])

    ranked = rank_opportunities(dataframe).head(max(1, top_n)).copy()
    keyword = ranked["Recommended_Long_Tail"].astype(str)
    ranked["Title_Idea"] = (
        "How to win with "
        + keyword.str.title()
        + " in 2026 (step-by-step)"
    )
    return ranked[["Seed_Keyword", "Recommended_Long_Tail", "Title_Idea"]]


def build_markdown_brief(dataframe: pd.DataFrame, top_n: int = 15) -> str:
    """Build a lightweight markdown brief for execution planning."""
    ranked = rank_opportunities(dataframe).head(max(1, top_n))
    if ranked.empty:
        return "# SEO Opportunity Brief\n\nNo opportunities found.\n"

    lines = ["# SEO Opportunity Brief", ""]
    for _, row in ranked.iterrows():
        seed = row.get("Seed_Keyword", "")
        phrase = row.get("Recommended_Long_Tail", "")
        growth = row.get("Growth_Value", 0)
        score = row.get("Priority_Score", 0)
        lines.append(f"## {phrase}")
        lines.append(f"- Seed keyword: {seed}")
        lines.append(f"- Growth: {growth}%")
        lines.append(f"- Priority score: {score:.1f}")
        lines.append(f"- Suggested angle: Actionable guide targeting '{phrase}' intent.")
        lines.append("")
    return "\n".join(lines)


def expand_keywords(seeds: list[str], modifiers: list[str], max_per_seed: int = 20) -> list[str]:
    """Create lightweight long-tail variants from seed keywords."""
    variants: list[str] = []
    for seed in seeds:
        base = seed.strip()
        if not base:
            continue
        local = [
            base,
            f"{base} strategy",
            f"{base} checklist",
            f"{base} tips",
            f"best {base}",
            f"{base} for beginners",
        ]
        for mod in modifiers:
            mod_clean = mod.strip()
            if mod_clean:
                local.append(f"{base} {mod_clean}")
        variants.extend(local[: max(1, max_per_seed)])
    return list(dict.fromkeys(v.strip() for v in variants if v.strip()))
