import argparse
import os
import requests
import hashlib
import hmac
import base64
from datetime import datetime, UTC
from urllib.parse import urlparse
import certifi

# Config
username = "collectorinvestorapiuser"
base64_token = "U4uRz/MrYA5O4lQNw/zHIlq7v5ez+Mv8ljw80oq3pVU="
uri = "https://bid.collectorinvestorauctions.com/api/event/SearchListing"

content_type = "application/json"


def generate_headers(username, base64_token, uri, content_type):
    # ✅ No body → MD5 of empty string
    md5_bytes = hashlib.md5(b"").digest()
    content_md5 = base64.b64encode(md5_bytes).decode("utf-8")

    # ✅ RFC1123 Date (timezone aware)
    date = datetime.now(UTC).strftime("%a, %d %b %Y %H:%M:%S GMT")

    # Request path lowercase
    request_path = urlparse(uri).path.lower()

    # ✅ String to sign (GET request)
    string_to_sign = (
        "GET\n"
        + content_md5 + "\n"
        + content_type + "\n"
        + date + "\n"
        + username + "\n"
        + request_path
    )

    # HMAC SHA256 signature
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


def parse_args():
    parser = argparse.ArgumentParser(description="CollectorInvestor API tester")
    parser.add_argument(
        "--ca-bundle",
        dest="ca_bundle",
        help="Path to a custom CA bundle PEM file",
    )
    parser.add_argument(
        "--insecure",
        dest="insecure",
        action="store_true",
        help="Disable SSL verification for local testing",
    )
    return parser.parse_args()


def get_verify_path(args):
    # Use CLI arg first, then env var, then certifi default.
    return args.ca_bundle or os.environ.get("COLLECTOR_INVESTOR_CA_BUNDLE") or certifi.where()


def allow_insecure(args):
    return args.insecure or os.environ.get("COLLECTOR_INVESTOR_INSECURE", "").strip().lower() in {"1", "true", "yes", "y"}


def is_network_block(response):
    if response.status_code != 403:
        return False
    body = response.text.lower()
    return any(
        marker in body
        for marker in [
            "blocked site",
            "access restricted",
            "sophos",
            "fw.artesian.io",
            "network administration",
            "blocked by",
        ]
    )


def main(args):
    try:
        headers = generate_headers(username, base64_token, uri, content_type)

        print("\n--- Sending Request ---\n")
        print("Authorization:", headers["Authorization"])
        print("Date:", headers["Date"])
        print("Content-MD5:", headers["Content-MD5"])

        verify_path = get_verify_path(args)
        print("Verify path:", verify_path)
        response = requests.get(
            uri,
            headers=headers,
            verify=verify_path,
        )

        print("\n--- Response ---\n")
        print("Status:", response.status_code)

        if is_network_block(response):
            print("The request is being blocked by your network or web filter.")
            print("This looks like a corporate firewall/proxy block, not an issue with the request signature.")
            print("If you need access, allow the site through your network filter or try from an unrestricted network.")
            return

        print(response.text)

    except requests.exceptions.SSLError as e:
        print("\n--- SSL Error ---\n")
        print(str(e))
        if allow_insecure(args):
            print("\n-- INSECURE MODE ENABLED --")
            print("Retrying with SSL verification disabled. Use only for local testing.")
            insecure_response = requests.get(uri, headers=headers, verify=False)
            print("\n--- Insecure Response ---\n")
            print("Status:", insecure_response.status_code)
            if is_network_block(insecure_response):
                print("The request is still being blocked by your network or web filter.")
                print("This is not a certificate issue; the corporate firewall/proxy is intercepting the request.")
                return
            print(insecure_response.text)
            return

        if args.ca_bundle or os.environ.get("COLLECTOR_INVESTOR_CA_BUNDLE"):
            print("\nThe custom CA bundle path may be invalid or not contain the issuer chain.")
        else:
            print(
                "\nThe remote server certificate chain appears broken or incomplete. "
                "This is a server-side TLS issue, not a signing issue. "
                "Ask the server operator to fix the certificate chain, or provide a valid CA bundle "
                "with --ca-bundle or COLLECTOR_INVESTOR_CA_BUNDLE."
            )
        print("\nTemporary workaround: run with --insecure or set COLLECTOR_INVESTOR_INSECURE=1.")
    except requests.RequestException as e:
        print("\n--- Error ---\n")
        print(str(e))


if __name__ == "__main__":
    main(parse_args())