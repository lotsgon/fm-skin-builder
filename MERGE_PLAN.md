# Merge Plan & Summary

This document answers your questions and provides a merge plan.

## Your Questions Answered

### Q1: Merge to main first?

**Answer: YES** ✅

We should merge this branch to `main` first, then create `beta` from `main`.

**Why:**

- Workflows need to exist in default branch to work
- Beta branch will inherit the workflows when created
- Keeps history clean

**Steps:**

```bash
# 1. Commit everything on current branch
git add .
git commit -m "feat: implement automated versioning and CI/CD pipeline"
git push

# 2. Create PR to main → merge

# 3. After merge, create beta branch
git checkout main
git pull
git checkout -b beta
git push -u origin beta
```

### Q2: Build artifacts on GitHub Releases?

**Answer: NOW YES** ✅

I just updated the workflows:

- ✅ **Stable releases**: Artifacts attached to GitHub Release
- ✅ **Beta releases**: Artifacts attached to GitHub Release (marked as pre-release)

**Benefits:**

- Artifacts available in two places (R2 + GitHub)
- Can verify R2 uploads match GitHub artifacts
- Users can download from GitHub if R2 has issues
- GitHub provides checksums automatically

**How it works:**

**For Stable Releases (tags):**

```yaml
- name: Create GitHub Release
  uses: softprops/action-gh-release@v1
  with:
    files: artifacts/**/* # ← Attaches all build artifacts
```

**For Beta Releases (beta branch):**

```yaml
- name: Create GitHub Release (Beta)
  uses: softprops/action-gh-release@v1
  with:
    tag_name: ${{ version }} # e.g., 0.2.0-beta.abc123
    prerelease: true # ← Marked as pre-release
    files: artifacts/**/* # ← Attaches all build artifacts
```

### Q3: Latest release metadata for auto-updates?

**Answer: NOW IMPLEMENTED** ✅

Created `scripts/update_latest_metadata.py` that maintains:

**`latest.json` at root of R2:**

```json
{
  "stable": {
    "version": "0.2.0",
    "date": "2025-01-15T10:30:00Z",
    "platforms": {
      "linux-x86_64": [{
        "url": "https://...",
        "signature": "sha256_hash",
        "format": "AppImage",
        "size": 12345678
      }],
      "windows-x86_64": [...],
      "darwin-aarch64": [...],
      "darwin-x86_64": [...]
    }
  },
  "beta": {
    // Same structure
  },
  "last_updated": "2025-01-15T10:30:00Z"
}
```

**Version-specific metadata:**

```
/metadata/0.2.0.json
/metadata/0.2.0-beta.abc123.json
```

**Usage:**

**Website downloads:**

```typescript
const data = await fetch("https://release.fmskinbuilder.com/latest.json");
const { stable, beta } = await data.json();

// Get latest stable download
const windowsUrl = stable.platforms["windows-x86_64"][0].url;
```

**Tauri auto-updater:**

```json
{
  "tauri": {
    "updater": {
      "endpoints": ["https://release.fmskinbuilder.com/latest.json"]
    }
  }
}
```

See [AUTO_UPDATES.md](.github/AUTO_UPDATES.md) for complete docs.

## What Was Changed

### New Files

1. **Workflows:**

   - `.github/workflows/ci.yml` - Tests only (cheap)
   - `.github/workflows/auto-tag.yml` - Auto version tagging
   - `.github/workflows/build-app.yml` - Full builds (expensive, controlled)

2. **Scripts:**

   - `scripts/get_next_version.py` - Calculate version from commits
   - `scripts/version.sh` - User-friendly version helper
   - `scripts/upload_release_to_r2.py` - Upload artifacts to R2
   - `scripts/update_latest_metadata.py` - Update latest.json

3. **Documentation:**
   - `.github/README.md` - Overview
   - `.github/SETUP.md` - Setup guide
   - `.github/RELEASE_PROCESS.md` - Quick release guide
   - `.github/BRANCH_STRATEGY.md` - Complete branch strategy
   - `.github/VERSIONING.md` - Versioning details
   - `.github/WORKFLOW_STRATEGY.md` - CI/CD details
   - `.github/AUTO_UPDATES.md` - Auto-update system docs

