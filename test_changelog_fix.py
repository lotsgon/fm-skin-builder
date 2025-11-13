#!/usr/bin/env python3
"""
Test the changelog application logic with mock data.
This ensures the fix works before running expensive GitHub Actions.
"""

import json
from pathlib import Path
import tempfile
import shutil

def test_change_tracking():
    """Test that change tracking correctly updates metadata."""

    # Create temp directories
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        prev_dir = tmpdir / "prev"
        curr_dir = tmpdir / "curr"
        prev_dir.mkdir()
        curr_dir.mkdir()

        # Mock previous version CSS variables
        prev_css_vars = [
            {
                "name": "--scroller-size",
                "first_seen": "2026.0.4",
                "last_seen": "2026.0.4",
                "change_status": None,
                "changed_in_version": None
            },
            {
                "name": "--existing-var",
                "first_seen": "2026.0.3",
                "last_seen": "2026.0.4",
                "change_status": None,
                "changed_in_version": None
            }
        ]

        # Mock current version CSS variables (before fixing)
        curr_css_vars = [
            {
                "name": "--scroller-size",
                "first_seen": "2026.0.5-beta",  # WRONG! Should preserve 2026.0.4
                "last_seen": "2026.0.5-beta",
                "change_status": None,
                "changed_in_version": None
            },
            {
                "name": "--existing-var",
                "first_seen": "2026.0.5-beta",  # WRONG! Should preserve 2026.0.3
                "last_seen": "2026.0.5-beta",
                "change_status": None,
                "changed_in_version": None,
                "values": "modified"
            },
            {
                "name": "--new-var",
                "first_seen": "2026.0.5-beta",
                "last_seen": "2026.0.5-beta",
                "change_status": None,
                "changed_in_version": None
            }
        ]

        # Mock changelog (uses SINGULAR keys!)
        changelog = {
            "from_version": "2026.0.4",
            "to_version": "2026.0.5-beta",
            "changes_by_type": {
                "css_variable": {  # SINGULAR!
                    "added": [
                        {"name": "--new-var"}
                    ],
                    "modified": [
                        {"name": "--existing-var", "old_values": "original"}
                    ],
                    "removed": []
                }
            }
        }

        # Save files
        with open(prev_dir / "css-variables.json", "w") as f:
            json.dump(prev_css_vars, f)

        with open(curr_dir / "css-variables.json", "w") as f:
            json.dump(curr_css_vars, f)

        with open(curr_dir / "changelog-summary.json", "w") as f:
            json.dump(changelog, f)

        # Import and run the fixed function
        import sys
        sys.path.insert(0, str(Path(__file__).parent))
        from scripts.generate_post_merge_changelog import apply_change_tracking

        # Apply the fix
        apply_change_tracking(curr_dir, prev_dir, changelog)

        # Load results
        with open(curr_dir / "css-variables.json") as f:
            result = json.load(f)

        # Verify results
        results_by_name = {v["name"]: v for v in result}

        # Check --scroller-size (unchanged)
        scroller = results_by_name["--scroller-size"]
        assert scroller["first_seen"] == "2026.0.4", f"first_seen should be 2026.0.4, got {scroller['first_seen']}"
        assert scroller["last_seen"] == "2026.0.5-beta", f"last_seen should be 2026.0.5-beta, got {scroller['last_seen']}"
        assert scroller["change_status"] == "unchanged", f"change_status should be unchanged, got {scroller['change_status']}"

        # Check --existing-var (modified)
        existing = results_by_name["--existing-var"]
        assert existing["first_seen"] == "2026.0.3", f"first_seen should be 2026.0.3, got {existing['first_seen']}"
        assert existing["last_seen"] == "2026.0.5-beta", f"last_seen should be 2026.0.5-beta, got {existing['last_seen']}"
        assert existing["change_status"] == "modified", f"change_status should be modified, got {existing['change_status']}"
        assert existing["changed_in_version"] == "2026.0.5-beta", f"changed_in_version should be 2026.0.5-beta, got {existing['changed_in_version']}"

        # Check --new-var (added)
        new_var = results_by_name["--new-var"]
        assert new_var["first_seen"] == "2026.0.5-beta", f"first_seen should be 2026.0.5-beta, got {new_var['first_seen']}"
        assert new_var["last_seen"] == "2026.0.5-beta", f"last_seen should be 2026.0.5-beta, got {new_var['last_seen']}"
        assert new_var["change_status"] == "new", f"change_status should be new, got {new_var['change_status']}"

        print("✅ All tests passed!")
        return True

if __name__ == "__main__":
    try:
        test_change_tracking()
    except AssertionError as e:
        print(f"❌ Test failed: {e}")
        exit(1)
    except Exception as e:
        print(f"❌ Test error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
