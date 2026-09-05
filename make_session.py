"""V2 setup helper: creates TELEGRAM_SESSION_STRING step by step.

Run:  pip install telethon   THEN   python make_session.py
You will type:
  1. API_ID + API_HASH  (from https://my.telegram.org -> API development tools)
  2. Your phone number (e.g. +2567XXXXXXXX) — Telegram sends a login code to your app
  3. The login code from your Telegram app
  4. Your 2FA password, ONLY if you have one (else just press Enter)
Output: a long session string. Paste it back to your CTO, or save it as the
GitHub secret TELEGRAM_SESSION_STRING. It is read-only in our bot (history read).
You can revoke it anytime: Telegram -> Settings -> Devices -> Terminate session.
"""
import os

def main():
    try:
        from telethon.sync import TelegramClient
        from telethon.sessions import StringSession
    except ImportError:
        print("First run:  pip install telethon")
        return
    api_id = input("API_ID: ").strip()
    api_hash = input("API_HASH: ").strip()
    phone = input("Phone (e.g. +2567XXXXXXXX): ").strip()
    with TelegramClient(StringSession(), int(api_id), api_hash) as client:
        client.start(phone=phone)
        me = client.get_me()
        print(f"\nLogged in as: {getattr(me, 'first_name', '?')} (@{getattr(me, 'username', '?')})")
        sess = client.session.save()
        print("\n==== COPY EVERYTHING BETWEEN THE LINES ====")
        print(sess)
        print("==== END ====\n")
        print("Send this string to your CTO (or save as GitHub secret TELEGRAM_SESSION_STRING).")

if __name__ == "__main__":
    main()
