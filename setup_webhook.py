"""
Run this ONCE after deploying to Vercel to register the webhook.
Usage: python setup_webhook.py https://your-project.vercel.app
"""
import sys
import httpx

BOT_TOKEN   = "8301928989:AAGw1b58x9NCDf51hDRl650PP8ges0UhS8Q"
TG_API      = f"https://api.telegram.org/bot{BOT_TOKEN}"

def main():
    if len(sys.argv) < 2:
        print("Usage: python setup_webhook.py https://your-project.vercel.app")
        sys.exit(1)

    base_url    = sys.argv[1].rstrip("/")
    webhook_url = f"{base_url}/api/webhook"

    print(f"Setting webhook to: {webhook_url}")

    with httpx.Client() as client:
        # Set webhook
        r = client.post(f"{TG_API}/setWebhook", json={
            "url":             webhook_url,
            "allowed_updates": ["message", "edited_message"],
            "drop_pending_updates": True
        })
        data = r.json()
        if data.get("ok"):
            print("✅ Webhook set successfully!")
        else:
            print(f"❌ Failed: {data}")
            sys.exit(1)

        # Confirm
        info = client.get(f"{TG_API}/getWebhookInfo").json()
        print(f"\nWebhook Info:")
        print(f"  URL:             {info['result'].get('url')}")
        print(f"  Pending updates: {info['result'].get('pending_update_count', 0)}")
        print(f"  Last error:      {info['result'].get('last_error_message', 'None')}")

if __name__ == "__main__":
    main()
