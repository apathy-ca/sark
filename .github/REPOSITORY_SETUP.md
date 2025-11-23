# GitHub Repository Configuration

This document outlines required GitHub repository settings to eliminate CI/CD warnings.

## Required Settings

### 1. Enable Dependency Graph

**Issue:** "Dependency review is not supported on this repository"

**Fix:**
1. Go to: `https://github.com/apathy-ca/sark/settings/security_analysis`
2. Under "Dependency graph" → Click **Enable**
3. Under "Dependabot" → Enable "Dependabot alerts" (optional but recommended)
4. Under "Dependabot" → Enable "Dependabot security updates" (optional but recommended)

**Why:** Allows GitHub to scan dependencies for vulnerabilities and track dependency changes in PRs.

---

### 2. Repository Labels

**Issue:** "This PR has no labels. Please add appropriate labels."

**Fix:** Ensure these labels exist in the repository:

**Required Labels:**
- `enhancement` - New features or improvements
- `bug` - Bug fixes
- `documentation` - Documentation updates
- `chore` - Maintenance/tooling
- `release` - Release PRs
- `ci` - CI/CD changes
- `dependencies` - Dependency updates
- `security` - Security-related changes
- `performance` - Performance improvements
- `test` - Test updates

**Create Labels:**
1. Go to: `https://github.com/apathy-ca/sark/labels`
2. Click "New label"
3. Add each label with appropriate color:
   - `enhancement` - Green (#0E8A16)
   - `bug` - Red (#D73A4A)
   - `documentation` - Blue (#0075CA)
   - `chore` - Gray (#7057FF)
   - `release` - Purple (#5319E7)
   - `ci` - Orange (#F9D0C4)
   - `dependencies` - Teal (#0366D6)
   - `security` - Yellow (#FBCA04)
   - `performance` - Pink (#E99695)
   - `test` - Light Blue (#C5DEF5)

---

### 3. Branch Protection Rules (Recommended)

**For main branch:**
1. Go to: `https://github.com/apathy-ca/sark/settings/branches`
2. Click "Add rule" for `main`
3. Configure:
   - ✅ Require pull request reviews before merging
   - ✅ Require status checks to pass before merging
   - ✅ Require branches to be up to date before merging
   - ✅ Include administrators (optional)

---

### 4. PR Check Configuration

**Enable Required Checks:**
1. Go to: `https://github.com/apathy-ca/sark/settings/branches`
2. Edit `main` branch protection
3. Under "Require status checks to pass before merging":
   - Search and enable: `PR Metadata Checks`
   - Search and enable: `Dependency Review` (after enabling dependency graph)
   - Search and enable: `Ensure PR has labels`

---

## Quick Setup Checklist

- [ ] Enable Dependency Graph
- [ ] Enable Dependabot Alerts
- [ ] Create all required labels
- [ ] Configure branch protection for `main`
- [ ] Add required status checks
- [ ] Test with a sample PR

---

## Automated Label Assignment

For future automation, consider adding `.github/labeler.yml`:

```yaml
# Automatically label PRs based on changed files

documentation:
  - docs/**/*
  - '**/*.md'

test:
  - tests/**/*
  - '**/*test*.py'

ci:
  - .github/**/*
  - .gitlab-ci.yml
  - Dockerfile*
  - docker-compose*.yml

dependencies:
  - requirements*.txt
  - pyproject.toml
  - Pipfile*

chore:
  - scripts/**/*
  - tools/**/*
```

Then enable the "Labeler" GitHub Action.

---

## Notes

- These settings only affect future PRs, not historical ones
- Dependency graph requires repository to be public or have GitHub Advanced Security enabled for private repos
- Labels can be added to existing PRs manually after creation

**Current Status:** Repository needs these configurations applied to eliminate CI/CD warnings.
