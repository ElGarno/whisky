"""OpenAI Integration für Whisky-Erkennung und Content-Generierung."""

import os
import json
import base64
from typing import List, Optional
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def encode_image(image_bytes: bytes) -> str:
    """Kodiere Bilddaten als Base64."""
    return base64.b64encode(image_bytes).decode("utf-8")


def analyze_whisky_photo(image_bytes: bytes) -> dict:
    """
    Analysiere ein Whisky-Flaschen-Foto mit GPT-4 Vision.
    Gibt zurück: {name, year, distillery, fill_level, confidence}
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
                        "text": """Analysiere dieses Whisky-Flaschen-Foto und extrahiere folgende Informationen.
Gib ein JSON-Objekt mit diesen Feldern zurück:
- name: Der vollständige Whisky-Name (Marke und Ausdruck, z.B. "Lagavulin 16 Year Old")
- year: Die Altersangabe als Zahl (z.B. 16), oder null wenn nicht sichtbar
- distillery: Der Name der Brennerei (z.B. "Lagavulin")
- fill_level: Schätze wie voll die Flasche ist. Verwende: "full", "three_quarters", "half", "quarter", "near_empty"
- confidence: Deine Sicherheit bei dieser Identifikation von 0.0 bis 1.0

Gib nur das JSON-Objekt zurück, keinen anderen Text."""
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

    # Parse JSON aus Antwort (behandle Markdown Code-Blöcke)
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
        content = content.strip()

    return json.loads(content)


def generate_whisky_info(name: str, distillery: str, year: int = None) -> str:
    """
    Generiere eine ansprechende Markdown-Infoseite über einen Whisky.
    """
    year_text = f"{year} Jahre alt" if year else ""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": f"""Schreibe eine ansprechende Markdown-Seite über {name} von der {distillery} Brennerei.
Schreibe auf Deutsch!

Füge diese Abschnitte ein:
## Über {distillery}
Kurze Geschichte der Brennerei (2-3 Sätze)

## Verkostungsnotizen
- **Nase**: Wichtige Aromen
- **Gaumen**: Geschmacksprofil
- **Abgang**: Wie er endet

## Wissenswertes
2-3 interessante Fakten über diesen Whisky oder die Brennerei

## Essensempfehlungen
3-4 empfohlene Speisen die gut dazu passen

Halte es prägnant (300-400 Wörter insgesamt). Verwende Aufzählungspunkte wo angemessen.
Füge keine Titelüberschrift am Anfang ein - diese wird separat hinzugefügt."""
            }
        ],
        max_tokens=1000
    )

    return response.choices[0].message.content.strip()


def suggest_tasting_order(whiskies: list[dict]) -> list[dict]:
    """
    Schlage Verkostungsreihenfolgen für eine Liste von Whiskies vor.
    Input: Liste von Dicts mit {name, distillery, year}
    Gibt zurück: Liste von 3 vorgeschlagenen Reihenfolgen mit Erklärungen
    """
    whisky_list = "\n".join([
        f"- {w['name']} ({w.get('distillery', 'Unbekannt')}, {w.get('year', 'NAS')} Jahre)"
        for w in whiskies
    ])

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": f"""Ich habe diese Whiskies für eine Verkostung:
{whisky_list}

Schlage 3 verschiedene Verkostungsreihenfolgen vor. Beachte diese Prinzipien:
- Leicht vor schwer
- Jünger vor älter (normalerweise)
- Ungetorft vor getorft
- Niedrigerer Alkoholgehalt vor höherem
- Süß vor rauchig

Für jede Reihenfolge, gib ein JSON-Array mit 3 Objekten zurück:
[
  {{
    "order_name": "Klassische Progression",
    "whisky_names": ["name1", "name2", ...],
    "explanation": "Warum diese Reihenfolge funktioniert..."
  }},
  ...
]

Schreibe die Erklärungen auf Deutsch!
Gib nur das JSON-Array zurück, keinen anderen Text."""
            }
        ],
        max_tokens=1000
    )

    content = response.choices[0].message.content.strip()

    # Parse JSON aus Antwort
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
        content = content.strip()

    return json.loads(content)


def generate_tasting_summary(ratings: list[dict], whiskies: list[str],
                              participants: list[str]) -> str:
    """
    Generiere eine KI-Zusammenfassung einer Verkostungs-Session.
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
                "content": f"""Analysiere diese Whisky-Verkostung und schreibe eine unterhaltsame Zusammenfassung.
Schreibe auf Deutsch!

Teilnehmer: {', '.join(participants)}
Verkostete Whiskies: {', '.join(whiskies)}

Bewertungen:
{ratings_text}

Schreibe eine Markdown-Zusammenfassung mit:
## Verkostungsergebnisse

### Der Gewinner
Welcher Whisky hatte die höchste Durchschnittsbewertung?

### Am kontroversesten
Welcher Whisky hatte die größte Varianz in den Bewertungen?

### Teilnehmerprofile
Kurze, unterhaltsame Charakterisierung der Vorlieben jedes Teilnehmers basierend auf ihren Bewertungen

### Interessante Muster
Bemerkenswerte Muster oder Überraschungen in den Bewertungen

Halte es unterhaltsam und ansprechend, etwa 200-300 Wörter."""
            }
        ],
        max_tokens=800
    )

    return response.choices[0].message.content.strip()


def get_distillery_location(distillery_name: str) -> dict | None:
    """
    Ermittle die geografischen Koordinaten einer Brennerei.
    Gibt zurück: {latitude, longitude, region, country} oder None
    """
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": f"""Was sind die geografischen Koordinaten der {distillery_name} Brennerei?

Gib ein JSON-Objekt zurück mit:
- latitude: Dezimalzahl
- longitude: Dezimalzahl
- region: Die Whisky-Region (z.B. "Islay", "Speyside", "Highland", "Kentucky", etc.)
- country: Das Land (z.B. "Schottland", "USA", "Japan", etc.)

Wenn du den genauen Standort nicht kennst, gib deine beste Schätzung für eine bekannte Brennerei an.
Gib nur das JSON-Objekt zurück, keinen anderen Text."""
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


def estimate_whisky_price(name: str, distillery: str, year: int = None) -> dict | None:
    """
    Schätze den Marktpreis eines Whiskys basierend auf aktuellen Marktdaten.
    Gibt zurück: {price_eur, price_range_min, price_range_max, source_info} oder None
    """
    year_text = f"{year} Jahre alt" if year else "ohne Altersangabe"

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": f"""Was ist der ungefähre Marktpreis für den Whisky "{name}" von {distillery} ({year_text})?

Recherchiere basierend auf deinem Wissen über aktuelle Whisky-Preise in Deutschland/Europa.

Gib ein JSON-Objekt zurück mit:
- price_eur: Der geschätzte Durchschnittspreis in Euro (als Zahl)
- price_range_min: Untere Preisspanne in Euro
- price_range_max: Obere Preisspanne in Euro
- source_info: Kurze Info woher die Schätzung stammt (z.B. "Basierend auf typischen Einzelhandelspreisen")

Falls der Whisky sehr selten oder unbekannt ist, schätze basierend auf ähnlichen Whiskys.
Gib nur das JSON-Objekt zurück, keinen anderen Text."""
            }
        ],
        max_tokens=300
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
