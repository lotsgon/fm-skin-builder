# Parallel Asset Catalogue Building

## Overview

The parallel catalogue building system enables processing of large numbers of FM bundles (e.g., 297+ bundles) within GitHub Actions' 2-hour timeout limit by splitting the work across multiple parallel jobs.

## Problem Statement

**Challenge**: Processing all FM bundles sequentially takes more than 2 hours, causing GitHub Actions workflows to timeout.

**Key Issues**:
1. **Large bundle files**: 1.6GB newgen faces bundle alone takes significant time
2. **Duplicate processing**: Scale variants (_1x, _2x, _3x, _4x) processed separately then deduplicated
3. **Sequential bottleneck**: All bundles processed in a single job

**Solution**:
1. **Exclude problematic bundles** (newgen/regen faces)
2. **Keep scale variants together** to deduplicate before image processing
3. **Split into parallel groups** for faster processing
4. **Merge results** with deduplication

## Architecture

```
┌─────────────┐
│ 1. Split    │  List all bundles from R2 and divide into N groups
│   Bundles   │  Output: group_0.json, group_1.json, ..., group_N.json
└──────┬──────┘
       │
       ├──────┬──────┬──────┬──────┐
       ▼      ▼      ▼      ▼      ▼
┌──────────┐  ┌──────────┐  ┌──────────┐
│ 2. Extract│  │ 2. Extract│  │ 2. Extract│  Process each group in parallel
│  Group 0  │  │  Group 1  │  │  Group N  │  Output: partial catalogues
└─────┬────┘  └─────┬────┘  └─────┬────┘
      │             │             │
      └─────────────┴─────────────┘
                    │
              ┌─────▼──────┐
              │ 3. Merge   │  Combine all partials with deduplication
              │ Catalogues │  Output: unified catalogue
              └────────────┘
```

## Components

### 1. Bundle Splitting (`scripts/split_bundles.py`)

**Purpose**: List all bundles from R2 and split them into N groups for parallel processing.

**Usage**:
```bash
python scripts/split_bundles.py \
  --prefix "fm2025/StandaloneOSX" \
  --groups 10 \
  --exclude newgen regen \
  --output bundle_groups
```

**Features**:
- **Bundle exclusion**: Skip problematic bundles (default: newgen, regen)
- **Scale variant grouping**: Keep _1x, _2x, _3x, _4x together
- **Load balancing**: Distribute bundles evenly across groups

**Output**:
- `bundle_groups/group_0.json` - First group of bundles
- `bundle_groups/group_1.json` - Second group of bundles
- ...
- `bundle_groups/split_summary.json` - Metadata about the split

**Manifest Format**:
```json
{
  "group_id": 0,
  "bundle_count": 30,
  "bundles": [
    "fm2025/StandaloneOSX/bundle1.bundle",
    "fm2025/StandaloneOSX/bundle2.bundle",
    ...
  ]
}
```

**Grouping Example**:
```
ui-iconspriteatlases_assets_1x.bundle  ┐
ui-iconspriteatlases_assets_2x.bundle  ├─ Kept together in same group
ui-iconspriteatlases_assets_3x.bundle  │  for efficient deduplication
ui-iconspriteatlases_assets_4x.bundle  ┘
```

### 2. Group Download (`scripts/download_bundle_group.py`)

**Purpose**: Download only the bundles specified in a group manifest (used by parallel jobs).

**Usage**:
```bash
python scripts/download_bundle_group.py \
  --group-file bundle_groups/group_0.json \
  --output bundles
```

**Features**:
- Downloads only bundles in the specified group
- Preserves R2 directory structure
- Continues on individual bundle download errors
- Reports download success rate

### 3. Catalogue Merging (`scripts/merge_catalogues.py`)

**Purpose**: Combine partial catalogues from parallel jobs into a unified catalogue.

**Usage**:
```bash
python scripts/merge_catalogues.py \
  --partial-dirs catalogue_group_0/ catalogue_group_1/ catalogue_group_2/ \
  --output merged_catalogue
```

**Deduplication Strategy**:

| Asset Type      | Deduplication Key | Notes                                    |
|-----------------|-------------------|------------------------------------------|
| Sprites         | `content_hash`    | SHA256 hash ensures identical content    |
| Textures        | `content_hash`    | SHA256 hash ensures identical content    |
| CSS Variables   | `name`            | Unique by variable name                  |
| CSS Classes     | `name`            | Unique by class name                     |
| Fonts           | `name`            | Unique by font name                      |

