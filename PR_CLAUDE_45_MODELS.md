# PR: Update to Claude 4.5 models with dev mode

## Summary

Update Claude API integration to use the latest Claude 4.5 models with a development mode toggle for cost optimization during development.

## Changes

### Model Configuration
- **Production models:**
  - Haiku: `claude-haiku-4-5-20251001`
  - Sonnet: `claude-sonnet-4-5-20250929`
- **Development mode:** Added `USE_DEV_MODE` flag (currently `True`)
  - When enabled: All queries use Haiku for cost savings
  - When disabled: Uses Sonnet/Haiku based on query requirements

### Code Cleanup
- Removed hardcoded token pricing (changes too frequently)
- Simplified cost calculation methods to return 0.0
- Added notes directing to Anthropic's pricing page for current rates

## Benefits

1. **Latest models:** Access to Claude 4.5's improved capabilities
2. **Cost control:** Dev mode prevents expensive Sonnet calls during development
3. **Maintainability:** Removed hardcoded pricing that becomes stale
4. **Easy toggle:** Single flag to switch between dev and production modes

## Testing

- [x] Backend starts successfully with new model names
- [x] Initial analysis works with Haiku 4.5
- [x] Queries work with dev mode enabled
- [ ] Production mode testing (requires setting `USE_DEV_MODE = False`)

## Files Changed

- `web/core/claude.py` - Model configuration and dev mode logic

## Migration Notes

To switch to production mode:
```python
# In web/core/claude.py, line 26
USE_DEV_MODE = False  # Changed from True
```

No other changes needed - the code automatically uses the configured models.

## Commands to create PR

```bash
# Option 1: Using GitHub web interface
# 1. Go to https://github.com/bwaxse/claude-paper-companion
# 2. Click "Pull requests" > "New pull request"
# 3. Base: main, Compare: claude/build-pdf-viewer-011FrmvFBWntNpv77BmVYvPx
# 4. Copy the content above into the PR description

# Option 2: If gh CLI becomes available
gh pr create \
  --base main \
  --head claude/build-pdf-viewer-011FrmvFBWntNpv77BmVYvPx \
  --title "Update to Claude 4.5 models with dev mode" \
  --body-file PR_CLAUDE_45_MODELS.md
```
