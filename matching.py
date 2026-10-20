
from difflib import SequenceMatcher


def similarity(text1, text2):
    """Return text similarity between 0 and 1."""
    text1 = (text1 or "").strip().lower()
    text2 = (text2 or "").strip().lower()

    if not text1 or not text2:
        return 0.0

    return SequenceMatcher(None, text1, text2).ratio()


def calculate_match_score(lost_item, found_item):
    """
    Each item is a dictionary containing:
    item_name, category, description, color, location
    """

    score = 0

    # Item name: 30 points
    score += 30 * similarity(
        lost_item["item_name"],
        found_item["item_name"]
    )

    # Category: 25 points
    if (
        lost_item.get("category")
        and found_item.get("category")
        and lost_item["category"].strip().lower()
        == found_item["category"].strip().lower()
    ):
        score += 25

    # Color: 20 points
    if (
        lost_item.get("color")
        and found_item.get("color")
        and lost_item["color"].strip().lower()
        == found_item["color"].strip().lower()
    ):
        score += 20

    # Location: 10 points
    score += 10 * similarity(
        lost_item["location"],
        found_item["location"]
    )

    # Description: 15 points
    score += 15 * similarity(
        lost_item["description"],
        found_item["description"]
    )

    return round(score, 2)
