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


def select_random_whiskies(eligible_whiskies: list[dict], count: int) -> dict:
    """
    KI-gestützte Auswahl von vielfältigen Whiskies für eine Verkostung.

    Args:
        eligible_whiskies: Liste von Dicts mit {id, name, year, distillery}
        count: Anzahl der auszuwählenden Whiskies (2-10)

    Returns:
        {
            "selected_whisky_ids": [int, ...],
            "selected_whisky_names": [str, ...],
            "diversity_explanation": "Begründung für die Auswahl...",
            "profiles": {"Name": "Geschmacksprofil", ...}
        }
    """
    whisky_list = "\n".join([
        f"- {w['name']} ({w.get('distillery', 'Unbekannt')}, {w.get('year', 'NAS')} Jahre)"
        for w in eligible_whiskies
    ])

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": f"""Wähle {count} Whiskies aus dieser Liste für eine vielfältige Verkostung:

{whisky_list}

Wähle Whiskies mit maximaler Vielfalt:
- Unterschiedliche Brennereien bevorzugen (nicht mehrere vom gleichen Hersteller)
- Unterschiedliche Geschmacksprofile (getorft vs. süß vs. fruchtig vs. würzig vs. maritim)
- Verschiedene Altersangaben wenn möglich
- Unterschiedliche Regionen (Islay, Speyside, Highland, Lowland, Campbeltown, etc.)

Gib ein JSON-Objekt zurück:
{{
  "selected_whisky_names": ["Name1", "Name2", ...],
  "diversity_explanation": "Deutsche Erklärung warum diese Auswahl vielfältig ist (2-3 Sätze)",
  "profiles": {{
    "Name1": "Kurzes Geschmacksprofil (z.B. 'Rauchig, maritim, torfig')",
    "Name2": "...",
    ...
  }}
}}

WICHTIG: Verwende die exakten Namen aus der Liste oben!
Gib nur das JSON-Objekt zurück, keinen anderen Text."""
            }
        ],
        max_tokens=1000
    )

    content = response.choices[0].message.content.strip()

    # Parse JSON (handle markdown code blocks)
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
        content = content.strip()

    result = json.loads(content)

    # Map names back to IDs with validation
    name_to_id = {w['name']: w['id'] for w in eligible_whiskies}
    selected_ids = []
    missing_names = []

    for name in result['selected_whisky_names']:
        if name in name_to_id:
            selected_ids.append(name_to_id[name])
        else:
            missing_names.append(name)

    # Warn but don't fail if some names don't match (AI might have slight variations)
    if missing_names and len(selected_ids) < 2:
        raise ValueError(
            f"KI hat Whisky-Namen zurückgegeben, die nicht in der Datenbank sind: {missing_names}. "
            f"Bitte versuche es erneut."
        )

    # Update the result with validated IDs and names
    result['selected_whisky_ids'] = selected_ids
    # Filter names to only those that matched
    result['selected_whisky_names'] = [
        name for name in result['selected_whisky_names']
        if name in name_to_id
    ]
    # Also filter profiles to match
    result['profiles'] = {
        name: profile for name, profile in result['profiles'].items()
        if name in name_to_id
    }

    return result


def generate_flavor_fingerprint(
    ratings: list[dict],
    participant_name: str,
    available_whiskies: list[str] = None
) -> dict:
    """
    Analysiere die Geschmackspräferenzen eines Teilnehmers basierend auf seinen Bewertungen.

    Args:
        ratings: Liste von Dicts mit {whisky_name, distillery, score, notes}
        participant_name: Name des Teilnehmers
        available_whiskies: Optionale Liste von Whiskies in der Sammlung für Empfehlungen

    Returns:
        {
            "profile_name": "Der Islay-Liebhaber",
            "description": "Kurze Beschreibung...",
            "preferences": {
                "peat": 0-100,
                "fruit": 0-100,
                "sweet": 0-100,
                "spice": 0-100,
                "maritime": 0-100,
                "sherry": 0-100
            },
            "favorite_regions": ["Islay", "Highland"],
            "recommendations_from_collection": ["Whisky aus Sammlung"],
            "recommendations_external": ["Externer Whisky 1", "Externer Whisky 2"]
        }
    """
    ratings_text = "\n".join([
        f"- {r['whisky_name']} ({r.get('distillery', 'Unbekannt')}): {r['score']}/10" +
        (f" - Notizen: {r['notes']}" if r.get('notes') else "")
        for r in ratings
    ])

    collection_info = ""
    if available_whiskies:
        collection_info = f"""