**Merge Process**:
1. Load all partial catalogues
2. Combine metadata (bundle lists, asset counts)
3. Merge assets with deduplication
4. Consolidate thumbnails
5. Rebuild search index
6. Export unified catalogue

## GitHub Actions Workflow

### Workflow File

Location: `.github/workflows/build-catalogue.yml`

### Trigger

**Manual trigger only** (no scheduled runs)

Inputs:
- `fm_version`: FM version (e.g., "2025.0.0")
- `catalogue_version`: Catalogue version number (e.g., "1")
- `bundles_prefix`: R2 prefix (e.g., "fm2025/StandaloneOSX")
- `num_groups`: Number of parallel groups (default: 10, recommend: 10-15)
- `exclude_bundles`: Space-separated patterns to exclude (default: "newgen regen")

### Jobs

#### Job 1: Split
- Lists bundles from R2
- Splits into N groups
- Uploads group manifests as artifacts
- Outputs matrix for parallel jobs

#### Job 2: Extract (Matrix)
- Runs in parallel for each group (0 to N-1)
- Downloads bundles for assigned group
- Builds partial catalogue (with intra-group deduplication)
- Uploads partial catalogue as artifact
- **Timeout**: 60 minutes per group (adjust based on testing)

**Matrix Strategy**:
```yaml
strategy:
  fail-fast: false  # Don't cancel other groups if one fails
  matrix:
    group: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
```

**Note**: Scale variants (\_1x, \_2x, etc.) are kept in the same group for efficient deduplication before image processing.

#### Job 3: Merge
- Downloads all partial catalogue artifacts
- Merges into unified catalogue
- Uploads to R2 (when implemented)
- Stores merged catalogue as artifact

### Environment Variables

Required Secrets:
- `R2_ACCOUNT_ID`: Cloudflare account ID
- `R2_ACCESS_KEY`: R2 Access Key ID
- `R2_SECRET_ACCESS_KEY`: R2 Secret Access Key

Required Variables:
- `R2_BUNDLES_BUCKET`: Bundles bucket name (e.g., "fm-skin-builder-bundles")
- `R2_CATALOGUE_BUCKET`: Catalogue bucket name (e.g., "fm-skin-builder-asset-catalogue")

### Usage Example

```bash
# In GitHub UI:
Actions → Build Asset Catalogue → Run workflow

# Fill in:
fm_version: fm2025
bundle_prefix: fm2025/StandaloneOSX
num_groups: 10
```

## Performance Optimization

### Key Optimizations

1. **Bundle Exclusion** 🚫
   - Excludes newgen/regen face bundles by default (1.6GB+)
   - Can be customized via `--exclude` parameter
   - Reduces total processing time significantly

2. **Scale Variant Grouping** 🎯
   - Keeps `bundle_1x`, `bundle_2x`, `bundle_3x`, `bundle_4x` together
   - Enables deduplication **before** image processing
   - Prevents processing the same image 4 times
   - **Major time saver** for image-heavy bundles

3. **Load Balancing** ⚖️
   - Uses bin-packing algorithm to distribute bundles
   - Aims for equal bundle counts per group
   - Minimizes stragglers (groups that finish late)

### Choosing Number of Groups

**Factors to consider**:
1. **Total bundle count**: More bundles → more groups
2. **GitHub Actions limits**: Max 20 concurrent jobs (free tier)
3. **Image processing time**: Dominates the workload
4. **Processing time target**: Aim for 30-60 minutes per group

**Recommendations**:
- **~297 bundles (excluding newgen)**: Start with **10 groups**
- **If groups timeout**: Increase to **12-15 groups**
- **If groups finish quickly**: Can reduce to 8 groups

**GitHub Actions Concurrency**:
- Free tier: 20 concurrent jobs
- Pro: 40 concurrent jobs
- **Recommendation**: Stay under 15 groups to leave buffer

### Expected Performance

**Without optimizations** (sequential):
- 297 bundles with all scale variants
- Processing same images 4 times
- **Result**: 120-180+ minutes → **TIMEOUT** ❌

**With optimizations** (parallel):
- ~270 bundles (newgen excluded)
- Scale variants grouped for deduplication
- 10 parallel groups
- **Result**: 30-60 minutes per group = **~1 hour total** ✅

**Performance breakdown per group**:
- Download bundles: ~5 min
- Extract & process: ~25-50 min (depends on bundle complexity)
- Upload results: ~2 min

