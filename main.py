import httpx
from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from tagger import generate_tags
from search import search_products
from storage import load_products, add_or_update_product, get_product_count


# Mock data fallback
MOCK_PRODUCTS = [
    {
        "id": 1,
        "name": "Virat Kohli - Gold Edition",
        "category": "Cricket",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9b/Virat_Kohli_in_2023.jpg/220px-Virat_Kohli_in_2023.jpg",
        "description": "Indian national team captain, right-hand batsman, RCB franchise player. Known for chasing targets in ODIs and aggressive leadership.",
    },
    {
        "id": 2,
        "name": "Jasprit Bumrah - Platinum",
        "category": "Cricket",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5b/Jasprit_Bumrah_in_2023.jpg/220px-Jasprit_Bumrah_in_2023.jpg",
        "description": "Indian fast bowler, unique bowling action, deadly yorkers specialist. Mumbai Indians pacer and top wicket-taker.",
    },
    {
        "id": 3,
        "name": "Lionel Messi - World Cup Hero",
        "category": "Football",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b4/Lionel-Messi-Argentina-2022-FIFA-World-Cup_%28cropped%29.jpg/220px-Lionel-Messi-Argentina-2022-FIFA-World-Cup_%28cropped%29.jpg",
        "description": "Argentine forward, FIFA World Cup 2022 winner, multiple Ballon d Or. Former Barcelona, now Inter Miami.",
    },
    {
        "id": 4,
        "name": "Cristiano Ronaldo - Al Nassr",
        "category": "Football",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8c/Cristiano_Ronaldo_2018.jpg/220px-Cristiano_Ronaldo_2018.jpg",
        "description": "Portuguese striker, 5x Ballon d Or, UCL winner multiple times. Top scorer for Manchester United, Real Madrid, Juventus.",
    },
    {
        "id": 5,
        "name": "MS Dhoni - Captain Cool",
        "category": "Cricket",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/00/MS_Dhoni_in_2019.jpg/220px-MS_Dhoni_in_2019.jpg",
        "description": "Former Indian captain, wicketkeeper-batsman, ICC World Cup 2011 winner. Iconic helicopter shot. Chennai Super Kings legend.",
    },
]


# Request/Response models
class PipelineRunRequest(BaseModel):
    api_url: Optional[str] = None


class PipelineRunResponse(BaseModel):
    success: bool
    products_tagged: int
    total_tags: int


app = FastAPI(title="Sports Card Tagger", version="1.0.0")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def health_check():
    """Health check endpoint."""
    return {"status": "ok", "products_in_db": get_product_count()}


@app.post("/pipeline/run")
async def run_pipeline(request: PipelineRunRequest) -> PipelineRunResponse:
    """
    Fetch products from API, generate tags with GPT-4o, save to products.json.
    """
    products = []
    store_base_url = ""

    if request.api_url:
        # Try to fetch from external API
        try:
            print(f"📥 Fetching products from: {request.api_url}")
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(request.api_url)
                response.raise_for_status()

                data = response.json()
                products = data if isinstance(data, list) else data.get("products", [])

                # Extract base URL for relative image paths
                from urllib.parse import urlparse

                parsed = urlparse(request.api_url)
                store_base_url = f"{parsed.scheme}://{parsed.netloc}"

                print(f"✅ Fetched {len(products)} products")
        except Exception as e:
            print(f"❌ Failed to fetch from API: {e}")
            print("🔄 Falling back to mock data...")
            products = MOCK_PRODUCTS

    else:
        # Use mock data
        print("📋 Using mock product data...")
        products = MOCK_PRODUCTS

    if not products:
        return PipelineRunResponse(success=False, products_tagged=0, total_tags=0)

    # Tag each product with GPT-4o
    total_tags = 0
    for i, product in enumerate(products, 1):
        product_id = product.get("id", i)

        has_image = bool(
            product.get("image") or product.get("image_url") or product.get("thumbnail")
        )
        image_indicator = "with image" if has_image else "text only"

        print(
            f"🏷️  Tagging {i}/{len(products)}: {product.get('name', f'Product {product_id}')} ({image_indicator})..."
        )

        tags = generate_tags(product, store_base_url)
        product["tags"] = tags
        total_tags += len(tags)

        # Save immediately to preserve progress
        add_or_update_product(product)

        print(f"   → Generated {len(tags)} tags")

    print(f"\n✨ Pipeline complete! Tagged {len(products)} products ({total_tags} total tags)")

    return PipelineRunResponse(
        success=True, products_tagged=len(products), total_tags=total_tags
    )


@app.get("/search")
def search_endpoint(q: str = Query(..., description="Search query")) -> dict:
    """
    Search products by query across tags, name, and description.

    Scoring:
    - Tag match: 2 points
    - Name match: 5 points
    - Description match: 1 point

    Query example: /search?q=fast+bowler
    """
    return search_products(q)


@app.get("/products")
def get_all_products() -> list[dict]:
    """Get all products with their tags from products.json."""
    return load_products()


@app.get("/products/{product_id}/tags")
def get_product_tags(product_id: int) -> dict:
    """Get tags for a single product by ID."""
    from storage import get_product_by_id

    product = get_product_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")

    return {"id": product_id, "name": product.get("name"), "tags": product.get("tags", [])}


@app.get("/products/{product_id}")
def get_product(product_id: int) -> dict:
    """Get full product details by ID."""
    from storage import get_product_by_id

    product = get_product_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")

    return product


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
