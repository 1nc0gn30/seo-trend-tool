from io import StringIO

import pandas as pd
import streamlit as st

from ai_clients import provider_runtime_note, run_ai_analysis
from seotrendtool_core import (
    build_markdown_brief,
    fetch_rising_keywords,
    generate_title_ideas,
    rank_opportunities,
    summarize_by_seed,
)


st.set_page_config(page_title="SEO Trend Tool", page_icon="📈", layout="wide")
st.title("SEO Trend Tool")
st.caption("Breakout keyword discovery + lightweight prioritization for fast SEO execution.")


def _read_uploaded_keywords(uploaded_file) -> list[str]:
    if uploaded_file is None:
        return []

    name = uploaded_file.name.lower()
    if name.endswith(".csv"):
        df = pd.read_csv(uploaded_file, header=None)
        raw = df.iloc[:, 0].dropna().astype(str).tolist()
    else:
        text = uploaded_file.getvalue().decode("utf-8", errors="ignore")
        raw = StringIO(text).read().splitlines()

    cleaned = [k.strip() for k in raw if str(k).strip()]
    return list(dict.fromkeys(cleaned))


@st.cache_data(ttl=6 * 60 * 60)
def cached_collect(
    keywords: tuple[str, ...],
    timeframe: str,
    geo: str,
    growth_threshold: int,
    max_keywords: int,
    min_sleep: float,
    max_sleep: float,
    retries: int,
) -> pd.DataFrame:
    return fetch_rising_keywords(
        keywords=list(keywords),
        timeframe=timeframe,
        geo=geo,
        growth_threshold=growth_threshold,
        max_keywords=max_keywords,
        min_sleep=min_sleep,
        max_sleep=max_sleep,
        retries=retries,
    )


with st.sidebar:
    st.header("Run Settings")
    cloud_mode = st.toggle("Cloud mode (recommended)", value=True)
    use_cache = st.toggle("Cache identical runs", value=True)

    keywords_input = st.text_area(
        "Seed keywords (one per line)",
        "content marketing\nseo optimization\nchatgpt prompts",
        height=160,
    )
    uploaded_keywords = st.file_uploader("Or upload TXT/CSV keyword file", type=["txt", "csv"])

    timeframe = st.selectbox("Timeframe", ["now 7-d", "today 1-m", "today 3-m", "today 12-m"], index=3)
    geo = st.text_input("Geo (country code, blank = global)", "US")
    growth_threshold = st.slider("Min growth %", min_value=0, max_value=2000, value=350, step=50)
    max_keywords = st.slider("Max seed keywords per run", min_value=3, max_value=60, value=15, step=1)

    if cloud_mode:
        min_sleep = st.slider("Min delay (sec)", min_value=0.0, max_value=5.0, value=1.5, step=0.5)
        max_sleep = st.slider("Max delay (sec)", min_value=0.0, max_value=8.0, value=3.0, step=0.5)
        retries = st.slider("Retries per keyword", min_value=0, max_value=3, value=1, step=1)
    else:
        min_sleep = st.slider("Min delay (sec)", min_value=0.0, max_value=15.0, value=4.0, step=0.5)
        max_sleep = st.slider("Max delay (sec)", min_value=0.0, max_value=20.0, value=8.0, step=0.5)
        retries = st.slider("Retries per keyword", min_value=0, max_value=5, value=2, step=1)

    enable_ai = st.toggle("Enable AI analysis", value=False)
    ai_provider = st.selectbox(
        "AI provider",
        ["none", "ollama", "openai", "anthropic", "gemini"],
        index=0,
        disabled=not enable_ai,
    )
    default_models = {
        "none": "",
        "ollama": "llama3",
        "openai": "gpt-4o-mini",
        "anthropic": "claude-3-5-haiku-latest",
        "gemini": "gemini-1.5-flash",
    }
    ai_model = st.text_input(
        "AI model",
        value=default_models.get(ai_provider, ""),
        disabled=not enable_ai or ai_provider == "none",
    )
    needs_key = ai_provider in {"openai", "anthropic", "gemini"}
    ai_api_key = st.text_input(
        "API key",
        type="password",
        help="Needed for cloud AI providers. Leave blank for Ollama/local mode.",
        disabled=not enable_ai or not needs_key,
    )
    if enable_ai:
        st.caption(provider_runtime_note(ai_provider))
    run_button = st.button("Run analysis", use_container_width=True)


