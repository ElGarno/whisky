# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Whisky Tasting Webapp - A mobile-friendly Streamlit app for managing a personal whisky collection and conducting tastings. Single user, DuckDB database, OpenAI for photo recognition and content generation.

## Tech Stack

- **Framework**: Streamlit (multi-page app)
- **Database**: DuckDB (file-based, `data/whisky.duckdb`)
- **AI**: OpenAI GPT-4o (vision + text)
- **Maps**: Folium + streamlit-folium
- **Deployment**: Docker

## Development Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
streamlit run app.py

# Run with Docker
docker-compose up --build

# Set API key
export OPENAI_API_KEY=sk-your-key
# or create .env file from .env.example
```

## Project Structure

```
whisky/
├── app.py                    # Main entry point
├── pages/
│   ├── 1_Register_Whisky.py  # Photo upload, AI recognition
│   ├── 2_Whisky_Info.py      # Markdown info pages
│   ├── 3_Statistics.py       # Charts, maps, analytics
│   └── 4_Tasting.py          # Tasting sessions, ratings
├── services/
│   ├── db.py                 # DuckDB operations
│   └── ai.py                 # OpenAI integration
├── data/                     # DuckDB file (gitignored)
└── assets/                   # Images (gitignored)
```

## Custom Commands

- `/intro` - Get project overview
- `/cap` - Review changes, create conventional commit, push

## Conventional Commits

Format: `<type>(<scope>): <subject>`

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `chore`
