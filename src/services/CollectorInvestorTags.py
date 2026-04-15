import requests
import hashlib
import hmac
import base64
import json
import datetime
from urllib.parse import urlparse
from pathlib import Path

# Config
username = "collectorinvestorapiuser"
base64_token = "U4uRz/MrYA5O4lQNw/zHIlq7v5ez+Mv8ljw80oq3pVU="
uri = "https://bid.collectorinvestorauctions.com/api/listing/createtags"

content_type = "application/json"

# Path to products.json
PRODUCTS_JSON_PATH = Path(__file__).parent.parent.parent.parent / "data" / "products.json"


def generate_headers(username, base64_token, uri, body, content_type):
    # Content-MD5
    md5_bytes = hashlib.md5(body.encode("utf-8")).digest()
    content_md5 = base64.b64encode(md5_bytes).decode("utf-8")

    # Date RFC1123
    date = datetime.datetime.now(datetime.timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")

    # Request path lowercase
    request_path = urlparse(uri).path.lower()

    # String to sign
    string_to_sign = (
        "POST\n"
        + content_md5 + "\n"
        + content_type + "\n"
        + date + "\n"
        + username + "\n"
        + request_path
    )

    # HMAC SHA256
    token_bytes = base64.b64decode(base64_token)
    signature = base64.b64encode(
        hmac.new(token_bytes, string_to_sign.encode("utf-8"), hashlib.sha256).digest()
    ).decode("utf-8")

    return {
        "Date": date,
        "Content-MD5": content_md5,
        "Authorization": f"RWX_SECURE {username}:{signature}",
        "Content-Type": content_type,
    }


def load_products():
    """Load products from products.json"""
    try:
        with open(PRODUCTS_JSON_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: products.json not found at {PRODUCTS_JSON_PATH}")
        return []
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in products.json - {e}")
        return []


def send_tags_for_product(product):
    """Send tags for a single product to the API"""
    try:
        listing_id = str(product.get("ListingID"))
        tags_list = product.get("tags", [])
        tags_str = ", ".join(tags_list)
        
        # Create JSON body in required format
        json_body = {
            "Items": {
                "ListingID": listing_id,
                "Tags": tags_str
            }
        }
        
        body_str = json.dumps(json_body, separators=(",", ":"))
        headers = generate_headers(username, base64_token, uri, body_str, content_type)
        
        response = requests.post(uri, headers=headers, data=body_str)
        
        is_success = 200 <= response.status_code < 300
        
        return {
            "listing_id": listing_id,
            "title": product.get("title", ""),
            "status_code": response.status_code,
            "success": is_success,
            "response": response.text,
            "headers": dict(response.headers) if not is_success else {}
        }
    
    except Exception as e:
        return {
            "listing_id": str(product.get("ListingID")),
            "title": product.get("title", ""),
            "status_code": None,
            "success": False,
            "response": str(e),
            "headers": {}
        }


def send_all_tags(from_storage=True):
    """
    Load all products and send their tags to the API.
    
    Args:
        from_storage: If True, load from database storage (default). If False, load from products.json
    
    Returns:
        List of result dictionaries for each product
    """
    if from_storage:
        try:
            from src.storage import load_products as load_from_storage
            products = load_from_storage()
        except ImportError:
            print("Storage module not available, using products.json instead")
            products = load_products()
    else:
        products = load_products()
    
    if not products:
        print("No products to process.")
        return []
    
    print(f"\n--- Processing {len(products)} products ---\n")
    
    successful = 0
    failed = 0
    results = []
    
    for product in products:
        result = send_tags_for_product(product)
        results.append(result)
        
        if result["success"]:
            successful += 1
            print(f"✓ [{result['listing_id']}] {result['title'][:50]}... - Success")
        else:
            failed += 1
            status = result.get('status_code', 'ERROR')
            response_text = result['response'][:100] if result['response'] else "(empty response)"
            print(f"✗ [{result['listing_id']}] {result['title'][:50]}... - Status: {status}")
            if response_text:
                print(f"  Response: {response_text}")
    
    print(f"\n--- Summary ---")
    print(f"Total: {len(products)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}\n")
    
    return results


def main():
    send_all_tags()


if __name__ == "__main__":
    main()