if run_button:
    uploaded_list = _read_uploaded_keywords(uploaded_keywords)
    text_list = [k.strip() for k in keywords_input.splitlines() if k.strip()]
    keywords = list(dict.fromkeys(uploaded_list + text_list))

    if not keywords:
        st.warning("Add at least one keyword or upload a keyword file.")
        st.stop()

    if min_sleep > max_sleep:
        st.error("Min delay cannot be greater than max delay.")
        st.stop()

    status = st.empty()
    status.info("Collecting rising queries from Google Trends...")

    try:
        if use_cache:
            raw = cached_collect(
                tuple(keywords),
                timeframe,
                geo,
                growth_threshold,
                max_keywords,
                min_sleep,
                max_sleep,
                retries,
            )
        else:
            raw = fetch_rising_keywords(
                keywords=keywords,
                timeframe=timeframe,
                geo=geo,
                growth_threshold=growth_threshold,
                max_keywords=max_keywords,
                min_sleep=min_sleep,
                max_sleep=max_sleep,
                retries=retries,
            )
    except Exception as exc:
        st.error(f"Collection failed: {exc}")
        st.stop()

    status.empty()

    if raw.empty:
        st.info("No opportunities met the threshold. Try lowering min growth or broadening timeframe/geo.")
        st.stop()

    ranked = rank_opportunities(raw)
    summary = summarize_by_seed(ranked)
    titles = generate_title_ideas(ranked, top_n=30)
    brief = build_markdown_brief(ranked, top_n=20)

    c1, c2, c3 = st.columns(3)
    c1.metric("Opportunities", value=len(ranked))
    c2.metric("Unique seeds", value=ranked["Seed_Keyword"].nunique())
    c3.metric("Median growth %", value=int(ranked["Growth_Value"].median()))

    tab1, tab2, tab3, tab4 = st.tabs(["Ranked Opportunities", "Seed Insights", "Content Plan", "Data Exports"])

    with tab1:
        view_cols = ["Seed_Keyword", "Recommended_Long_Tail", "Growth_Value", "Growth_%", "Priority_Score"]
        view = ranked[view_cols].copy()
        st.dataframe(view, use_container_width=True, hide_index=True)

    with tab2:
        st.subheader("Seed Performance")
        st.dataframe(summary, use_container_width=True, hide_index=True)
        if not summary.empty:
            chart_df = summary.set_index("Seed_Keyword")[["Opportunities", "Max_Growth"]]
            st.bar_chart(chart_df)

    with tab3:
        st.subheader("Title Ideas")
        st.dataframe(titles, use_container_width=True, hide_index=True)
        st.subheader("Markdown Brief")
        st.code(brief, language="markdown")

        if enable_ai and ai_provider != "none":
            st.subheader("Optional AI Add-on")
            try:
                prompt = f"""
                Analyze these top ranked opportunities and propose a 14-day execution sprint:
                {ranked.head(30).to_string(index=False)}
                """
                with st.spinner(f"Querying {ai_provider} model '{ai_model}'..."):
                    text = run_ai_analysis(
                        provider=ai_provider,
                        model=ai_model,
                        prompt=prompt,
                        api_key=ai_api_key,
                    )
                st.markdown(text)
            except Exception as exc:
                st.warning(f"AI analysis unavailable. Reason: {exc}")

    with tab4:
        st.subheader("Download Outputs")
        st.download_button(
            "Download ranked opportunities CSV",
            data=ranked.to_csv(index=False).encode("utf-8"),
            file_name="seo_opportunities_ranked.csv",
            mime="text/csv",
        )
        st.download_button(
            "Download seed summary CSV",
            data=summary.to_csv(index=False).encode("utf-8"),
            file_name="seed_summary.csv",
            mime="text/csv",
        )
        st.download_button(
            "Download title ideas CSV",
            data=titles.to_csv(index=False).encode("utf-8"),
            file_name="title_ideas.csv",
            mime="text/csv",
        )
        st.download_button(
            "Download markdown brief",
            data=brief.encode("utf-8"),
            file_name="seo_brief.md",
            mime="text/markdown",
        )