Die folgenden Whiskies sind in der Sammlung verfügbar (für Empfehlungen aus der Sammlung):
{chr(10).join(['- ' + w for w in available_whiskies])}
"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": f"""Analysiere die Whisky-Vorlieben von {participant_name} basierend auf diesen Bewertungen:

{ratings_text}
{collection_info}
Erstelle ein Geschmacksprofil als JSON-Objekt:
{{
  "profile_name": "Ein kreativer, lustiger Titel für den Whisky-Geschmack (auf Deutsch, z.B. 'Der Torfmonster-Flüsterer')",
  "description": "2-3 Sätze auf Deutsch, die den Geschmack charakterisieren",
  "preferences": {{
    "peat": <0-100 Wert basierend auf Vorliebe für torfige Whiskies>,
    "fruit": <0-100 für fruchtige Whiskies>,
    "sweet": <0-100 für süße Whiskies>,
    "spice": <0-100 für würzige Whiskies>,
    "maritime": <0-100 für maritime/salzige Whiskies>,
    "sherry": <0-100 für Sherry-Fass-Whiskies>
  }},
  "favorite_regions": ["Liste der bevorzugten Regionen basierend auf hohen Bewertungen"],
  "recommendations_from_collection": ["1-2 Whiskies AUS DER SAMMLUNG OBEN die zu diesem Profil passen - NUR wenn Sammlung angegeben wurde, sonst leere Liste"],
  "recommendations_external": ["2-3 Whisky-Empfehlungen die NICHT in der Sammlung sind und gut zum Profil passen würden"]
}}

WICHTIG:
- recommendations_from_collection: NUR Whiskies aus der angegebenen Sammlung verwenden! Wenn keine Sammlung angegeben, leere Liste.
- recommendations_external: Whiskies die der Person gefallen könnten und zum Kauf empfohlen werden.

Basiere die Analyse auf bekannten Geschmacksprofilen der bewerteten Whiskies.
Gib nur das JSON-Objekt zurück, keinen anderen Text."""
            }
        ],
        max_tokens=900
    )

    content = response.choices[0].message.content.strip()

    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
        content = content.strip()

    result = json.loads(content)

    # Backwards compatibility: merge old format if needed
    if 'recommendations' in result and 'recommendations_external' not in result:
        result['recommendations_external'] = result.pop('recommendations', [])
        result['recommendations_from_collection'] = []

    return result


def suggest_cocktails(whisky_name: str, distillery: str, fill_ml: int) -> dict:
    """
    Schlage Cocktails für eine fast leere Flasche vor.

    Args:
        whisky_name: Name des Whiskys
        distillery: Brennerei
        fill_ml: Verbleibende ML

    Returns:
        {
            "message": "Einleitender Text",
            "cocktails": [
                {
                    "name": "Cocktail Name",
                    "description": "Kurze Beschreibung",
                    "ingredients": ["Zutat 1", "Zutat 2"],
                    "ml_needed": 50
                }
            ],
            "neat_suggestion": "Warum man ihn doch pur trinken sollte"
        }
    """
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": f"""Du hast noch {fill_ml}ml von {whisky_name} ({distillery}) übrig.

Schlage 2-3 passende Cocktails vor, die zu diesem Whisky passen würden.
Berücksichtige den Charakter des Whiskys bei der Auswahl.

Antworte als JSON:
{{
  "message": "Einleitender Text auf Deutsch (1-2 Sätze, humorvoll, etwa 'Ja, wir wissen - Whisky mixen ist Ketzerei...')",
  "cocktails": [
    {{
      "name": "Cocktail Name",
      "description": "Kurze Beschreibung auf Deutsch",
      "ingredients": ["Zutat 1 mit Menge", "Zutat 2 mit Menge"],
      "ml_needed": <ML Whisky benötigt>
    }}
  ],
  "neat_suggestion": "Ein humorvoller Grund, warum man ihn doch lieber pur trinken sollte (auf Deutsch)"
}}

Gib nur das JSON-Objekt zurück."""
            }
        ],
        max_tokens=800
    )

    content = response.choices[0].message.content.strip()

    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
        content = content.strip()

    return json.loads(content)


def analyze_collection_health(whiskies: list[dict], stats: dict) -> dict:
    """
    Analysiere die Gesundheit der Whisky-Sammlung und gib Empfehlungen.

    Args:
        whiskies: Liste von Dicts mit {name, distillery, region, year, price, fill_pct}
        stats: Dict mit {total_bottles, total_value, avg_price}

    Returns:
        {
            "health_score": 0-100,
            "score_breakdown": {
                "diversity": 0-100,
                "value": 0-100,
                "fill_levels": 0-100,
                "age_range": 0-100
            },
            "strengths": ["Stärke 1", "Stärke 2"],
            "gaps": ["Lücke 1", "Lücke 2"],
            "recommendations": [
                {
                    "whisky": "Empfohlener Whisky",
                    "reason": "Warum er die Sammlung ergänzen würde",
                    "price_range": "€40-60"
                }
            ]
        }
    """
    whisky_list = "\n".join([
        f"- {w['name']} ({w.get('distillery', 'Unbekannt')}, {w.get('region', '?')}, " +
        f"{w.get('year', 'NAS')}J, €{w.get('price', '?')}, {w.get('fill_pct', 100)}% voll)"
        for w in whiskies
    ])

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": f"""Analysiere diese Whisky-Sammlung:

