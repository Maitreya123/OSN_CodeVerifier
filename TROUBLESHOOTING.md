# Troubleshooting Guide

## 500 Internal Server Error

If you're getting a "500 Internal Server Error" when testing the TAMU API, this typically means:

### Cause 1: Invalid API Key
Your API key is incorrect or malformed.

**Solution:**
1. Go to https://chat-api.tamu.ai
2. Generate a new API key
3. Update your `.env` file:
   ```
   TAMU_API_KEY=your-new-api-key-here
   ```
4. Run the test again: `python3 nuclear_doxygen/test_api.py`

### Cause 2: Expired API Key
Your API key has expired.

**Solution:**
1. Go to https://chat-api.tamu.ai
2. Generate a new API key
3. Update your `.env` file with the new key
4. Test again

### Cause 3: TAMU API Service Issue
The TAMU API service might be temporarily down.

**Solution:**
1. Wait 5-10 minutes
2. Try again
3. If still failing, the system will automatically fall back to Groq API (if configured)

## Testing Your Setup

Run the diagnostic test:
```bash
python3 nuclear_doxygen/test_api.py
```

This will:
- Check if your API key is present
- Test the connection
- Provide specific error diagnostics
- Suggest solutions

## Common Error Messages

### "TAMU_API_KEY not found in .env file"
**Problem:** No API key configured

**Solution:**
1. Create or edit `.env` file in the project root
2. Add: `TAMU_API_KEY=your-api-key-here`

### "401 Unauthorized"
**Problem:** Invalid API key

**Solution:** Get a new API key from https://chat-api.tamu.ai

### "429 Rate Limit Exceeded"
**Problem:** Too many requests

**Solution:** Wait 5-10 minutes before trying again

### "Connection timeout"
**Problem:** Network issue

**Solution:** Check your internet connection

## Fallback System

The system has automatic fallback:
1. **Primary:** TAMU AI Chat (default model)
2. **Fallback 1:** Groq API (Llama 3.3 70B)
3. **Fallback 2:** OpenAI API
4. **Fallback 3:** Ollama (local)

To enable fallback providers, add to `.env`:
```
GROQ_API_KEY=your-groq-key
OPENAI_API_KEY=your-openai-key
```

## Getting Help

If you're still having issues:

1. Run the diagnostic test and save the output:
   ```bash
   python3 nuclear_doxygen/test_api.py > test_output.txt
   ```

2. Check that your `.env` file has the correct format:
   ```
   TAMU_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```

3. Verify your API key at https://chat-api.tamu.ai

4. Try generating a fresh API key

## Quick Fix Checklist

- [ ] API key is in `.env` file
- [ ] API key starts with `sk-`
- [ ] No extra spaces or quotes around the key
- [ ] `.env` file is in the project root directory
- [ ] Ran `python3 nuclear_doxygen/test_api.py` to test
- [ ] Internet connection is working
- [ ] Tried generating a new API key
