"""
Catalogue Note Command

CLI command for adding or viewing notes for a catalogue version.
"""

from __future__ import annotations
from pathlib import Path
from argparse import Namespace
import json
from datetime import datetime

from ...core.logger import get_logger


log = get_logger(__name__)


def run(args: Namespace) -> None:
    """
    Run catalogue note command.

    Args:
        args: Parsed command-line arguments
    """
    # Get catalogue directory
    catalogue_dir = Path(args.catalogue_dir)

    # Validate path
    if not catalogue_dir.exists():
        log.error(f"Catalogue directory does not exist: {catalogue_dir}")
        return

    # Check for metadata file
    metadata_path = catalogue_dir / "metadata.json"
    if not metadata_path.exists():
        log.error(f"Metadata file not found: {metadata_path}")
        return

    # Notes file path
    notes_path = catalogue_dir / "notes.json"

    # Load existing notes if they exist
    existing_notes = {}
    if notes_path.exists():
        try:
            with open(notes_path, "r", encoding="utf-8") as f:
                existing_notes = json.load(f)
        except Exception as e:
            log.warning(f"Failed to load existing notes: {e}")

    # If no note provided, display existing notes
    if args.note is None:
        if not existing_notes or not existing_notes.get("entries"):
            log.info("No notes found for this catalogue version")
        else:
            log.info(f"Notes for {catalogue_dir.name}:")
            log.info("")
            for entry in existing_notes.get("entries", []):
                timestamp = entry.get("timestamp", "Unknown time")
                note = entry.get("note", "")
                log.info(f"[{timestamp}]")
                log.info(f"  {note}")
                log.info("")
        return

    # Add new note
    try:
        # Initialize notes structure if needed
        if "entries" not in existing_notes:
            existing_notes = {"entries": []}

        # Create new note entry
        new_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "note": args.note,
        }

        # Append or replace
        if args.append:
            existing_notes["entries"].append(new_entry)
            log.info("Note appended")
        else:
            existing_notes["entries"] = [new_entry]
            log.info("Note added (replaced previous notes)")

        # Save notes
        with open(notes_path, "w", encoding="utf-8") as f:
            json.dump(existing_notes, f, ensure_ascii=False, indent=2)

        log.info(f"✅ Notes saved: {notes_path}")

        # Also update changelog.json if it exists
        changelog_path = catalogue_dir / "changelog.json"
        if changelog_path.exists():
            try:
                with open(changelog_path, "r", encoding="utf-8") as f:
                    changelog = json.load(f)

                # Update notes field in changelog
                changelog["notes"] = existing_notes

                with open(changelog_path, "w", encoding="utf-8") as f:
                    json.dump(changelog, f, ensure_ascii=False, indent=2)

                log.info(f"✅ Changelog updated with notes")
            except Exception as e:
                log.warning(f"Failed to update changelog with notes: {e}")

    except Exception as e:
        log.error(f"Failed to save note: {e}")
        import traceback

        traceback.print_exc()