{whisky_list}

Statistiken:
- Gesamtflaschen: {stats.get('total_bottles', 0)}
- Gesamtwert: €{stats.get('total_value', 0)}
- Durchschnittspreis: €{stats.get('avg_price', 0)}

Bewerte die Sammlung und gib Empfehlungen als JSON:
{{
  "health_score": <0-100 Gesamtbewertung>,
  "score_breakdown": {{
    "diversity": <0-100 für Vielfalt der Regionen/Brennereien>,
    "value": <0-100 für Preis-Leistung und Wertsteigerungspotential>,
    "fill_levels": <0-100 basierend auf Füllständen>,
    "age_range": <0-100 für Altersspanne>
  }},
  "strengths": ["2-3 Stärken der Sammlung auf Deutsch"],
  "gaps": ["2-3 Lücken oder fehlende Aspekte auf Deutsch"],
  "recommendations": [
    {{
      "whisky": "Konkreter Whisky-Name",
      "reason": "Begründung auf Deutsch warum er die Sammlung ergänzt",
      "price_range": "Ungefähre Preisspanne"
    }}
  ]
}}

Berücksichtige:
- Fehlen wichtige Regionen? (Islay, Speyside, Highland, Campbeltown, Lowland, Islands)
- Gibt es eine gute Mischung aus getorft/ungetorft?
- Sind verschiedene Fasstypen vertreten?
- Wie ist die Altersspanne?

Gib nur das JSON-Objekt zurück."""
            }
        ],
        max_tokens=1000
    )

    content = response.choices[0].message.content.strip()

    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
        content = content.strip()

    return json.loads(content)


def generate_tasting_invitation(
    tasting_name: str,
    date: str,
    whiskies: list[str],
    host_name: str = None
) -> dict:
    """
    Generiere eine Einladung für eine Whisky-Verkostung.

    Returns:
        {
            "title": "Einladungstitel",
            "subtitle": "Untertitel",
            "body_text": "Einladungstext",
            "whisky_preview": "Vorschau der Whiskies",
            "footer": "Fußzeile"
        }
    """
    whisky_list = ", ".join(whiskies[:3])
    if len(whiskies) > 3:
        whisky_list += f" und {len(whiskies) - 3} weitere"

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": f"""Erstelle eine stilvolle Einladung für eine Whisky-Verkostung:

Verkostungsname: {tasting_name}
Datum: {date}
Whiskies: {', '.join(whiskies)}
{f'Gastgeber: {host_name}' if host_name else ''}

Erstelle eine Einladung als JSON:
{{
  "title": "Kreativer Titel für die Einladung (kurz, auf Deutsch)",
  "subtitle": "Eleganter Untertitel",
  "body_text": "2-3 Sätze einladender Text auf Deutsch, stilvoll aber nicht zu förmlich",
  "whisky_preview": "Appetitanregende Vorschau der Whiskies (1 Satz)",
  "footer": "Kurzer Abschluss, z.B. 'Slàinte!'"
}}

Gib nur das JSON-Objekt zurück."""
            }
        ],
        max_tokens=400
    )

    content = response.choices[0].message.content.strip()

    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
        content = content.strip()

    return json.loads(content)


def suggest_soundscape(whiskies: list[dict]) -> dict:
    """
    Schlage passende Ambient-Sounds und Spotify-Playlists für die Verkostung vor.

    Args:
        whiskies: Liste von Dicts mit {name, distillery, region}

    Returns:
        {
            "mood": "Stimmungsbeschreibung",
            "ambient_sounds": ["Regen an der schottischen Küste", "Knisterndes Kaminfeuer"],
            "spotify_searches": ["Scottish Folk Ambient", "Fireplace Jazz"],
            "fun_fact": "Wusstest du..."
        }
    """
    whisky_info = ", ".join([
        f"{w.get('name', 'Unbekannt')} ({w.get('region', '?')})"
        for w in whiskies[:5]
    ])

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": f"""Für eine Whisky-Verkostung mit diesen Whiskies:
{whisky_info}

Schlage passende Ambient-Sounds und Musik vor als JSON:
{{
  "mood": "Kurze Stimmungsbeschreibung auf Deutsch (1 Satz)",
  "ambient_sounds": ["3-4 passende Ambient-Sounds auf Deutsch, z.B. 'Schottischer Regen', 'Kaminfeuer'"],
  "spotify_searches": ["3-4 Spotify-Suchbegriffe für passende Playlists"],
  "fun_fact": "Ein interessanter Fakt über Whisky und Musik/Atmosphäre auf Deutsch"
}}

Berücksichtige die Regionen der Whiskies (Islay = maritim/wild, Speyside = gemütlich/süß, etc.)
Gib nur das JSON-Objekt zurück."""
            }
        ],
        max_tokens=400
    )

    content = response.choices[0].message.content.strip()

    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
        content = content.strip()

    return json.loads(content)
