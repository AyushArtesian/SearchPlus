"""Search service for querying products by tags, title, and description."""

from src.storage import load_products


def search_products(query: str) -> dict:
    """
    Search products by query across tags, title/name, subtitle, and description.
    
    Scoring:
    - Tag match: 2 points
    - Title/name match: 5 points
    - Subtitle match: 2 points
    - Description match: 1 point
    
    Args:
        query: Search query string
    
    Returns:
        Dict with query, total count, and ranked results with highlighting
    """
    products = load_products()
    query_lower = query.lower().strip()
    
    if not query_lower:
        return {"query": query, "total": 0, "results": []}
    
    results = []
    
    for product in products:
        score = 0
        matched_tags = []
        
        # Get product fields (support both old and new schemas)
        tags = product.get("tags", [])
        title = (product.get("title") or product.get("name") or "").lower()
        subtitle = (product.get("subtitle") or "").lower()
        description = product.get("description", "").lower()
        category = product.get("category", "").lower()
        
        # Check tag matches (2 pts each)
        for tag in tags:
            tag_lower = tag.lower()
            if query_lower in tag_lower or tag_lower in query_lower:
                score += 2
                matched_tags.append(tag)
        
        # Check title/name match (5 pts)
        if query_lower in title:
            score += 5

        # Check subtitle match (2 pts)
        if subtitle and query_lower in subtitle:
            score += 2
        
        # Check description match (1 pt)
        if query_lower in description:
            score += 1
        
        # Check category match (1 pt)
        if query_lower in category:
            score += 1
        
        if score > 0:
            result = {
                "id": product.get("id"),
                "title": product.get("title") or product.get("name"),
                "subtitle": product.get("subtitle", ""),
                "category": product.get("category"),
                "description": product.get("description"),
                "image_url": product.get("image_url"),
                "tags": product.get("tags", []),
                "matched_tags": list(set(matched_tags)),  # unique matched tags
                "score": score
            }
            results.append(result)
    
    # Sort by score (descending)
    results.sort(key=lambda x: x["score"], reverse=True)
    
    return {
        "query": query,
        "total": len(results),
        "results": results
    }
