# Parallel Asset Catalogue Building

## Overview

The parallel catalogue building system enables processing of large numbers of FM bundles (e.g., 297+ bundles) within GitHub Actions' 2-hour timeout limit by splitting the work across multiple parallel jobs.

## Problem Statement

**Challenge**: Processing all FM bundles sequentially takes more than 2 hours, causing GitHub Actions workflows to timeout.

**Solution**: Split bundles into groups, process each group in parallel, then merge the results into a unified catalogue.

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
  --output bundle_groups
```

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

Manual workflow dispatch with inputs:
- `fm_version`: FM version (e.g., "fm2025")
- `bundle_prefix`: R2 prefix (e.g., "fm2025/StandaloneOSX")
- `num_groups`: Number of parallel groups (default: 10)

### Jobs

#### Job 1: Split
- Lists bundles from R2
- Splits into N groups
- Uploads group manifests as artifacts
- Outputs matrix for parallel jobs

#### Job 2: Extract (Matrix)
- Runs in parallel for each group (0 to N-1)
- Downloads bundles for assigned group
- Builds partial catalogue
- Uploads partial catalogue as artifact

**Matrix Strategy**:
```yaml
strategy:
  fail-fast: false
  matrix:
    group: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
```

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

### Choosing Number of Groups

**Factors to consider**:
1. **Total bundle count**: More bundles → more groups
2. **GitHub Actions limits**: Max concurrent jobs (usually 20)
3. **Bundle size variance**: Uneven bundle sizes may create stragglers
4. **Processing time**: Aim for ~10-15 minutes per group

**Recommendations**:
- **100 bundles**: 5-8 groups
- **200 bundles**: 8-12 groups
- **300 bundles**: 10-15 groups
- **500+ bundles**: 15-20 groups

### Expected Speedup

| Sequential | Parallel (10 groups) | Speedup |
|------------|----------------------|---------|
| 120 min    | ~15 min              | 8x      |
| 150 min    | ~18 min              | 8.3x    |
| 180 min    | ~21 min              | 8.6x    |

*Note: Speedup accounts for split/merge overhead (~2-3 min)*

## Limitations & Future Work

### Current Limitations

1. **Catalogue Builder Not Implemented**: Workflow includes placeholder for actual catalogue building logic
2. **R2 Upload Not Integrated**: Manual upload required after merge
3. **No Incremental Updates**: Full rebuild required each time
4. **Static Group Split**: Groups split by count, not by bundle size

### Future Enhancements

1. **Smart Splitting**: Split by estimated processing time, not just count
2. **Incremental Updates**: Only process changed bundles
3. **Dynamic Scaling**: Auto-adjust group count based on bundle count
4. **Progress Tracking**: Real-time progress visualization
5. **Cost Optimization**: Use spot instances for parallel jobs
6. **Bundle Filtering**: Option to process specific bundle patterns

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
