# Whisky Collection & Tasting App

A mobile-friendly web app for managing your whisky collection and running tasting sessions with friends.

## Features

- **Photo Recognition** - Snap a photo of a bottle, AI identifies the whisky (name, distillery, age, fill level)
- **Whisky Info Pages** - AI-generated tasting notes, distillery history, fun facts, and food pairings
- **Collection Statistics** - Value analytics, age distribution charts, and an interactive distillery map
- **Tasting Sessions** - AI suggests optimal tasting orders, track ratings from multiple participants, get AI-generated summaries

## Tech Stack

- **Frontend/Backend**: Streamlit
- **Database**: DuckDB (file-based, zero config)
- **AI**: OpenAI GPT-4o (vision + text)
- **Maps**: Folium

## Quick Start

### Local Development

```bash
# Clone the repo
git clone https://github.com/ElGarno/whisky.git
cd whisky

# Install dependencies
pip install -r requirements.txt

# Set your OpenAI API key
export OPENAI_API_KEY=sk-your-key-here

# Run the app
streamlit run app.py
```

Open http://localhost:8501

### Docker Deployment

```bash
# Create .env file with your API key
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# Build and run
docker-compose up -d
```

## Project Structure

```
whisky/
├── app.py                    # Main dashboard
├── pages/
│   ├── 1_Register_Whisky.py  # Photo upload & AI recognition
│   ├── 2_Whisky_Info.py      # Whisky details & markdown info
│   ├── 3_Statistics.py       # Charts, maps, analytics
│   └── 4_Tasting.py          # Tasting session management
├── services/
│   ├── db.py                 # DuckDB operations
│   └── ai.py                 # OpenAI integration
├── data/                     # DuckDB database (auto-created)
├── assets/                   # Uploaded images
├── Dockerfile
└── docker-compose.yml
```

## Usage

1. **Add Whiskies** - Upload a photo or enter manually on the Register page
2. **Browse Collection** - View AI-generated info pages for each whisky
3. **Check Stats** - See your collection value, age distribution, and map
4. **Run a Tasting** - Select whiskies, add participants, get AI-suggested orders, rate, and get a summary

## License

MIT