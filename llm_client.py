from typing import List, Dict
import os
from dotenv import load_dotenv

try:
    from tamu_chat import TAMUChatClient
    TAMU_AVAILABLE = True
except ImportError:
    TAMU_AVAILABLE = False

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False

# Load environment variables
load_dotenv()


class LLMClient:
    """Client for LLM API with automatic fallback (TAMU → Groq → OpenAI → Ollama)"""
    
    def __init__(self):
        self.client = None
        self.fallback_client = None
        self.provider = None
        self.fallback_provider = None
        
        # Try TAMU AI Chat first (primary)
        tamu_key = os.getenv("TAMU_API_KEY")
        if tamu_key and TAMU_AVAILABLE:
            try:
                self.client = TAMUChatClient(api_key=tamu_key)
                self.model = "gpt-3.5-turbo"
                self.provider = "tamu"
                print("✓ Primary: TAMU AI Chat API (GPT-3.5-turbo)")
            except Exception as e:
                print(f"⚠ TAMU API initialization failed: {e}")
        
        # Set up Groq as fallback
        groq_key = os.getenv("GROQ_API_KEY")
        if groq_key and groq_key != "your-groq-api-key-here" and GROQ_AVAILABLE:
            try:
                self.fallback_client = Groq(api_key=groq_key)
                self.fallback_model = "llama-3.3-70b-versatile"  # Updated model (replaces 3.1)
                self.fallback_provider = "groq"
                print("✓ Fallback: Groq API (Llama 3.3 70B)")
            except Exception as e:
                print(f"⚠ Groq API initialization failed: {e}")
        
        # If no primary, try Groq as primary
        if not self.client and self.fallback_client:
            self.client = self.fallback_client
            self.model = self.fallback_model
            self.provider = self.fallback_provider
            self.fallback_client = None
            print("  → Using Groq as primary (TAMU not available)")
        
        # OpenAI as additional fallback
        if not self.client:
            openai_key = os.getenv("OPENAI_API_KEY")
            if OPENAI_AVAILABLE and openai_key:
                self.client = OpenAI(api_key=openai_key)
                self.model = "gpt-3.5-turbo"
                self.provider = "openai"
                print("✓ Using OpenAI API")
        
        # Ollama as last resort
        if not self.client and OPENAI_AVAILABLE:
            self.client = OpenAI(
                base_url="http://localhost:11434/v1",
                api_key="ollama"
            )
            self.model = "llama3.2"
            self.provider = "ollama"
            print("✓ Using Ollama (local)")
        
        if not self.client:
            raise RuntimeError("No LLM client available. Install: pip install tamu-chat groq openai")
    
    def _call_with_fallback(self, messages: List[Dict], temperature: float, max_tokens: int) -> str:
        """Call LLM with automatic fallback to secondary provider"""
        # Try primary provider
        try:
            if self.provider == "tamu":
                combined_prompt = messages[0]["content"] + "\n\n" + messages[1]["content"]
                response = self.client.chat_completion(combined_prompt)
                return response.text
            elif self.provider == "groq":
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                return response.choices[0].message.content.strip()
            else:  # OpenAI or Ollama
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"⚠ {self.provider} API failed: {e}")
            
            # Try fallback if available
            if self.fallback_client:
                print(f"  → Trying fallback: {self.fallback_provider}")
                try:
                    if self.fallback_provider == "groq":
                        response = self.fallback_client.chat.completions.create(
                            model=self.fallback_model,
                            messages=messages,
                            temperature=temperature,
                            max_tokens=max_tokens
                        )
                        return response.choices[0].message.content.strip()
                except Exception as fallback_error:
                    print(f"⚠ Fallback also failed: {fallback_error}")
            
            raise Exception(f"All LLM providers failed. Primary: {e}")

    def generate_code(self, prompt: str, context: List[Dict], language: str) -> str:
        """Generate code using RAG context"""
        # Build context string - prioritize code chunks
        code_contexts = [item for item in context if item.get('type') == 'code']
        text_contexts = [item for item in context if item.get('type') == 'text']
        
        # Use code contexts first, then text
        priority_contexts = (code_contexts + text_contexts)[:5]
        
        context_str = "\n\n=== DOCUMENTATION ===\n\n".join([
            f"Source: {item['source']}\n\n{item['content']}"
            for item in priority_contexts
        ])
        
        full_prompt = f"""TASK: Generate {language} code for: "{prompt}"

OPENSN DOCUMENTATION (use as reference):
{context_str}

INSTRUCTIONS:
1. FIRST, check if the documentation contains relevant code examples
2. If YES: Use that code as your foundation - include all imports, setup, and structure
3. If the user's request needs modifications or extensions:
   - Start with the documented code
   - Add or modify as needed to fulfill the request
   - Keep the same style and patterns from the documentation
4. If NO relevant code in docs: Generate appropriate OpenSn code based on the documentation context

GUIDELINES:
- Always include necessary imports (from pyopensn.* import ...)
- Follow OpenSn conventions shown in the documentation
- Use classes and methods mentioned in the documentation
- Keep code clean, well-commented, and runnable
- If adapting documented code, maintain its structure
- Return ONLY the code, no explanations before or after

EXAMPLE:
If docs show: "xs_mat = MultiGroupXS(); xs_mat.CreateSimpleOneGroup(sigma_t=2.2, c=0.5)"
And user asks: "create 1-group cross section with sigma_t=3.0"
You should adapt: "xs_mat = MultiGroupXS(); xs_mat.CreateSimpleOneGroup(sigma_t=3.0, c=0.5)"

Generate the {language} code:"""
        
        # Prepare messages
        messages = [
            {
                "role": "system",
                "content": "You are an expert OpenSn developer. Use the provided documentation as your primary reference. When documentation contains relevant code, use it as your foundation. Adapt and extend the code as needed to fulfill the user's specific request while maintaining OpenSn conventions and patterns."
            },
            {
                "role": "user",
                "content": full_prompt
            }
        ]
        
        # Call with automatic fallback
        # Temperature 0.2: Low enough for consistency, high enough for adaptation
        code = self._call_with_fallback(messages, temperature=0.2, max_tokens=2000)
        
        # Clean up markdown code blocks if present
        if "```" in code:
            parts = code.split("```")
            if len(parts) >= 3:
                code = parts[1]
                # Remove language identifier
                if code.startswith(("python", "javascript", "js", "py")):
                    code = "\n".join(code.split("\n")[1:])
        
        # Remove any explanatory text before the code
        lines = code.split("\n")
        code_start = 0
        for i, line in enumerate(lines):
            # Find where actual code starts
            if any(line.strip().startswith(keyword) for keyword in 
                   ["import", "from", "#", "def", "class", "var", "const", "let", "function"]):
                code_start = i
                break
        
        if code_start > 0:
            code = "\n".join(lines[code_start:])
        
        return code.strip()
    
    def explain_code(self, code: str, context: List[Dict]) -> str:
        """Explain code using industry context"""
        context_str = "\n\n".join([
            f"Source: {item['source']}\n{item['content'][:400]}"
            for item in context[:3]
        ])
        
        full_prompt = f"""OpenSn Documentation Context:
{context_str}

Code to explain:
```python
{code}
```

Provide a well-formatted explanation using this structure:

## 📋 Overview
[Brief 1-2 sentence summary of what this code does]

## 🔍 Detailed Breakdown

### Section 1: [Name]
- **Purpose**: [What it does]
- **Key Components**: [Important elements]
- **Parameters**: [If applicable]

### Section 2: [Name]
[Continue for each major section]

## 🎯 Key Concepts
- **[Concept 1]**: [Brief explanation]
- **[Concept 2]**: [Brief explanation]

## 💡 Important Notes
- [Any important considerations, best practices, or warnings]

Use clear markdown formatting with headers, bullet points, and bold text for emphasis."""
        
        messages = [
            {
                "role": "system",
                "content": "You are an expert on OpenSn. Provide well-formatted, structured explanations using markdown. Make explanations clear, organized, and easy to scan with proper headers and formatting."
            },
            {
                "role": "user",
                "content": full_prompt
            }
        ]
        
        return self._call_with_fallback(messages, temperature=0.5, max_tokens=1200)
    
    def explain_concept(self, question: str, context: List[Dict]) -> str:
        """Explain a concept using documentation context"""
        context_str = "\n\n".join([
            f"Source: {item['source']}\n{item['content'][:600]}"
            for item in context[:5]
        ])
        
        full_prompt = f"""OpenSn Documentation:
{context_str}

Question: {question}

Provide a well-formatted, comprehensive explanation using this structure:

## 📖 {question}

### Quick Answer
[Direct, concise answer in 1-2 sentences]

### Detailed Explanation
[Comprehensive explanation with clear paragraphs]

### Key Points
- **Point 1**: [Explanation]
- **Point 2**: [Explanation]
- **Point 3**: [Explanation]

### Example Usage
```python
[If applicable, show a code example]
```

### Related Concepts
- **[Related concept 1]**: [Brief description]
- **[Related concept 2]**: [Brief description]

### References
- [Mention which documentation sources were used]

Use clear markdown formatting with headers, bullet points, code blocks, and bold text for emphasis."""
        
        messages = [
            {
                "role": "system",
                "content": "You are an expert on OpenSn. Provide well-formatted, structured explanations using markdown. Make explanations comprehensive yet scannable with proper headers, bullet points, and formatting."
            },
            {
                "role": "user",
                "content": full_prompt
            }
        ]
        
        return self._call_with_fallback(messages, temperature=0.5, max_tokens=1500)
    
    def check_connection(self) -> bool:
        """Check if API is accessible"""
        try:
            if self.provider == "tamu":
                # Test with a simple query
                self.client.chat_completion("Hello")
                return True
            else:
                self.client.models.list()
                return True
        except Exception as e:
            print(f"API connection failed: {e}")
            return False
