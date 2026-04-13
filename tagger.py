import os
import json
import re
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI()  # reads OPENAI_API_KEY from .env automatically


def generate_tags(product: dict, store_base_url: str = "") -> list[str]:
    """
    Generate AI tags for a product using GPT-4o with vision.
    
    Args:
        product: Product dict with id, name, description, image_url, category
        store_base_url: Base URL to prepend to relative image paths
    
    Returns:
        List of generated tags, or empty list if tagging fails
    """
    image_url = (
        product.get("image")
        or product.get("image_url")
        or product.get("thumbnail")
        or None
    )

    # Convert relative image paths to absolute
    if image_url and image_url.startswith("/"):
        if store_base_url:
            image_url = store_base_url.rstrip("/") + image_url
        else:
            image_url = None  # Skip if we can't resolve it

    text_prompt = f"""You are a sports trading card tagging expert for an ecommerce search engine.
Analyze this product card — read the image carefully along with the name and description.
Generate 15-20 highly relevant search tags that buyers would actually type when searching.

Product name: {product.get('name', '')}
Category: {product.get('category', '')}
Description: {product.get('description', '')}

Generate tags covering:
- Player name + common spelling variations and nicknames
- Team names (national + franchise/club)
- Nationality and country
- Playing role/position (e.g. 'fast bowler', 'right hand batsman', 'striker')
- Playing style (e.g. 'aggressive batsman', 'death over specialist', 'free kick specialist')
- Achievements (e.g. 'world cup winner', 'ballon dor', 'ipl champion')
- Card rarity/type visible in image (e.g. 'gold foil', 'holographic', 'platinum border')
- Jersey number or colors visible in the image
- Era / generation (e.g. 'modern era', '90s legend')
- Sport name and format (e.g. 'test cricket', 'T20', 'champions league')
- Any text, logo, or design visible on the card image

Return ONLY a raw JSON array of tag strings. No explanation, no markdown, no backticks.
Example: ["virat kohli","kohli","rcb","royal challengers","indian batsman","run chase king","gold edition","right hand bat"]"""

    # Build message content — include image if available
    content = []

    if image_url:
        content.append(
            {
                "type": "image_url",
                "image_url": {
                    "url": image_url,
                    "detail": "high",  # high = reads fine text, jersey numbers, logos on the card
                },
            }
        )

    content.append({"type": "text", "text": text_prompt})

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": content}],
            max_tokens=500,
            temperature=0.3,  # lower temp = more consistent, focused tags
        )

        raw = response.choices[0].message.content.strip()

        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            # fallback: extract anything inside [ ]
            match = re.search(r"\[.*?\]", raw, re.DOTALL)
            return json.loads(match.group()) if match else []

    except Exception as e:
        print(f"❌ Error calling GPT-4o: {e}")
        return []
