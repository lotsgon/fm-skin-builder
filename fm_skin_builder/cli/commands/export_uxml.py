"""Export UXML files from Unity bundles"""
from __future__ import annotations
from pathlib import Path
import UnityPy
from ...core.uxml.uxml_exporter import UXMLExporter
from ...core.logger import get_logger


log = get_logger(__name__)


def run(args) -> None:
    """
    Export UXML files from Unity bundles.

    Args:
        args: Command-line arguments with:
            - bundle: Path to bundle file or directory
            - out: Output directory for UXML files
            - filter: Optional comma-separated list of asset names to export
            - dry_run: Preview without writing files
    """
    bundle_path = Path(args.bundle).resolve()
    out_dir = Path(args.out).resolve()

    # Parse filter if provided
    asset_filter = None
    if args.filter:
        asset_filter = set(name.strip() for name in args.filter.split(","))
        log.info(f"Filter: {', '.join(asset_filter)}")

    # Handle directory of bundles
    if bundle_path.is_dir():
        log.info(f"Scanning directory: {bundle_path}")
        bundle_files = list(bundle_path.glob("*.unity3d"))
        if not bundle_files:
            log.error(f"No .unity3d files found in {bundle_path}")
            return
        log.info(f"Found {len(bundle_files)} bundle(s)")
    else:
        bundle_files = [bundle_path]

    total_exported = 0
    exporter = UXMLExporter()

    # Process each bundle
    for bundle_file in bundle_files:
        if not bundle_file.exists():
            log.warning(f"Bundle not found: {bundle_file}")
            continue

        log.info(f"\nProcessing bundle: {bundle_file.name}")

        try:
            env = UnityPy.load(str(bundle_file))
        except Exception as e:
            log.error(f"Failed to load bundle {bundle_file.name}: {e}")
            continue

        bundle_exported = 0

        # Find all VisualTreeAssets
        for obj in env.objects:
            if obj.type.name == "MonoBehaviour":
                try:
                    data = obj.read()
                    type_name = getattr(data, "m_ClassName", None)

                    if type_name == "UnityEngine.UIElements.VisualTreeAsset":
                        asset_name = getattr(data, "m_Name", f"VTA_{obj.path_id}")
                        if not asset_name:
                            asset_name = f"VTA_{obj.path_id}"

                        # Apply filter if specified
                        if asset_filter and asset_name not in asset_filter:
                            continue

                        # Export to UXML
                        output_file = out_dir / f"{asset_name}.uxml"

                        if args.dry_run:
                            log.info(f"  [DRY-RUN] Would export: {asset_name}")
                        else:
                            log.info(f"  Exporting: {asset_name}")
                            out_dir.mkdir(exist_ok=True, parents=True)

                            try:
                                doc = exporter.export_visual_tree_asset(
                                    data, asset_name=asset_name
                                )
                                exporter.write_uxml(doc, output_file)
                                bundle_exported += 1
                                total_exported += 1
                            except Exception as e:
                                log.error(f"    Failed to export {asset_name}: {e}")

                except Exception as e:
                    log.warning(f"  Failed to read object {obj.path_id}: {e}")
                    continue

        if bundle_exported > 0 or args.dry_run:
            log.info(f"  Exported {bundle_exported} UXML file(s) from {bundle_file.name}")

    # Summary
    log.info("\n=== Export Summary ===")
    if args.dry_run:
        log.info(f"[DRY-RUN] Would export {total_exported} UXML file(s)")
    else:
        log.info(f"Exported {total_exported} UXML file(s) to {out_dir}")

    if total_exported == 0 and not args.dry_run:
        log.warning("No VisualTreeAssets found or exported")
