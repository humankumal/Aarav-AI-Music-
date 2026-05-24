#!/usr/bin/env python3
"""Seed initial artist profiles into Firestore (or local storage fallback)."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

CONFIG_DIR = Path("config/artists")
STORAGE_DIR = Path("storage")


def seed_to_local():
    print("Seeding artist configs to local storage (Firestore not configured)...")
    for config_file in CONFIG_DIR.glob("*.json"):
        artist_id = config_file.stem
        config = json.loads(config_file.read_text())
        out_path = STORAGE_DIR / "artists" / f"{artist_id}.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(config, indent=2, ensure_ascii=False))
        print(f"  Seeded: {artist_id} → {out_path}")


def seed_to_firestore():
    try:
        import firebase_admin
        from firebase_admin import credentials, firestore as fs

        cred_path = Path("firebase/service-account.json")
        if not cred_path.exists():
            print("No Firebase service account found. Falling back to local storage.")
            seed_to_local()
            return

        cred = credentials.Certificate(str(cred_path))
        firebase_admin.initialize_app(cred)
        db = fs.client()

        for config_file in CONFIG_DIR.glob("*.json"):
            artist_id = config_file.stem
            config = json.loads(config_file.read_text())
            db.collection("artists").document(artist_id).set(config)
            print(f"  Seeded to Firestore: {artist_id}")

    except ImportError:
        print("firebase-admin not installed. Falling back to local storage.")
        seed_to_local()


if __name__ == "__main__":
    seed_to_firestore()
    print("\nArtist seed complete ✓")
