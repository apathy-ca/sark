# Engineer 4 - Docker Updates

## Task Assignment

Engineer 4 was assigned to update Docker configuration across the SARK repository.

## Docker Compose V2 Migration

### Change Required
Migrate from `docker-compose` (V1) to `docker compose` (V2)

**Old format (V1)**:
```bash
docker-compose up
docker-compose down
docker-compose build
```

**New format (V2)**:
```bash
docker compose up
docker compose down
docker compose build
```

### Files to Update

1. **Documentation files** - Any `.md` files with docker-compose commands
2. **Shell scripts** - Any `.sh` files using docker-compose
3. **Makefiles** - Any Makefile targets using docker-compose
4. **CI/CD configs** - GitHub Actions, GitLab CI, etc.
5. **README files** - Installation and deployment instructions

### Why This Matters

- Docker Compose V2 is the current standard
- V1 (docker-compose) is deprecated
- V2 is built into Docker CLI (no separate install needed)
- Better performance and features in V2

### Docker Files Review

Also review and update any Dockerfiles for:
- Best practices
- Security improvements
- Multi-stage builds where applicable
- Layer optimization

## Expected Changes

This should be a straightforward find-and-replace across the repository:
- Search: `docker-compose`
- Replace: `docker compose`

Plus any Dockerfile improvements Engineer 4 identifies.

## Impact on Omnibus Merge

These changes are:
- ✅ Safe (backward compatible in most cases)
- ✅ Non-breaking (Docker Compose V2 syntax is compatible)
- ✅ Isolated (shouldn't conflict with gateway integration work)

Should merge cleanly into the omnibus branch.

---

**Assigned by**: Human (Worker #7)
**Worker**: Engineer 4
**Branch**: `feat/gateway-audit`
**Status**: In progress