*Note: Times vary based on bundle contents. Image-heavy bundles take longer.*

## Limitations & Future Work

### Current Limitations

1. **Catalogue Builder Not Implemented**: Workflow includes placeholder for actual catalogue building logic
2. **R2 Upload Not Integrated**: Manual upload required after merge
3. **No Incremental Updates**: Full rebuild required each time
4. **Static Group Split**: Groups split by count, not by bundle size

### Future Enhancements

1. **Early Deduplication in Catalogue Builder** 🎯
   - Deduplicate images **during** extraction, not just at merge
   - Skip processing of already-seen image hashes
   - Would eliminate the 4x redundant processing entirely
   - **Highest priority optimization**

2. **Smart Splitting by Size**:
   - Split by estimated processing time, not just bundle count
   - Factor in bundle file sizes
   - Better load balancing for mixed bundle sizes

3. **Incremental Updates**:
   - Only process changed bundles
   - Compare with previous catalogue
   - Skip unchanged scale variants

4. **Dynamic Scaling**:
   - Auto-adjust group count based on bundle count
   - Detect available GitHub Actions concurrency

5. **Progress Tracking**:
   - Real-time progress visualization
   - Estimated time remaining per group

6. **Bundle Filtering**:
   - Process only specific bundle patterns
   - Include/exclude by bundle type (UI, textures, etc.)

## Testing Locally

### Test Split
```bash
# Set R2 credentials
export R2_ACCOUNT_ID="your-account-id"
export R2_ACCESS_KEY_ID="your-access-key"
export R2_SECRET_ACCESS_KEY="your-secret-key"
export R2_BUNDLES_BUCKET="fm-skin-builder-bundles"

# Split bundles
python scripts/split_bundles.py \
  --prefix "fm2025/StandaloneOSX" \
  --groups 5 \
  --output test_groups

# Check results
cat test_groups/split_summary.json
```

### Test Download
```bash
# Download one group
python scripts/download_bundle_group.py \
  --group-file test_groups/group_0.json \
  --output test_bundles

# Verify downloads
ls -lh test_bundles/
```

### Test Merge
```bash
# Create mock partial catalogues
mkdir -p partial_0 partial_1
echo '{"name": "sprite1", "content_hash": "abc123"}' > partial_0/sprites.json
echo '{"name": "sprite2", "content_hash": "def456"}' > partial_1/sprites.json

# Merge
python scripts/merge_catalogues.py \
  --partial-dirs partial_0 partial_1 \
  --output test_merged

# Check results
cat test_merged/sprites.json
```

## Troubleshooting

### Split Job Fails

**Error**: "No bundle files found!"

**Causes**:
- Incorrect R2 credentials
- Wrong bundle prefix
- Empty R2 bucket

**Solutions**:
1. Check R2 credentials in GitHub Secrets
2. Verify bundle prefix matches R2 structure
3. Confirm bundles exist: `aws s3 ls s3://bucket/prefix/ --endpoint-url=...`

### Extract Job Timeout

**Error**: Job exceeds 2-hour limit

**Causes**:
- Too many bundles per group
- Complex bundles taking long to process

**Solutions**:
1. Increase `num_groups` to split work further
2. Optimize catalogue extraction code
3. Use faster GitHub runner types

### Merge Job Out of Memory

**Error**: "MemoryError" during merge

**Causes**:
- Too many large thumbnails
- Large search index

**Solutions**:
1. Reduce thumbnail size/quality
2. Process assets in batches during merge
3. Use runners with more memory

### Duplicate Assets in Output

**Error**: Same asset appears multiple times

**Causes**:
- Deduplication logic not working
- Hash collision (extremely rare)

**Solutions**:
1. Check merge script deduplication logic
2. Verify `content_hash` is consistent across groups
3. Review asset equality comparison

## References

- [ASSET_CATALOGUE_PLAN.md](./ASSET_CATALOGUE_PLAN.md) - Catalogue system design
- [GitHub Actions Matrix Strategy](https://docs.github.com/en/actions/using-jobs/using-a-matrix-for-your-jobs)
- [Cloudflare R2 Documentation](https://developers.cloudflare.com/r2/)
- [boto3 S3 Client Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html)

## Questions?

For issues or questions about the parallel catalogue system:
1. Check existing GitHub Issues
2. Create a new issue with:
   - Workflow run link
   - Error messages
   - Group manifest files (if relevant)
