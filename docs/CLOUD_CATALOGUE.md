# Cloud Catalogue Building

Build FM asset catalogues automatically in the cloud using GitHub Actions and Cloudflare R2 storage.

## Architecture

```
┌─────────────────┐
│  Your Mac       │
│  FM Bundles     │
└────────┬────────┘
         │ Upload once
         ▼
┌─────────────────┐
│  R2 Bucket      │
│  fm-bundles     │ (Private)
│  ├─ fm2025/     │
│  └─ fm2026/     │
└────────┬────────┘
         │
         │ GitHub Actions downloads
         ▼
┌─────────────────┐
│ GitHub Actions  │
│ Ubuntu Runner   │
│ - Downloads     │
│ - Builds        │
│ - Uploads       │
└────────┬────────┘
         │
         │ Upload results
         ▼
┌─────────────────┐
│  R2 Bucket      │
│  fm-catalogue   │ (Public)
│  ├─ 2025.0.0/   │
│  └─ 2026.0.0/   │
└─────────────────┘
```

## Benefits

- ✅ **No local resources** - Runs on GitHub's servers
- ✅ **Runs while you sleep** - Can schedule weekly/monthly
- ✅ **Automatic deployment** - Results go straight to public R2
- ✅ **Version history** - All catalogues tracked in R2
- ✅ **Free** - GitHub Actions free for public repos
- ✅ **Reproducible** - Same environment every time

## Setup (One-Time)

### 1. Create Cloudflare R2 Buckets

Create two R2 buckets in your Cloudflare dashboard:

**Private bucket for source bundles:**
```
Name: fm-bundles
Public access: Disabled
```

**Public bucket for catalogues:**
```
Name: fm-asset-catalogue
Public access: Enabled
Custom domain: catalogue.your-domain.com (optional)
```

### 2. Create R2 API Token

In Cloudflare Dashboard → R2 → Manage R2 API Tokens:

```
Token name: fm-catalogue-builder
Permissions:
  - fm-bundles: Read
  - fm-asset-catalogue: Read & Write
```

Save the generated:
- Account ID
- Access Key ID
- Secret Access Key

### 3. Add Secrets to GitHub

In your GitHub repo → Settings → Secrets and variables → Actions:

Add these repository secrets:

```
R2_ACCOUNT_ID         = your-account-id
R2_ACCESS_KEY_ID      = your-access-key-id
R2_SECRET_ACCESS_KEY  = your-secret-access-key
R2_BUNDLES_BUCKET     = fm-bundles
R2_CATALOGUE_BUCKET   = fm-asset-catalogue
```

### 4. Install boto3 Locally

For the upload script:

```bash
pip install boto3
```

## Usage

### Step 1: Upload Bundles to R2 (One-Time Per FM Version)

Set environment variables:

```bash
export R2_ACCOUNT_ID="your-account-id"
export R2_ACCESS_KEY_ID="your-access-key"
export R2_SECRET_ACCESS_KEY="your-secret-key"
```

Upload bundles from your Mac:

```bash
python scripts/upload_bundles_to_r2.py \
  --bundles "~/Library/Application Support/Steam/steamapps/common/Football Manager 26/fm.app/Contents/Resources/Data/StreamingAssets/aa/StandaloneOSX" \
  --prefix "fm2025/StandaloneOSX"
```

This uploads all `.bundle` files to R2 once. You only need to do this when:
- New FM version is released
- Bundles are updated (game patches)

### Step 2: Trigger Catalogue Build

**Option A: Manual Trigger (Recommended)**

1. Go to GitHub → Actions → "Build FM Asset Catalogue"
2. Click "Run workflow"
3. Enter:
   - **FM Version**: `2025.0.0`
   - **Catalogue Version**: `1` (increment for rebuilds)
   - **Bundles Prefix**: `fm2025/StandaloneOSX`
4. Click "Run workflow"

**Option B: Automatic Schedule**

The workflow runs automatically every Monday at 2am UTC (configured in the workflow file).

### Step 3: Access Results

**Option 1: Download from GitHub**

