# Docker Compose Standards

**Version:** 1.0
**Effective Date:** November 28, 2024
**Applies To:** All Engineers
**Status:** MANDATORY

---

## Critical Rules

### 1. Use `docker compose` NOT `docker-compose`

❌ **WRONG**:
```bash
docker-compose up -d
docker-compose ps
docker-compose down
```

✅ **CORRECT**:
```bash
docker compose up -d
docker compose ps
docker compose down
```

**Rationale**: `docker-compose` (hyphenated) is the legacy standalone tool. `docker compose` (space) is the modern Docker CLI plugin and is the official standard as of Docker Compose V2.

### 2. DO NOT Include Version Number in Compose Files

❌ **WRONG**:
```yaml
version: '3.8'

services:
  app:
    image: myapp:latest
```

✅ **CORRECT**:
```yaml
services:
  app:
    image: myapp:latest
```

**Rationale**: As of Docker Compose specification, the `version` field is obsolete and ignored. Modern Docker Compose automatically uses the latest compose file format.

---

## Standards

### Compose File Format

```yaml
# NO version field

services:
  service-name:
    image: image:tag
    container_name: container-name
    restart: unless-stopped
    ports:
      - "host:container"
    environment:
      - VAR=value
    volumes:
      - ./local:/container
    networks:
      - network-name
    depends_on:
      - other-service
    healthcheck:
      test: ["CMD", "command"]
      interval: 30s
      timeout: 10s
      retries: 3

networks:
  network-name:
    name: explicit-network-name
    driver: bridge

volumes:
  volume-name:
    name: explicit-volume-name
```

### Command Line Usage

**Start services**:
```bash
docker compose up -d
```

**View logs**:
```bash
docker compose logs -f [service]
```

**Check status**:
```bash
docker compose ps
```

**Stop services**:
```bash
docker compose down
```

**Rebuild and restart**:
```bash
docker compose up -d --build
```

**Execute command in service**:
```bash
docker compose exec service-name command
```

**View service logs**:
```bash
docker compose logs -f service-name
```

### Multiple Compose Files

When using multiple compose files:

```bash
docker compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d
```

### Environment-Specific Files

```bash
# Development
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# Production
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

---

## Validation

### Pre-Commit Checklist

Before committing any `docker-compose*.yml` file:

- [ ] File does NOT contain `version:` field
- [ ] All documentation uses `docker compose` (with space)
- [ ] All scripts use `docker compose` (with space)
- [ ] Services have explicit `container_name`
- [ ] Networks have explicit `name`
- [ ] Volumes have explicit `name`
- [ ] Health checks defined for critical services
- [ ] Restart policies configured (`unless-stopped` or `always`)

### Automated Checks

Run this command to validate compose files:

```bash
# Validate syntax
docker compose -f docker-compose.yml config

# Check for version field (should be removed)
grep -n "^version:" docker-compose*.yml && echo "ERROR: Remove version field" || echo "OK"
```

---

## Migration Guide

### For Existing Files

1. **Remove version field**:
   ```bash
   # Find all compose files with version
   find . -name "docker-compose*.yml" -exec grep -l "^version:" {} \;

   # Remove version line
   sed -i '/^version:/d' docker-compose*.yml
   ```

2. **Update documentation**:
   ```bash
   # Find all markdown files with docker compose
   find . -name "*.md" -exec grep -l "docker compose" {} \;

   # Replace with docker compose
   find . -name "*.md" -exec sed -i 's/docker compose/docker compose/g' {} \;
   ```

3. **Update scripts**:
   ```bash
   # Find all scripts with docker compose
   find . -type f -name "*.sh" -exec grep -l "docker compose" {} \;

   # Replace with docker compose
   find . -type f -name "*.sh" -exec sed -i 's/docker compose/docker compose/g' {} \;
   ```

---

## CI/CD Integration

### GitHub Actions

```yaml
- name: Start services
  run: docker compose up -d

- name: Run tests
  run: docker compose exec -T app pytest

- name: Tear down
  run: docker compose down
```

### GitLab CI

```yaml
script:
  - docker compose up -d
  - docker compose exec -T app pytest
  - docker compose down
```

---

## Enforcement

### Code Review Requirements

All pull requests must:

1. Use `docker compose` (not `docker-compose`) in all files
2. NOT include `version:` field in compose files
3. Pass automated validation checks

### Automated Validation

Add this to `.github/workflows/validate-docker-compose.yml`:

```yaml
name: Validate Docker Compose

on: [pull_request]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Check for version field
        run: |
          if grep -r "^version:" docker-compose*.yml; then
            echo "ERROR: docker compose files must not contain version field"
            exit 1
          fi

      - name: Check for docker-compose command
        run: |
          if grep -r "docker-compose" docs/ scripts/; then
            echo "ERROR: Use 'docker compose' not 'docker-compose'"
            exit 1
          fi

      - name: Validate compose files
        run: |
          for file in docker-compose*.yml; do
            docker compose -f "$file" config > /dev/null
          done
```

---

## Common Mistakes

### ❌ Mistake 1: Using hyphenated command
```bash
docker-compose up -d
```
**Fix**: Use space instead of hyphen
```bash
docker compose up -d
```

### ❌ Mistake 2: Including version in compose file
```yaml
version: '3.8'
services:
  app:
    image: myapp
```
**Fix**: Remove version field entirely
```yaml
services:
  app:
    image: myapp
```

### ❌ Mistake 3: Old-style documentation
```markdown
Run `docker-compose up -d` to start services
```
**Fix**: Update to modern syntax
```markdown
Run `docker compose up -d` to start services
```

---

## References

- [Docker Compose Specification](https://docs.docker.com/compose/compose-file/)
- [Docker Compose V2](https://docs.docker.com/compose/cli-command/)
- [Compose File Version Obsolescence](https://docs.docker.com/compose/compose-file/04-version-and-name/)

---

## Exceptions

**None**. This standard applies to ALL docker compose files in the repository with no exceptions.

---

**Approved By:** Engineering Leadership
**Effective Immediately**
**Non-Compliance**: Code review rejection

---

## Quick Reference Card

```
✅ DO:
  - docker compose up -d
  - docker compose ps
  - docker compose logs
  - NO version field in YAML

❌ DON'T:
  - docker-compose (with hyphen)
  - version: '3.8' in YAML
  - Mix old and new syntax
```

---

**Last Updated:** November 28, 2024
**Document Owner:** Infrastructure Team