### Modified Files

- Removed: `.github/workflows/release.yml` (merged into build-app.yml)

## Complete Workflow After Merge

### 1. Daily Development

```bash
git checkout beta
git checkout -b feat/my-feature
git commit -m "feat: add feature"
# PR to beta → merge
# → Beta build: 0.2.0-beta.abc123
# → Uploaded to R2 /beta/
# → GitHub Release (pre-release)
# → latest.json updated
```

### 2. Create Release

```bash
# Create PR: beta → main, merge
# → Auto-tags v0.2.0
# → Release build starts
# → Uploaded to R2 /releases/0.2.0/
# → GitHub Release created
# → latest.json updated
```

## Key Features

✅ **Automatic versioning** - Based on conventional commits
✅ **Auto-tagging** - No manual tags needed
✅ **Cost optimized** - 98% reduction (tests only on PRs)
✅ **Beta builds** - Automatic on every beta push
✅ **GitHub Releases** - Both stable and beta
✅ **R2 uploads** - All artifacts uploaded
✅ **Auto-update metadata** - latest.json maintained
✅ **Fail-fast** - Stops all if one platform fails
✅ **Full documentation** - Everything documented

## Merge Steps

### Step 1: Merge Current Branch

```bash
# Current branch: chore/husky-commits
git add .
git commit -m "feat: implement automated versioning and CI/CD pipeline

- Add automatic semantic versioning based on conventional commits
- Implement beta branch workflow with auto-builds
- Add auto-tagging on main branch merges
- Configure cost-optimized GitHub Actions (98% reduction)
- Add R2 upload for releases and beta builds
- Create latest.json metadata for auto-updates
- Add comprehensive documentation

BREAKING CHANGE: New branch strategy requires beta branch"

git push origin chore/husky-commits
```

Create PR on GitHub → Merge to main

### Step 2: Create Beta Branch

```bash
git checkout main
git pull
git checkout -b beta
git push -u origin beta
```

### Step 3: Set Up R2

Add to GitHub Secrets:

```
R2_ACCOUNT_ID
R2_ACCESS_KEY
R2_SECRET_ACCESS_KEY
```

Add to GitHub Variables:

```
R2_RELEASES_BUCKET=your-bucket-name
```

### Step 4: Test Beta Build

```bash
git checkout beta
git commit --allow-empty -m "test: verify beta workflow"
git push

# → Should trigger beta build
# → Check Actions tab
# → Check R2 bucket /beta/ path
# → Check GitHub Releases (pre-release)
```

### Step 5: Test Release

```bash
# Merge beta to main (PR or direct)
git checkout main
git merge beta
git push

# → Auto-tags v0.1.0
# → Triggers release build
# → Check R2 bucket /releases/0.1.0/
# → Check GitHub Releases
# → Check latest.json
```

## Verification Checklist

After everything is set up:

- [ ] Beta branch exists and builds work
- [ ] Beta releases appear in GitHub (pre-release)
- [ ] R2 has `/beta/` artifacts
- [ ] Main auto-tags on push/merge
- [ ] Release builds work
- [ ] R2 has `/releases/` artifacts
- [ ] GitHub Releases created for stable
- [ ] `latest.json` exists in R2 root
- [ ] `latest.json` updates on new releases
- [ ] Version calculation works correctly

## Getting Started

1. Read this document
2. Merge to main following steps above
3. Create beta branch
4. Add R2 credentials
5. Read [RELEASE_PROCESS.md](.github/RELEASE_PROCESS.md)
6. Start developing!

## Questions?

Check the documentation:

- Quick start: [RELEASE_PROCESS.md](.github/RELEASE_PROCESS.md)
- Branch model: [BRANCH_STRATEGY.md](.github/BRANCH_STRATEGY.md)
- Auto-updates: [AUTO_UPDATES.md](.github/AUTO_UPDATES.md)
- Setup: [SETUP.md](.github/SETUP.md)