After the workflow completes:
- Go to Actions → Click the workflow run
- Download the artifact `catalogue-2025.0.0-v1.zip`
- Extract locally for debugging

**Option 2: Access from R2**

Results are automatically uploaded to:

```
https://catalogue.your-domain.com/2025.0.0/v1/metadata.json
https://catalogue.your-domain.com/2025.0.0/v1/textures.json
https://catalogue.your-domain.com/2025.0.0/v1/thumbnails/textures/...
```

Or via R2 API:

```
s3://fm-asset-catalogue/2025.0.0/v1/
```

## Monitoring

### GitHub Actions

View logs in real-time:
1. Go to Actions tab
2. Click the running workflow
3. Click "build-catalogue" job
4. Expand steps to see detailed logs

### Workflow Status

The workflow will:
- ⏱️ Show estimated time remaining
- 📊 Display progress for each phase
- ✅ Mark successful completion
- ❌ Show errors if anything fails

### Artifacts

Every run saves artifacts for 7 days:
- Full catalogue JSON files
- All generated thumbnails
- Metadata and search indices

## Cost Estimate

**GitHub Actions:**
- Free for public repos
- Private repos: ~$0.008/minute (but you get 2000 free minutes/month)
- Estimated: 10-30 minutes per run = **$0**-$0.24/run

**Cloudflare R2:**
- Storage: $0.015/GB/month
- Egress: Free (unlike S3!)
- Operations: Very cheap ($4.50 per million requests)
- Estimated with 1000 bundles + catalogues: **~$1-5/month**

**Total: Essentially free** (~$5/month max)

## Troubleshooting

### "No bundles found"

Check that bundles were uploaded correctly:

```bash
# List bundles in R2
aws s3 ls s3://fm-bundles/fm2025/ \
  --endpoint-url=https://YOUR_ACCOUNT_ID.r2.cloudflarestorage.com
```

### "R2 credentials not found"

Verify GitHub secrets are set correctly in repository settings.

### "Catalogue empty"

Check the workflow logs for errors during extraction. Some bundles may not contain extractable assets.

### Timeout (2 hour limit)

If processing takes > 2 hours:
1. Split into multiple workflow runs (by bundle prefix)
2. Or use a cloud service with longer timeout

## Advanced: Custom Domain

To serve catalogues from your own domain:

1. In R2 bucket settings → Custom Domains
2. Add domain: `catalogue.yourdomain.com`
3. Add CNAME record in your DNS: `catalogue.yourdomain.com` → `[bucket-id].r2.cloudflarestorage.com`
4. Enable Public Access on bucket

Then access at:
```
https://catalogue.yourdomain.com/2025.0.0/v1/metadata.json
```

## Alternative: Cloud Run (Google Cloud)

If you prefer Google Cloud Platform:

```bash
# Build and deploy
gcloud run deploy fm-catalogue-builder \
  --source . \
  --memory 4Gi \
  --timeout 3600 \
  --set-env-vars R2_ACCOUNT_ID=$R2_ACCOUNT_ID
```

See `docs/CLOUD_RUN.md` for details.

## Comparison: Local vs Cloud

| Feature | Local (Docker) | Cloud (GitHub Actions) |
|---------|---------------|------------------------|
| Setup | Docker Desktop | GitHub Secrets |
| Resources | Your Mac | GitHub Servers |
| Speed | Depends on Mac | Consistent (fast) |
| Cost | Free (your power) | Free (public repos) |
| Availability | When Mac is on | 24/7 automated |
| Storage | Local disk | R2 (persistent) |
| Deployment | Manual | Automatic to R2 |

## Best Practice Workflow

**Initial Setup (Once):**
1. Create R2 buckets
2. Set up GitHub secrets
3. Upload bundles to R2

**Each FM Release:**
1. Upload new bundles: `python scripts/upload_bundles_to_r2.py`
2. Trigger workflow manually with new version
3. Catalogue auto-deploys to R2

**Regular Updates:**
- Schedule weekly runs to catch game patches
- Or trigger manually when needed

---

This gives you a fully automated asset catalogue pipeline that runs in the cloud! 🚀
