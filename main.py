"""FastAPI application and pipeline orchestration."""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from src.models import PipelineRunRequest, PipelineRunResponse, PostTagsResponse, PostTagResult, FullEventPipelineRequest, FullEventPipelineResponse
from src.services.collector_investor import fetch_products
from src.services.tagger_service import generate_tags
from src.services.search_service import search_products
from src.services.CollectorInvestorTags import send_all_tags
from src.storage import load_products, add_or_update_product, get_product_count, should_skip_tagging, record_tagging


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
    Fetch products from CollectorInvestor, generate tags with OpenAI, save to database,
    and post tags to Collector Investor API - ONE BY ONE.
    
    Workflow:
    1. Fetch product (for specific event)
    2. Generate tags
    3. Save to database
    4. Post tags to API
    5. Record in tagging history to prevent duplicates
    
    REQUIRED: event_id must be provided
    """
    # Validate event_id is provided and not empty
    if not request.event_id or not request.event_id.strip():
        raise HTTPException(
            status_code=400,
            detail="event_id is required. Please provide a CollectorInvestor Event ID (e.g., '4053663')"
        )
    
    try:
        products = fetch_products(
            offset=request.offset,
            limit=request.limit,
            timeout=request.timeout,
            status=request.status,
            event_id=request.event_id,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)) from e

    if not products:
        return PipelineRunResponse(
            success=True,
            fetched=0,
            products_tagged=0,
            total_tags=0,
            tags_posted=0,
            tags_posted_failed=0,
        )

    # One-by-one workflow: Tag → Save → Post for each product
    total_tags = 0
    tags_posted = 0
    tags_posted_failed = 0
    event_id = request.event_id.strip()  # Normalize event_id

    for i, product in enumerate(products, 1):
        product_id = int(product.get("id", i))
        event_id = request.event_id or "default"  # Use "default" if no event_id provided
        has_image = bool(product.get("image_url"))
        image_indicator = "with image" if has_image else "text only"

        print(f"\n{'='*70}")
        print(f"[{i}/{len(products)}] Processing: {product.get('title', f'Product {product_id}')} ({image_indicator})...")
        print(f"{'='*70}")

        # Check if already tagged in this event
        if should_skip_tagging(product_id, event_id):
            print(f"  ⊘ Skipped (already tagged in event {event_id})")
            continue

        # Step 1: Generate tags
        print(f"  → Generating tags...")
        try:
            tags = generate_tags(product)
            product["tags"] = tags

            # Keep compatibility with any old code that reads "name".
            if not product.get("name") and product.get("title"):
                product["name"] = product["title"]

            total_tags += len(tags)
            print(f"  ✓ Generated {len(tags)} tags")
        except Exception as e:
            print(f"  ✗ Tag generation failed: {e}")
            record_tagging(product_id, event_id, 0, "failed", str(e))
            continue

        # Step 2: Save to database
        print(f"  → Saving to database...")
        try:
            add_or_update_product(product)
            print(f"  ✓ Saved to database")
        except Exception as e:
            print(f"  ✗ Failed to save: {e}")
            continue

        # Step 3: Post tags to API
        print(f"  → Posting tags to Collector Investor API...")
        post_success = False
        try:
            from src.services.CollectorInvestorTags import send_tags_for_product
            post_result = send_tags_for_product(product)
            
            if post_result.get("success"):
                tags_posted += 1
                post_success = True
                print(f"  ✓ Posted successfully (Status: {post_result.get('status_code')})")
            else:
                tags_posted_failed += 1
                print(f"  ✗ Post failed (Status: {post_result.get('status_code')}) - {post_result.get('response')}")
        except Exception as e:
            tags_posted_failed += 1
            print(f"  ✗ Post error: {e}")
        
        # Step 4: Record in tagging history
        status = "posted" if post_success else "pending"
        record_tagging(product_id, event_id, len(tags), status)

    print(f"\n{'='*70}")
    print(f"Pipeline complete!")
    print(f"  • Fetched: {len(products)}")
    print(f"  • Tagged: {len(products)}")
    print(f"  • Total tags: {total_tags}")
    print(f"  • Posted: {tags_posted}")
    print(f"  • Failed: {tags_posted_failed}")
    print(f"{'='*70}\n")

    return PipelineRunResponse(
        success=True,
        fetched=len(products),
        products_tagged=len(products),
        total_tags=total_tags,
        tags_posted=tags_posted,
        tags_posted_failed=tags_posted_failed,
    )


@app.get("/search")
def search_endpoint(q: str = Query(..., description="Search query")) -> dict:
    """
    Search products by query across tags, title/name, subtitle, and description.

    Scoring:
    - Tag match: 2 points
    - Title/name match: 5 points
    - Subtitle match: 2 points
    - Description match: 1 point

    Query example: /search?q=patrick+ewing
    """
    return search_products(q)


@app.post("/tags/post-all")
def post_all_tags_endpoint() -> PostTagsResponse:
    """
    Post all product tags to Collector Investor API.
    
    This endpoint reads all products from the database, transforms them to the required format,
    and sends their tags to the Collector Investor API for each listing.
    
    Returns a detailed summary of which products succeeded and failed.
    """
    try:
        results = send_all_tags()
        
        if not results:
            return PostTagsResponse(
                success=False,
                total=0,
                successful=0,
                failed=0,
                results=[]
            )
        
        # Count successes and failures
        successful = sum(1 for r in results if r["success"])
        failed = sum(1 for r in results if not r["success"])
        
        # Convert results to PostTagResult models
        post_results = [
            PostTagResult(
                listing_id=r["listing_id"],
                title=r["title"],
                status_code=r.get("status_code"),
                success=r["success"],
                response=r["response"]
            )
            for r in results
        ]
        
        return PostTagsResponse(
            success=failed == 0,
            total=len(results),
            successful=successful,
            failed=failed,
            results=post_results
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/products")
def get_all_products() -> list[dict]:
    """Get all products with their tags from database."""
    return load_products()


@app.get("/products/{product_id}/tags")
def get_product_tags(product_id: int) -> dict:
    """Get tags for a single product by ID."""
    from src.storage import get_product_by_id

    product = get_product_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")

    return {
        "id": product_id,
        "title": product.get("title") or product.get("name"),
        "tags": product.get("tags", []),
    }


@app.get("/products/{product_id}")
def get_product(product_id: int) -> dict:
    """Get full product details by ID."""
    from src.storage import get_product_by_id

    product = get_product_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")

    return product


@app.get("/tagging-history")
def get_tagging_history_endpoint(product_id: int = None, event_id: str = None) -> dict:
    """Get tagging history records for debugging."""
    from src.storage import get_tagging_history
    
    records = get_tagging_history(product_id=product_id, event_id=event_id)
    return {
        "total_records": len(records),
        "records": records
    }


if __name__ == "__main__":
    import uvicorn
    from src.config import API_HOST, API_PORT, API_RELOAD

    uvicorn.run(app, host=API_HOST, port=API_PORT, reload=API_RELOAD)

@app.post("/pipeline/run-full-event")
async def run_full_event_pipeline(request: FullEventPipelineRequest) -> FullEventPipelineResponse:
    """
    Process ALL listings for a specific event automatically.
    
    Workflow: Fetch page → Process each product (generate → save → post) → Fetch next page → Repeat
    
    ONLY requires: event_id
    
    Example:
        curl -X POST http://localhost:8000/pipeline/run-full-event \
          -H "Content-Type: application/json" \
          -d '{"event_id": "4053663"}'
    """
    if not request.event_id or not request.event_id.strip():
        raise HTTPException(
            status_code=400,
            detail="event_id is required"
        )
    
    event_id = request.event_id.strip()
    page_size = 50
    
    print(f"\n{'='*70}")
    print(f"Processing ALL listings for event: {event_id}")
    print(f"Page-by-page workflow: Fetch → Process → Next page")
    print(f"{'='*70}\n")
    
    # Metrics
    total_fetched = 0
    total_tags = 0
    tags_posted = 0
    tags_posted_failed = 0
    products_tagged = 0
    products_skipped = 0
    pages_processed = 0
    global_product_counter = 0
    
    import time
    
    # Page-by-page pagination
    offset = 0
    while True:
        pages_processed += 1
        print(f"\n{'─'*70}")
        print(f"📄 PAGE {pages_processed}: Fetching offset={offset}, limit={page_size}...")
        print(f"{'─'*70}")
        
        # Fetch page
        try:
            page_products = fetch_products(
                offset=offset,
                limit=page_size,
                timeout=45,
                event_id=event_id
            )
        except Exception as e:
            print(f"✗ ERROR fetching page {pages_processed}: {e}")
            raise HTTPException(status_code=502, detail=str(e))
        
        if not page_products:
            print(f"✓ End of results - no more products")
            break
        
        print(f"✓ Fetched {len(page_products)} items for this page")
        total_fetched += len(page_products)
        
        # Process each product on this page: Generate → Save → Post
        for product_idx, product in enumerate(page_products, 1):
            global_product_counter += 1
            product_id = int(product.get("id", global_product_counter))
            title = product.get("title", "Unknown")
            
            # Check if already tagged
            if should_skip_tagging(product_id, event_id):
                products_skipped += 1
                print(f"  [{product_idx}/{len(page_products)}] ⊘ {product_id} - Skipped (already tagged)")
                continue
            
            # Generate tags
            try:
                print(f"  [{product_idx}/{len(page_products)}] → {product_id} - Generating tags...")
                tags = generate_tags(product)
                product["tags"] = tags
                if not product.get("name") and product.get("title"):
                    product["name"] = product["title"]
                
                total_tags += len(tags)
                print(f"  [{product_idx}/{len(page_products)}] ✓ Generated {len(tags)} tags")
            except Exception as e:
                print(f"  [{product_idx}/{len(page_products)}] ✗ Tag generation failed: {str(e)[:100]}")
                record_tagging(product_id, event_id, 0, "failed", str(e))
                continue
            
            # Save to database
            try:
                add_or_update_product(product)
                print(f"  [{product_idx}/{len(page_products)}] ✓ Saved to database")
            except Exception as e:
                print(f"  [{product_idx}/{len(page_products)}] ✗ Failed to save: {str(e)[:100]}")
                continue
            
            # Post to API
            post_success = False
            try:
                from src.services.CollectorInvestorTags import send_tags_for_product
                print(f"  [{product_idx}/{len(page_products)}] → Posting to API...")
                post_result = send_tags_for_product(product)
                
                if post_result.get("success"):
                    tags_posted += 1
                    post_success = True
                    print(f"  [{product_idx}/{len(page_products)}] ✓ Posted successfully")
                else:
                    tags_posted_failed += 1
                    print(f"  [{product_idx}/{len(page_products)}] ✗ Post failed: {post_result.get('response')}")
            except Exception as e:
                tags_posted_failed += 1
                print(f"  [{product_idx}/{len(page_products)}] ✗ Post error: {str(e)[:100]}")
            
            # Record in history
            status = "posted" if post_success else "pending"
            record_tagging(product_id, event_id, len(tags), status)
            products_tagged += 1
        
        # Move to next page
        offset += 1
        
        # Delay before next page
        if page_products:
            print(f"\n⏳ Waiting 1 second before next page...")
            time.sleep(1.0)
    
    print(f"\n{'='*70}")
    print(f"Event {event_id} - Complete!")
    print(f"  • Pages processed: {pages_processed}")
    print(f"  • Total fetched: {total_fetched}")
    print(f"  • Tagged: {products_tagged}")
    print(f"  • Skipped: {products_skipped}")
    print(f"  • Total tags: {total_tags}")
    print(f"  • Posted: {tags_posted}")
    print(f"  • Failed: {tags_posted_failed}")
    print(f"{'='*70}\n")
    
    return FullEventPipelineResponse(
        success=True,
        event_id=event_id,
        total_fetched=total_fetched,
        products_tagged=products_tagged,
        products_skipped=products_skipped,
        total_tags=total_tags,
        tags_posted=tags_posted,
        tags_posted_failed=tags_posted_failed,
        pages_processed=pages_processed,
        total_pages=pages_processed,
    )