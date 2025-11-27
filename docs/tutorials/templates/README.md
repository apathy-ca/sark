# SARK Tutorial Templates

This directory contains standardized templates for creating consistent, high-quality tutorials for SARK.

## Available Templates

### 1. General Tutorial Template
**File:** `TUTORIAL_TEMPLATE.md`
**Use for:** Comprehensive tutorials with multiple steps

**Best for:**
- Feature walkthroughs (30-90 minutes)
- Multi-step configurations
- Complex workflows
- In-depth learning experiences

**Includes:**
- Learning objectives
- Prerequisites with verification
- Step-by-step instructions with code examples
- Troubleshooting section
- Verification steps
- Next steps and resources
- Summary and cleanup

---

### 2. Quick Start Template
**File:** `QUICKSTART_TEMPLATE.md`
**Use for:** Fast, focused tutorials (5-15 minutes)

**Best for:**
- Getting started guides
- Single-feature demonstrations
- Proof-of-concept setups
- Time-constrained users

**Includes:**
- Minimal prerequisites
- 3-5 rapid steps
- Quick verification
- Emergency troubleshooting
- Links to deeper content

---

### 3. API Integration Template
**File:** `API_INTEGRATION_TEMPLATE.md`
**Use for:** External system integrations via API

**Best for:**
- Third-party service integrations
- Webhook implementations
- API client development
- Integration testing

**Includes:**
- API endpoint documentation
- Authentication methods
- Request/response examples
- Error handling patterns
- Rate limiting strategies
- Production checklist
- Monitoring setup

---

### 4. Policy Development Template
**File:** `POLICY_TUTORIAL_TEMPLATE.md`
**Use for:** OPA/Rego policy creation

**Best for:**
- Authorization policy development
- Custom Rego rules
- Policy testing and deployment
- Security policy implementation

**Includes:**
- Business requirements mapping
- Test case definitions
- Rego code structure
- Unit testing framework
- Performance optimization
- Deployment procedures
- Monitoring and debugging

---

## How to Use These Templates

### Step 1: Choose the Right Template

Match your tutorial type to the appropriate template:

| Tutorial Goal | Template | Duration |
|---------------|----------|----------|
| Quick demo of a feature | Quick Start | 5-15 min |
| Detailed feature tutorial | General Tutorial | 30-90 min |
| External API integration | API Integration | 30-60 min |
| Policy development | Policy Tutorial | 30-90 min |

### Step 2: Copy the Template

```bash
# Navigate to tutorials directory
cd docs/tutorials

# Copy template to new tutorial
cp templates/TUTORIAL_TEMPLATE.md ./tutorial-name/README.md

# Or for quick starts
cp templates/QUICKSTART_TEMPLATE.md ./quickstart-feature-name.md
```

### Step 3: Fill in the Template

Replace all placeholders (in square brackets `[like this]`):

**Common placeholders:**
- `[Tutorial Title]` → Actual tutorial title
- `[Description]` → Brief description
- `[X minutes]` → Estimated time
- `[Action]` → Specific action to take
- `[command]` → Actual command to run
- `[expected output]` → What users should see

### Step 4: Add Examples

**Good code examples:**

```bash
# ✅ GOOD: Specific, copy-pasteable
export SARK_API_KEY="sk_test_abc123xyz789"
curl -X GET "https://sark.example.com/api/v1/servers" \
  -H "Authorization: Bearer ${SARK_API_KEY}"
```

```bash
# ❌ BAD: Too generic
export API_KEY="your-key"
curl API_URL
```

### Step 5: Test the Tutorial

Before publishing:

- [ ] **Follow your own tutorial** - Do it step-by-step
- [ ] **Fresh environment** - Test on clean system if possible
- [ ] **Verify outputs** - Ensure all outputs match
- [ ] **Test troubleshooting** - Verify fixes work
- [ ] **Peer review** - Have someone else try it
- [ ] **Timing** - Confirm time estimate is accurate

---

## Writing Guidelines

### General Principles

1. **User-Centric Language**
   - ✅ "You'll deploy a server..."
   - ❌ "The server will be deployed..."

2. **Clear Action Verbs**
   - ✅ "Create", "Configure", "Deploy", "Test"
   - ❌ "Deal with", "Handle", "Work with"

3. **One Step, One Action**
   - ✅ "Step 1: Install dependencies"
   - ❌ "Step 1: Install dependencies, configure settings, and deploy"

4. **Progressive Disclosure**
   - Start simple, add complexity gradually
   - Use `<details>` tags for advanced content

### Code Examples

**Always include:**
- Comments explaining what the code does
- Expected output or results
- Error handling when relevant

**Example:**

```bash
# Register a new MCP server
# This creates a server entry in SARK's database
curl -X POST "${SARK_API_URL}/api/v1/servers" \
  -H "Authorization: Bearer ${SARK_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-mcp-server",
    "transport": "http",
    "endpoint": "https://mcp.example.com"
  }'

# Expected output:
# {
#   "id": "srv_abc123",
#   "name": "my-mcp-server",
#   "status": "registered",
#   "created_at": "2025-11-27T12:00:00Z"
# }
```

### Troubleshooting Sections

**Pattern:**

```markdown
### Issue: [Descriptive problem title]

**Symptoms:**
- [What users see]
- [Error messages]

**Cause:**
[Why this happens]

**Solution:**
[Step-by-step fix]

```bash
# Fix command
[command with explanation]
```
```

