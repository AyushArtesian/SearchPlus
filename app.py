import requests
import hashlib
import hmac
import base64
from datetime import datetime
from urllib.parse import urlparse

# Config
username = "collectorinvestorapiuser"
base64_token = "U4uRz/MrYA5O4lQNw/zHIlq7v5ez+Mv8ljw80oq3pVU="
uri = "https://bid.collectorinvestorauctions.com/api/listing/search/0/5"

json_body = {
    "Items": {
        
    }
}

content_type = "application/json"


def generate_headers(username, base64_token, uri, body, content_type):
    # Content-MD5
    md5_bytes = hashlib.md5(body.encode("utf-8")).digest()
    content_md5 = base64.b64encode(md5_bytes).decode("utf-8")

    # Date RFC1123
    date = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")

    # Request path lowercase
    request_path = urlparse(uri).path.lower()

    # String to sign
    string_to_sign = (
        "GET\n"
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


def main():
    try:
        import json
        body_str = json.dumps(json_body, separators=(",", ":"))
        headers = generate_headers(username, base64_token, uri, body_str, content_type)

        print("\n--- Sending Request ---\n")
        print("Authorization:", headers["Authorization"])
        print("Date:", headers["Date"])
        print("Content-MD5:", headers["Content-MD5"])

        # ⚠ GET requests normally ignore body, maybe should be POST
        response = requests.get(uri, headers=headers, data=body_str)

        print("\n--- Response ---\n")
        print("Status:", response.status_code)
        print(response.text)

    except requests.RequestException as e:
        print("\n--- Error ---\n")
        print(str(e))


if __name__ == "__main__":
    main()