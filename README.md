# SEO Trend Tool

Lightweight keyword opportunity mining from Google Trends, optimized to run on Streamlit Cloud free tier.

## Highlights

- Pulls rising related queries from Google Trends
- Filters breakout opportunities by growth threshold
- Adds lightweight priority scoring
- Generates seed-level summary metrics
- Generates non-AI title ideas + markdown brief
- Includes multiple small utility scripts for fast pipelines
- Optional Ollama add-on (local only; not required)
- Optional provider-based AI: `none`, `ollama`, `openai`, `anthropic`, `gemini`

## Project Files

- `app.py`: Streamlit app (cloud-friendly)
- `app2.py`: CLI collector and exporter
- `seotrendtool_core.py`: shared core logic
- `kw_cleaner.py`: normalize/dedupe keyword lists
- `keyword_expander.py`: create long-tail seed expansions
- `opportunity_ranker.py`: score/rank opportunities CSV
- `seed_report.py`: aggregate summary by seed keyword
- `brief_builder.py`: generate markdown execution brief
- `batch_collector.py`: chunked collector for larger seed sets
- `keywords.txt`: sample seeds
- `requirements.txt`: minimal dependencies for cloud
- `requirements-ai.txt`: optional local Ollama dependency

## Quick Start

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Optional local Ollama dependency:

```bash
pip install -r requirements-ai.txt
```

## Run Streamlit App

```bash
streamlit run app.py
```

## Streamlit Cloud (Free Tier) Guidance

Use these defaults in the sidebar for reliable runs:

- `Cloud mode`: ON
- `Cache identical runs`: ON
- `Max seed keywords`: 8-20
- `Retries`: 0-1
- `Min/Max delay`: around `1.5s` / `3.0s`
- Prefer narrower seed lists per run, then iterate

Notes:
- Ollama is optional and usually unavailable on Streamlit Cloud. The app handles this gracefully.
- For larger campaigns, run batches and merge outputs.
- For cloud AI providers, use API key in the app sidebar or CLI flag.

## CLI Usage

Basic run:

```bash
python app2.py --input keywords.txt --output seo_opportunities.csv --cloud-mode
```

With AI provider:

```bash
python app2.py \
  --input keywords.txt \
  --cloud-mode \
  --ai-provider openai \
  --ai-model gpt-4o-mini \
  --ai-api-key YOUR_KEY
```

More control:

```bash
python app2.py \
  --input keywords.txt \
  --output seo_opportunities.csv \
  --timeframe "today 12-m" \
  --geo US \
  --growth-threshold 350 \
  --max-keywords 15 \
  --min-sleep 1.5 \
  --max-sleep 3.0 \
  --retries 1
```

CLI auto-exports additional artifacts:

- `seed_summary.csv`
- `title_ideas.csv`
- `seo_brief.md`

## Lightweight Utilities

1. Clean/dedupe seeds:

```bash
python kw_cleaner.py --input keywords.txt --output keywords.cleaned.txt --lowercase --sort
```

2. Expand seeds into long-tail variations:

```bash
python keyword_expander.py --input keywords.cleaned.txt --output keywords.expanded.txt
```

3. Rank opportunities:

```bash
python opportunity_ranker.py --input seo_opportunities.csv --output seo_opportunities_ranked.csv --top 20
```

4. Seed summary report:

```bash
python seed_report.py --input seo_opportunities_ranked.csv --output seed_summary.csv
```

5. Markdown brief:

```bash
python brief_builder.py --input seo_opportunities_ranked.csv --output seo_brief.md --top 15
```

6. Batch collector for larger lists:

```bash
python batch_collector.py --input keywords.expanded.txt --chunk-size 10 --output seo_opportunities_batched.csv
```

## Input Format

TXT: one keyword per line.

CSV: first column is treated as the keyword list.

## Output Columns (Ranked)

- `Seed_Keyword`
- `Recommended_Long_Tail`
- `Growth_Value`
- `Growth_%`
- `Long_Tail_Words`
- `Long_Tail_Chars`
- `Priority_Score`

## AI Providers And Runtime

- `none`: no AI calls
- `ollama`: local runtime only (`ollama serve` on your machine)
- `openai`: API key-based, cloud compatible
- `anthropic`: API key-based, cloud compatible
- `gemini`: API key-based, cloud compatible

For local Ollama:

```bash
pip install -r requirements-ai.txt
ollama serve
ollama pull llama3
```

In Streamlit:
- Enable AI analysis
- Pick provider/model
- Add API key only for cloud providers
# seo-trend-tool