### Verification Steps

Always include verification:

```markdown
## ✅ Verify It Works

Test your setup with these commands:

```bash
# 1. Check server status
curl -X GET "${SARK_API_URL}/api/v1/servers/${SERVER_ID}" \
  -H "Authorization: Bearer ${SARK_API_KEY}"

# Expected: status should be "active"

# 2. Test server health
curl -X GET "${SARK_API_URL}/api/v1/servers/${SERVER_ID}/health" \
  -H "Authorization: Bearer ${SARK_API_KEY}"

# Expected: {"healthy": true, "last_check": "..."}
```

**If all checks pass: 🎉 Your setup is working!**
```

---

## Template Customization

### Adding New Sections

You can add custom sections for specific needs:

```markdown
## Advanced Configuration

[Custom section content]

---

## Integration with Other Services

[Custom section content]

---
```

### Removing Sections

Not all sections are required. Remove sections that don't apply:

- Remove "Cleanup" if no cleanup is needed
- Remove "Webhooks" if not using webhooks
- Remove "Specialization Tracks" if not applicable

### Creating Variations

For recurring tutorial types, create specialized templates:

```bash
# Example: Create a deployment tutorial template
cp TUTORIAL_TEMPLATE.md DEPLOYMENT_TEMPLATE.md

# Then customize the deployment-specific sections
```

---

## Quality Checklist

Before publishing a tutorial:

### Content Quality
- [ ] Clear learning objectives stated
- [ ] Prerequisites listed and verifiable
- [ ] All steps are actionable
- [ ] Code examples are tested and work
- [ ] Expected outputs are accurate
- [ ] Troubleshooting covers common issues
- [ ] Links to related resources included

### User Experience
- [ ] Estimated time is accurate (tested)
- [ ] Difficulty level is appropriate
- [ ] Commands are copy-pasteable
- [ ] No assumed knowledge beyond prerequisites
- [ ] Success criteria are clear
- [ ] Next steps guide users forward

### Technical Quality
- [ ] All commands execute without errors
- [ ] API calls use correct endpoints
- [ ] Environment variables are defined
- [ ] Security best practices followed
- [ ] No hardcoded credentials
- [ ] Clean up procedures work

### Documentation
- [ ] Proper markdown formatting
- [ ] No spelling errors
- [ ] Consistent terminology
- [ ] Code syntax highlighting correct
- [ ] Images/diagrams are clear (if included)
- [ ] Internal links work

---

## Style Guide

### Formatting

**Bold** for UI elements and emphasis:
- Click the **Settings** button
- This is **important**

**Code** for technical terms, commands, filenames:
- Use the `curl` command
- Edit `config.yaml`
- Set `SARK_API_KEY`

**Italic** for notes and asides:
- *Note: This feature requires SARK v2.0+*

### Emojis (Sparingly)

Use emojis to draw attention to key points:
- ✅ Success indicators
- ❌ Warnings/failures
- 💡 Tips and tricks
- ⚠️ Important warnings
- 🎉 Achievements/completions
- 🆘 Help/troubleshooting
- 📚 Documentation links
- 🏆 Advanced/expert content

Don't overuse - maximum 1-2 per major section.

### Command Formatting

```bash
# ✅ GOOD: Clear comments, readable formatting
export SARK_API_URL="https://sark.example.com"
curl -X POST "${SARK_API_URL}/api/v1/servers" \
  -H "Authorization: Bearer ${SARK_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-server",
    "transport": "http"
  }'
```

```bash
# ❌ BAD: No comments, hard to read
curl -X POST "https://sark.example.com/api/v1/servers" -H "Authorization: Bearer ${SARK_API_KEY}" -H "Content-Type: application/json" -d '{"name":"my-server","transport":"http"}'
```

---

## Examples of Great Tutorials

See these examples for reference:

1. **Quick Start:** (Future) `docs/tutorials/quickstart-register-server.md`
2. **Full Tutorial:** (Future) `docs/tutorials/tutorial-01-basic-setup/README.md`
3. **API Integration:** (Future) `docs/tutorials/integrations/kong-gateway/README.md`
4. **Policy Tutorial:** (Future) `docs/tutorials/policies/team-based-access/README.md`

---

## Getting Help

### Questions About Templates

- **Slack:** `#sark-documentation`
- **GitHub:** Open an issue with `documentation` label
- **Email:** docs@your-org.com

### Suggesting Improvements

We welcome template improvements!

```bash
# 1. Create a branch
git checkout -b improve-tutorial-template

# 2. Make your changes
edit docs/tutorials/templates/TUTORIAL_TEMPLATE.md

# 3. Submit PR
git add .
git commit -m "docs: improve tutorial template with X"
git push origin improve-tutorial-template

# 4. Open PR on GitHub
```

---

## Template Versioning

Templates follow semantic versioning:

**Current Versions:**
- General Tutorial: v1.0.0
- Quick Start: v1.0.0
- API Integration: v1.0.0
- Policy Development: v1.0.0

**Changelog:**

### v1.0.0 (2025-11-27)
- Initial release of all templates
- Created by Engineer 1 (Frontend Specialist)
- Part of Week 2 Session W2-E1-02

---

## License

These templates are part of the SARK project and follow the same license.

---

**Created:** 2025-11-27 (Week 2, Session W2-E1-02)
**Engineer:** Engineer 1 (Frontend Specialist)
**Status:** 4 templates complete ✅
