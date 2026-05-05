# OpenSn Doxygen Documentation Validator

A Streamlit web application that validates and automatically fixes Doxygen documentation in C++ header files according to [OpenSn guidelines](https://open-sn.github.io/opensn/devguide/doxygen.html).

## Quick Start

### 1. Setup (First Time Only)

```bash
./setup.sh
```

This will:
- Create a virtual environment
- Install all dependencies (tamu-chat, streamlit, etc.)
- Create a `.env` configuration file

### 2. Configure API Key

Edit `.env` and add your TAMU API key:

```bash
TAMU_API_KEY=your-actual-api-key-here
TAMU_CHAT_API_KEY=your-actual-api-key-here
```

Get your TAMU API key from: https://chat-api.tamu.ai

### 3. Start the App

```bash
./start.sh
```

The app will open in your browser at `http://localhost:8501`

## How to Use

1. **Upload** a C++ header file (.h) or paste code
2. **Validate** - Click "🔍 Validate Documentation"
   - See compliance percentage
   - View all issues found
3. **Fix** - Click "🔧 Fix All Issues"
   - AI generates proper Doxygen comments
   - See side-by-side comparison
   - View list of changes made
4. **Download** - Click "📥 Download Fixed File"

## Features

✅ **Validates** against OpenSn Doxygen guidelines  
✅ **Generates** concise documentation using TAMU AI Chat (GPT-5.4)  
✅ **Uses** OpenSn codebase context from GitHub  
✅ **Fixes** style issues (@note → \note, @param → \param)  
✅ **Shows** side-by-side comparison with GitHub-style diff highlighting  
✅ **Lists** all changes made with line numbers  
✅ **Verifies** AI changes don't modify actual code (only comments)  
✅ **Terminal API** for batch processing files and folders  
✅ **Supports** multiple file uploads (headers + source files)  

## What Gets Checked

### Mandatory Documentation
- All classes, structs, unions
- All public methods (except trivial getters/setters)
- All member variables (private, protected, public)
- All static members and methods

### Style Rules
- Use `///` for single-line comments
- Use `/** */` for multi-line comments
- Use `\param`, `\return`, `\note` (NOT @param, @return, @note)
- NO `\brief` or `\details` commands

### Entity-Specific Rules
- **Classes**: Noun phrase brief (e.g., "Geometry manager for mesh operations")
- **Methods**: Verb in base form (e.g., "Build the geometry structures")
- **Variables**: Noun phrase (e.g., "Spatial dimension of the domain")

## Example

### Before (0% Compliant)
```cpp
class GeometryManager
{
public:
  void BuildGeometry();
  
private:
  size_t dimension_;
};
```

### After (100% Compliant)
```cpp
/// Geometry manager for mesh operations.
class GeometryManager
{
public:
  /// Build the geometry structures.
  void BuildGeometry();
  
private:
  /// Spatial dimension of the domain.
  size_t dimension_;
};
```

## Project Structure

```
nuclear_doxygen/
├── setup.sh              # Setup script (run once)
├── start.sh              # Start the web app
├── streamlit_app.py      # Web interface
├── doxygen_validator.py  # Validation engine
├── llm_client.py         # TAMU AI Chat integration (GPT-5.4)
├── code_verifier.py      # Verifies AI doesn't modify code
├── doxygen_cli.py        # Terminal API for batch processing
├── angle_set.h           # Reference file (perfect docs)
├── demo_file.h           # Example file to test
├── requirements.txt      # Python dependencies
├── .env                  # API configuration
├── TROUBLESHOOTING.md    # API troubleshooting guide
└── README.md             # This file
```

## Requirements

- Python 3.8 or higher
- TAMU AI Chat API key
- Internet connection (for API calls)

## How It Works

1. **Parser** - Identifies all classes, methods, and variables in the C++ file
2. **Validator** - Checks each entity against OpenSn Doxygen guidelines
3. **Generator** - Uses TAMU AI Chat to generate proper documentation
   - Understands OpenSn codebase context from GitHub
   - Follows angle_set.h style exactly
   - Generates concise, meaningful descriptions
4. **Fixer** - Inserts documentation and fixes style issues
5. **Comparison** - Shows before/after with changes highlighted

## Guidelines Reference

Full guidelines: https://open-sn.github.io/opensn/devguide/doxygen.html

### Key Points

**DO:**
- Use `///` for single-line: `/// Brief description.`
- Use `/** */` for multi-line with parameters
- Use backslash commands: `\param`, `\return`, `\note`
- Write brief descriptions (3-8 words)
- Use noun phrases for classes/variables
- Use verb phrases for methods

**DON'T:**
- Use @-style commands: `@param`, `@return`, `@note`
- Use `\brief` or `\details` commands
- Write verbose descriptions
- Just restate the name (BAD: "/// Dimension.")

## Troubleshooting

### Setup Issues

```bash
# Make sure scripts are executable
chmod +x setup.sh start.sh

# If Python 3 not found
# Install Python 3.8+ from python.org
```

### API Issues

- Check `.env` has valid `TAMU_API_KEY`
- App shows connection status in sidebar
- Test API: `./venv/bin/python -c "from llm_client import LLMClient; print(LLMClient().provider)"`

### App Won't Start

```bash
# Reinstall dependencies
./venv/bin/pip install -r requirements.txt

# Or run setup again
./setup.sh
```

## Advanced Usage

### Terminal API (Batch Processing)

Process multiple files or entire directories:

```bash
# Validate a single file
python3 doxygen_cli.py myfile.h

# Fix a file and save to new file
python3 doxygen_cli.py myfile.h --fix

# Fix in-place with backup
python3 doxygen_cli.py myfile.h --fix --in-place --backup

# Process all .h files in a directory
python3 doxygen_cli.py src/ --fix --in-place

# Process recursively
python3 doxygen_cli.py src/ --fix --in-place --recursive

# Verbose output
python3 doxygen_cli.py myfile.h --fix --verbose

# Disable code verification (not recommended)
python3 doxygen_cli.py myfile.h --fix --no-verify
```

### Code Verification

The system automatically verifies that AI-generated changes only affect comments, not actual code:

1. Strips all comments and empty lines from both original and fixed versions
2. Compares the stripped code
3. Rejects changes if code was modified

This prevents the AI from accidentally changing function signatures, variable names, or other code elements.

To disable verification (not recommended):
- Web UI: Not available (always enabled for safety)
- CLI: Use `--no-verify` flag

### Command Line Testing

Test the validator without the UI:

```bash
python3 -c "
from doxygen_validator import DoxygenValidator
validator = DoxygenValidator()
with open('demo_file.h') as f:
    result = validator.validate_file(f.read())
print(f'Issues: {result[\"issues_found\"]}')
"
```

### Custom Reference File

Edit `doxygen_validator.py` line 14 or use CLI flag:

```python
validator = DoxygenValidator(reference_file_path="your_file.h")
```

Or with CLI:
```bash
python3 doxygen_cli.py myfile.h --reference your_reference.h
```

## API Information

**Primary**: TAMU AI Chat (GPT-5.4 model)  
**Fallback**: Groq (Llama 3.3 70B) → OpenAI → Ollama

The app automatically falls back if TAMU API is unavailable.

### Available Models

The TAMU API provides access to multiple models:
- GPT models: `protected.gpt-5.4`, `protected.gpt-5`, `protected.gpt-4o`, etc.
- Claude models: `protected.Claude Opus 4.6`, `protected.Claude Sonnet 4.6`, etc.
- Gemini models: `protected.gemini-2.5-pro`, etc.

Current configuration uses `protected.gpt-5.4` for best results.

## Contributing

To add features or fix bugs:

1. Edit the relevant file:
   - `streamlit_app.py` - UI changes
   - `doxygen_validator.py` - Validation logic
   - `llm_client.py` - API integration

2. Test your changes:
   ```bash
   ./start.sh
   ```

3. The app auto-reloads when files change

## License

MIT

## Credits

- OpenSn Project: https://github.com/Open-Sn/opensn
- OpenSn Doxygen Guidelines: https://open-sn.github.io/opensn/devguide/doxygen.html
- TAMU AI Chat: https://chat-api.tamu.ai
- Reference file: angle_set.h from OpenSn project
