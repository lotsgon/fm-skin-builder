"""Import UXML files and patch Unity bundles"""

from __future__ import annotations
from pathlib import Path
import shutil
import UnityPy
from ...core.uxml.uxml_importer import UXMLImporter
from ...core.logger import get_logger


log = get_logger(__name__)


def run(args) -> None:
    """
    Import UXML files and patch Unity bundles.

    Args:
        args: Command-line arguments with:
            - bundle: Path to bundle file to patch
            - uxml: Directory containing UXML files
            - out: Output path for patched bundle
            - backup: Create .bak backup of original
            - dry_run: Preview without writing files
    """
    bundle_path = Path(args.bundle).resolve()
    uxml_dir = Path(args.uxml).resolve()
    out_path = Path(args.out).resolve()

    # Validation
    if not bundle_path.exists():
        log.error(f"Bundle not found: {bundle_path}")
        return

    if not uxml_dir.exists() or not uxml_dir.is_dir():
        log.error(f"UXML directory not found: {uxml_dir}")
        return

    # Find UXML files
    uxml_files = list(uxml_dir.glob("*.uxml"))
    if not uxml_files:
        log.error(f"No .uxml files found in {uxml_dir}")
        return

    log.info(f"Found {len(uxml_files)} UXML file(s) in {uxml_dir}")

    # Backup original bundle
    if args.backup and not args.dry_run and bundle_path != out_path:
        backup_path = bundle_path.with_suffix(bundle_path.suffix + ".bak")
        if not backup_path.exists():
            log.info(f"Creating backup: {backup_path}")
            shutil.copy2(bundle_path, backup_path)

    # Load bundle
    log.info(f"Loading bundle: {bundle_path}")
    try:
        env = UnityPy.load(str(bundle_path))
    except Exception as e:
        log.error(f"Failed to load bundle: {e}")
        return

    importer = UXMLImporter()
    modified_count = 0
    skipped_count = 0

    # Build lookup of available UXML files
    uxml_lookup = {f.stem: f for f in uxml_files}

    # Find and update VisualTreeAssets
    for obj in env.objects:
        if obj.type.name == "MonoBehaviour":
            try:
                data = obj.read()

                # Check if this is a VisualTreeAsset by looking for VTA-specific fields
                # (m_ClassName may not be set in Unity 2021+)
                is_vta = (
                    hasattr(data, "m_VisualElementAssets")
                    or hasattr(data, "m_TemplateAssets")
                    or hasattr(data, "m_UxmlObjectEntries")
                )

                if is_vta:
                    asset_name = getattr(data, "m_Name", f"VTA_{obj.path_id}")
                    if not asset_name:
                        asset_name = f"VTA_{obj.path_id}"

                    # Check if we have a UXML file for this asset
                    uxml_file = uxml_lookup.get(asset_name)

                    if uxml_file:
                        if args.dry_run:
                            log.info(f"  [DRY-RUN] Would import: {asset_name}")
                            modified_count += 1
                        else:
                            log.info(f"  Importing: {asset_name}")

                            try:
                                # Import UXML
                                doc = importer.import_uxml(uxml_file)

                                # Convert to VTA structure
                                vta_structure = importer.build_visual_tree_asset(doc)

                                # Update object data
                                for key, value in vta_structure.items():
                                    setattr(data, key, value)

                                # Save changes
                                obj.save_typetree(data)
                                modified_count += 1

                            except Exception as e:
                                log.error(f"    Failed to import {asset_name}: {e}")
                                skipped_count += 1
                    else:
                        # VTA exists but no UXML override provided
                        pass

            except Exception as e:
                log.warning(f"  Failed to process object {obj.path_id}: {e}")
                continue

    # Save modified bundle
    if not args.dry_run and modified_count > 0:
        log.info(f"\nSaving patched bundle to: {out_path}")
        out_path.parent.mkdir(exist_ok=True, parents=True)

        with open(out_path, "wb") as f:
            f.write(env.file.save())

    # Summary
    log.info("\n=== Import Summary ===")
    if args.dry_run:
        log.info(f"[DRY-RUN] Would modify {modified_count} VTA asset(s)")
    else:
        log.info(f"Modified {modified_count} VTA asset(s)")

    if skipped_count > 0:
        log.warning(f"Skipped {skipped_count} asset(s) due to errors")

    if modified_count == 0:
        log.warning("No UXML files were imported (no matching VTA assets found)")
    elif not args.dry_run:
        log.info(f"✅ Bundle saved: {out_path}")
