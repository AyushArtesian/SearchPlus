#!/usr/bin/env python
"""
Example script to test the Sports Card Tagger API.
This demonstrates all available endpoints.
"""

import requests
import json

BASE_URL = "http://localhost:8000"


def test_health():
    """Test health check endpoint."""
    print("\n🏥 Testing health check...")
    response = requests.get(f"{BASE_URL}/")
    print(json.dumps(response.json(), indent=2))


def run_pipeline(api_url=None):
    """Run the tagging pipeline."""
    print("\n🚀 Running tagging pipeline...")
    payload = {"api_url": api_url}
    response = requests.post(f"{BASE_URL}/pipeline/run", json=payload)
    print(json.dumps(response.json(), indent=2))


def get_all_products():
    """Get all products."""
    print("\n📦 Getting all products...")
    response = requests.get(f"{BASE_URL}/products")
    products = response.json()
    print(f"Found {len(products)} products:")
    for p in products[:2]:  # Show first 2
        print(f"  - {p['name']} ({len(p['tags'])} tags)")
    if len(products) > 2:
        print(f"  ... and {len(products) - 2} more")


def get_product_by_id(product_id):
    """Get single product details."""
    print(f"\n📝 Getting product {product_id}...")
    response = requests.get(f"{BASE_URL}/products/{product_id}")
    product = response.json()
    print(f"Product: {product['name']}")
    print(f"Tags: {', '.join(product.get('tags', [])[:5])}...")


def get_product_tags(product_id):
    """Get tags for a product."""
    print(f"\n🏷️  Getting tags for product {product_id}...")
    response = requests.get(f"{BASE_URL}/products/{product_id}/tags")
    data = response.json()
    print(f"Product: {data['name']}")
    print(f"Tags ({len(data['tags'])}): {', '.join(data['tags'][:10])}...")


def search(query):
    """Search products."""
    print(f"\n🔍 Searching for: '{query}'...")
    response = requests.get(f"{BASE_URL}/search", params={"q": query})
    data = response.json()
    print(f"Found {data['total']} results:")
    for result in data['results'][:3]:  # Show top 3
        print(f"  #{result['id']}: {result['name']} (score: {result['score']})")
        print(f"      Matched tags: {', '.join(result['matched_tags'][:3])}")
    if data['total'] > 3:
        print(f"  ... and {data['total'] - 3} more")


def run_pipeline_with_custom_endpoint():
    """Example: Run pipeline with your custom auction site endpoint."""
    print("\n🚀 Running pipeline with custom endpoint...")
    payload = {
        "api_url": "https://bid.collectorinvestorauctions.com/api/products",
        "file_path": None,
        "data_format": None
    }
    response = requests.post(f"{BASE_URL}/pipeline/run", json=payload)
    result = response.json()
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    import sys

    print("=" * 60)
    print("Sports Card Tagger - API Test Script")
    print("=" * 60)

    try:
        # Test health
        test_health()

        # Run pipeline with mock data
        print("\n" + "=" * 60)
        print("Test 1: Using Mock Data")
        print("=" * 60)
        run_pipeline(api_url=None)
        
        # Uncomment to test with your custom auction site endpoint (after you set it up)
        # print("\n" + "=" * 60)
        # print("Test 2: Using Custom Auction Site Endpoint")
        # print("=" * 60)
        # run_pipeline_with_custom_endpoint()

        # Get all products
        get_all_products()

        # Get single product
        get_product_by_id(1)

        # Get tags for product
        get_product_tags(2)

        # Search examples
        search("fast bowler")
        search("world cup")
        search("gold")
        
        # Search sports cards examples
        search("psa 10")
        search("rookie card")

        print("\n" + "=" * 60)
        print("✅ All tests completed!")
        print("=" * 60)

    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Could not connect to API at", BASE_URL)
        print("   Make sure the server is running:")
        print("   uvicorn main:app --reload --port 8000")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
