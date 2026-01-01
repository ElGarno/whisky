"""OpenAI integration for whisky recognition and content generation."""

import os
import json
import base64
from typing import List, Optional
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def encode_image(image_bytes: bytes) -> str:
    """Encode image bytes to base64."""
    return base64.b64encode(image_bytes).decode("utf-8")


def analyze_whisky_photo(image_bytes: bytes) -> dict:
    """
    Analyze a whisky bottle photo using GPT-4 Vision.
    Returns: {name, year, distillery, fill_level, confidence}
    """
    base64_image = encode_image(image_bytes)

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": """Analyze this whisky bottle photo and extract the following information.
Return a JSON object with these fields:
- name: The full whisky name (brand and expression, e.g. "Lagavulin 16 Year Old")
- year: The age statement as a number (e.g. 16), or null if not visible
- distillery: The distillery name (e.g. "Lagavulin")
- fill_level: Estimate how full the bottle is. Use one of: "full", "three_quarters", "half", "quarter", "near_empty"
- confidence: Your confidence in this identification from 0.0 to 1.0

Only return the JSON object, no other text."""
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    }
                ]
            }
        ],
        max_tokens=500
    )

    content = response.choices[0].message.content.strip()

    # Parse JSON from response (handle markdown code blocks)
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
        content = content.strip()

    return json.loads(content)


def generate_whisky_info(name: str, distillery: str, year: int = None) -> str:
    """
    Generate an engaging markdown info page about a whisky.
    """
    year_text = f"{year} Year Old" if year else ""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": f"""Write an engaging markdown page about {name} from {distillery} distillery.

Include these sections:
## About {distillery}
Brief history of the distillery (2-3 sentences)

## Tasting Notes
- **Nose**: Key aromas
- **Palate**: Flavor profile
- **Finish**: How it ends

## Fun Facts
2-3 interesting facts about this whisky or distillery

## Food Pairings
3-4 recommended food pairings

Keep it concise (300-400 words total). Use bullet points where appropriate.
Do not include a title heading at the start - it will be added separately."""
            }
        ],
        max_tokens=1000
    )

    return response.choices[0].message.content.strip()


def suggest_tasting_order(whiskies: list[dict]) -> list[dict]:
    """
    Suggest tasting orders for a list of whiskies.
    Input: List of dicts with {name, distillery, year}
    Returns: List of 3 suggested orders with explanations
    """
    whisky_list = "\n".join([
        f"- {w['name']} ({w.get('distillery', 'Unknown')}, {w.get('year', 'NAS')} years)"
        for w in whiskies
    ])

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": f"""I have these whiskies for a tasting:
{whisky_list}

Suggest 3 different tasting orders. Consider these principles:
- Light before heavy
- Younger before older (usually)
- Unpeated before peated
- Lower ABV before higher ABV
- Sweet before smoky

For each order, return a JSON array with 3 objects:
[
  {{
    "order_name": "Classic Progression",
    "whisky_names": ["name1", "name2", ...],
    "explanation": "Why this order works..."
  }},
  ...
]

Only return the JSON array, no other text."""
            }
        ],
        max_tokens=1000
    )

    content = response.choices[0].message.content.strip()

    # Parse JSON from response
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
        content = content.strip()

    return json.loads(content)


def generate_tasting_summary(ratings: list[dict], whiskies: list[str],
                              participants: list[str]) -> str:
    """
    Generate an AI summary of a tasting session.
    """
    ratings_text = "\n".join([
        f"- {r['participant']}: {r['whisky']} = {r['score']}/10" +
        (f" ({r['notes']})" if r.get('notes') else "")
        for r in ratings
    ])

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": f"""Analyze this whisky tasting session and write a fun summary.

Participants: {', '.join(participants)}
Whiskies tasted: {', '.join(whiskies)}

Ratings:
{ratings_text}

Write a markdown summary including:
## Tasting Results

### The Winner
Which whisky had the highest average score?

### Most Divisive
Which whisky had the biggest score variance?

### Participant Profiles
Brief fun characterization of each participant's preferences based on their ratings

### Interesting Patterns
Any notable patterns or surprises in the ratings

Keep it fun and engaging, about 200-300 words."""
            }
        ],
        max_tokens=800
    )

    return response.choices[0].message.content.strip()


def get_distillery_location(distillery_name: str) -> dict | None:
    """
    Get the geographic coordinates of a distillery.
    Returns: {latitude, longitude, region, country} or None
    """
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": f"""What are the geographic coordinates of {distillery_name} distillery?

Return a JSON object with:
- latitude: decimal number
- longitude: decimal number
- region: the whisky region (e.g. "Islay", "Speyside", "Highland", "Kentucky", etc.)
- country: the country (e.g. "Scotland", "USA", "Japan", etc.)

If you don't know the exact location, provide your best estimate for a well-known distillery.
Only return the JSON object, no other text."""
            }
        ],
        max_tokens=200
    )

    content = response.choices[0].message.content.strip()

    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
        content = content.strip()

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return None
