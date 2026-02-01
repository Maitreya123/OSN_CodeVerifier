"""
Doxygen Documentation Validator and Fixer
Uses TAMU AI Chat to validate and fix Doxygen documentation in C++ header files
"""

import re
from typing import List, Dict, Tuple
from llm_client import LLMClient


class DoxygenValidator:
    """Validates and fixes Doxygen documentation in C++ header files"""
    
    def __init__(self, reference_file_path: str = "angle_set.h"):
        self.llm_client = LLMClient()
        self.guidelines = self._load_guidelines()
        self.reference_example = self._load_reference_example(reference_file_path)
    
    def _load_reference_example(self, file_path: str) -> str:
        """Load reference example file (angle_set.h)"""
        try:
            with open(file_path, 'r') as f:
                return f.read()
        except FileNotFoundError:
            return "Reference file not found"
    
    def _load_guidelines(self) -> str:
        """Load Doxygen guidelines from OpenSn documentation"""
        return """
OpenSn Doxygen Guidelines (https://open-sn.github.io/opensn/devguide/doxygen.html):

PURPOSE:
Provide developer-facing documentation for OpenSn using Doxygen.

COVERAGE REQUIREMENTS:

Mandatory documentation:
- All classes, structs, and unions
- All public methods except trivial getters/setters (reference/const reference to member, get/set member value)
- All member variables (private, protected, public)
- All static members and methods
- All functions except translation-unit local functions (static functions, anonymous namespace functions)
- All extern and constexpr variables declared in headers
- All C++20 concepts

Optional documentation:
- Protected methods: document if non-trivial
- Private methods: document only if logic is complex or non-obvious
- Deprecated APIs: brief note or no documentation
- Enums: brief description of enum purpose and each value (skip if obvious)
- Operator overloading: document if usage not self-explanatory

Do NOT document:
- Files
- Entities not declared in header files
- Type aliasing (using or typedef)
- Namespaces
- Preprocessor macros
- Default constructors
- Copy/move constructors and assignments
- Destructors

GENERIC GUIDELINES:
- Use backslash-style commands (\\return, \\param) NOT @-style
- Single-line: use ///
- Multi-line: use /** */
- NO \\brief or \\details (JAVADOC_AUTOBRIEF=ON)
- Text up to first full stop = brief description (automatic)
- Optional detailed description begins on new line after brief
- Write in clear, concise English
- Avoid implementation details unless necessary
- Document pitfalls using \\note or \\warning

CLASSES/STRUCTS:
- Brief: one-line noun phrase (NOT verb or complete sentence)
- Avoid redundant "Class that represents..."
- Optional detailed description should explain:
  * Design rationale, usage guidelines, valid conditions
  * Ownership, thread-safety, design patterns
  * Interaction with other classes, performance considerations
- Document at definition, NOT forward declarations
- Document members inside class body only, NOT outside
- For C++17 CTAD: document class definition only, deduction guides in class description or constructor

UNIONS:
- Document at definition, NOT forward declarations
- Brief: one-line noun phrase at top of union body
- Document all fields inside union body with noun phrase briefs
- Use inline comments (//) for complex/nested types only
- Do NOT document methods outside union body

FUNCTIONS/METHODS:
- Brief: one-line summary using verb in base form (without "s"/"es")
- Document at declaration in header, NOT at definition in source
- Optional detailed description should explain:
  * Purpose, algorithm, input/output behavior
  * Assumptions, side effects, performance notes
  * Preconditions, exceptions
- Use full sentences when possible
- Include \\param, \\return (if not void and not trivial), \\throw/\\exception

VARIABLES/CLASS MEMBERS:
- Brief: one-line noun phrase describing nature or purpose
- Must NOT describe entities solely by naming mathematical symbol
- BAD: "/// Alpha." or "/// Value of x in the algorithm."
- Exception: class members explicitly defined in mathematical formulation in class docs
- Describe what variable represents or how it's used, not just symbolic name

TEMPLATE PARAMETERS:
- Use \\tparam when:
  * Template parameter has semantic meaning beyond generic STL type
  * Parameter imposes constraints, expectations, or specific behavior
  * Intended use not obvious from standard STL conventions
  * Parameter affects algorithm behavior, ownership, or performance
- Omit when:
  * Generic typename
  * Strictly follows well-known STL conventions
  * No additional assumptions or constraints
- Describe what type represents and state all constraints (arithmetic, movable, comparable) in noun phrase

C++20 CONCEPTS:
- All concepts must be documented
- Use noun phrase describing requirements
- Focus on what concept guarantees
- Provide additional explanation if behavior is complex

MACRO-DEPENDENT IMPLEMENTATION:
- For class/function/variable affected by macros, state:
  * Macro dependency
  * Behavioral difference
  * Availability
- If API only exists under macro: "Only available when `MACRO_NAME` is defined"
- If macro not defined for Doxygen: add || defined(DOXYGEN_SHOULD_SKIP_THIS)
"""
    
    def validate_file(self, file_content: str) -> Dict:
        """
        Validate entire file for Doxygen compliance
        Returns dict with validation results
        """
        lines = file_content.split('\n')
        issues = []
        
        # Parse file structure
        entities = self._parse_entities(file_content)
        
        # Filter out entities that are already properly documented
        entities_needing_validation = []
        for entity in entities:
            entity_issues = self._validate_entity(entity, lines)
            if entity_issues:
                issues.extend(entity_issues)
                entities_needing_validation.append(entity)
        
        return {
            'total_entities': len(entities),
            'issues_found': len(issues),
            'issues': issues,
            'entities': entities_needing_validation  # Only entities with issues
        }
    
    def _parse_entities(self, content: str) -> List[Dict]:
        """Parse C++ entities that need documentation"""
        entities = []
        lines = content.split('\n')
        
        in_class = False
        class_name = None
        brace_count = 0
        access_level = 'private'  # default for class
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # Skip empty lines, preprocessor directives, comments, and license headers
            if not stripped or stripped.startswith('#') or stripped.startswith('//'):
                continue
            
            # Skip namespace declarations
            if stripped.startswith('namespace'):
                continue
            
            # Track access level
            if stripped in ['public:', 'protected:', 'private:']:
                access_level = stripped.rstrip(':')
                continue
            
            # Track class/struct scope
            if re.match(r'(class|struct)\s+\w+', stripped):
                match = re.search(r'(class|struct)\s+(\w+)', stripped)
                if match and not stripped.endswith(';'):  # Not forward declaration
                    in_class = True
                    class_name = match.group(2)
                    entities.append({
                        'type': 'class',
                        'name': class_name,
                        'line': i + 1,
                        'content': line,
                        'access': 'public'
                    })
            
            # Track braces
            brace_count += stripped.count('{') - stripped.count('}')
            if brace_count == 0 and in_class:
                in_class = False
                class_name = None
                access_level = 'private'
            
            # Skip if not in class or not public
            if not in_class:
                continue
            
            # Member variables (but not method calls)
            if in_class and ';' in stripped:
                # Check if it's a variable declaration (not a method)
                if re.search(r'\b(const\s+)?\w+[\*&\s]+\w+\s*[;=]', stripped) and '(' not in stripped:
                    # Skip if it's inside a method body or constructor initializer
                    if not any(x in stripped for x in ['return', 'if', 'for', 'while']):
                        entities.append({
                            'type': 'member_variable',
                            'class': class_name,
                            'line': i + 1,
                            'content': line,
                            'access': access_level
                        })
            
            # Methods/functions (but not constructors/destructors in some cases)
            if in_class and '(' in stripped and ')' in stripped:
                # Skip constructor initializer lists
                if ':' in stripped and '(' in stripped and i > 0:
                    continue
                
                # Skip lines that are just function calls (not declarations)
                # These are lines inside method bodies
                if not any(keyword in stripped for keyword in ['virtual', 'const', 'static', 'explicit', 'inline']) and ';' not in stripped and '{' not in stripped:
                    continue
                    
                # Check if it's a method declaration
                if ';' in stripped or 'virtual' in stripped or '{' in stripped:
                    # Skip trivial getters/setters (single line with return)
                    is_trivial = False
                    if '{' in stripped and '}' in stripped and 'return' in stripped:
                        # Check if it's a simple getter
                        if re.search(r'return\s+[\*&]?\w+_', stripped):
                            is_trivial = True
                    
                    if not is_trivial:
                        entities.append({
                            'type': 'method',
                            'class': class_name,
                            'line': i + 1,
                            'content': line,
                            'access': access_level
                        })
        
        return entities
    
    def _validate_entity(self, entity: Dict, lines: List[str]) -> List[Dict]:
        """Validate a single entity for Doxygen compliance"""
        issues = []
        line_idx = entity['line'] - 1
        
        # Check for documentation above the entity
        has_doc = False
        doc_lines = []
        
        # Look backwards for documentation (up to 15 lines)
        for i in range(line_idx - 1, max(0, line_idx - 15), -1):
            line = lines[i].strip()
            
            # Found Doxygen comment
            if line.startswith('///') or line.startswith('/**') or (line.startswith('*') and not line.startswith('*/')):
                has_doc = True
                doc_lines.insert(0, line)
            elif line.startswith('*/'):
                has_doc = True
                doc_lines.insert(0, line)
            # Empty line
            elif not line:
                if has_doc:
                    break
                continue
            # Hit code before finding doc
            else:
                break
        
        # Determine if this entity needs documentation
        needs_doc = False
        
        if entity['type'] == 'class':
            needs_doc = True
        elif entity['type'] == 'method':
            code = entity['content'].strip()
            
            # Check the next few lines for method body (for multi-line methods)
            method_body = code
            if line_idx + 1 < len(lines):
                for i in range(line_idx + 1, min(line_idx + 5, len(lines))):
                    method_body += ' ' + lines[i].strip()
            
            # Skip destructors (per guidelines)
            if '~' in code:
                needs_doc = False
            # Skip trivial getters/setters (per guidelines)
            elif '{' in code and '}' in code and ('return' in code or '=' in code):
                needs_doc = False
            # Skip methods that just throw errors (not implemented)
            elif 'Error(' in method_body or 'throw' in method_body:
                needs_doc = False
            # Public methods need documentation
            elif entity.get('access') == 'public':
                needs_doc = True
        elif entity['type'] == 'member_variable':
            needs_doc = True
        
        # Flag missing documentation
        if needs_doc and not has_doc:
            issues.append({
                'entity': entity,
                'issue_type': 'missing_documentation',
                'severity': 'error',
                'message': f"Missing Doxygen documentation for {entity['type']}"
            })
            return issues
        
        # If documentation EXISTS, validate its style
        if has_doc:
            doc_text = ' '.join(doc_lines)
            
            # Check for @-style commands (should use backslash)
            if re.search(r'@(param|return|throw|tparam|note|warning)', doc_text):
                issues.append({
                    'entity': entity,
                    'issue_type': 'wrong_style',
                    'severity': 'error',
                    'message': 'Use backslash-style commands (\\param, \\return, \\note) not @-style (@param, @return, @note)'
                })
            
            # Check for \\brief or \\details (should not be used)
            if '\\brief' in doc_text or '\\details' in doc_text:
                issues.append({
                    'entity': entity,
                    'issue_type': 'wrong_command',
                    'severity': 'error',
                    'message': 'Do not use \\brief or \\details (JAVADOC_AUTOBRIEF=ON)'
                })
            
            # Check if using proper comment style (/// or /** */)
            first_doc_line = doc_lines[0] if doc_lines else ''
            if first_doc_line and not (first_doc_line.startswith('///') or first_doc_line.startswith('/**') or first_doc_line.startswith('*')):
                issues.append({
                    'entity': entity,
                    'issue_type': 'wrong_format',
                    'severity': 'error',
                    'message': 'Use /// for single-line or /** */ for multi-line comments'
                })
        
        return issues
    
    def _validate_documentation(self, doc_text: str, entity: Dict) -> List[Dict]:
        """Validate documentation quality"""
        issues = []
        
        # Check for \\brief or \\details (should not be used)
        if '\\brief' in doc_text or '\\details' in doc_text:
            issues.append({
                'entity': entity,
                'issue_type': 'wrong_command',
                'severity': 'error',
                'message': 'Do not use \\brief or \\details (JAVADOC_AUTOBRIEF=ON)'
            })
        
        # Check for @ commands (should use backslash)
        if re.search(r'@(param|return|throw|tparam)', doc_text):
            issues.append({
                'entity': entity,
                'issue_type': 'wrong_style',
                'severity': 'error',
                'message': 'Use backslash-style commands (\\param) not @-style'
            })
        
        return issues
    
    def fix_entity(self, entity: Dict, file_content: str) -> str:
        """Generate proper Doxygen documentation for an entity using LLM"""
        
        # Prepare context for LLM
        context_lines = file_content.split('\n')
        line_idx = entity['line'] - 1
        
        # Get surrounding context (5 lines before and after)
        start = max(0, line_idx - 5)
        end = min(len(context_lines), line_idx + 6)
        context = '\n'.join(context_lines[start:end])
        
        # Build prompt for LLM with reference example
        prompt = f"""Generate proper Doxygen documentation for this C++ code following OpenSn guidelines.

=== REFERENCE EXAMPLE (angle_set.h) - YOUR STYLE GUIDE ===
Study these EXACT examples from angle_set.h and match their brevity and style:

```cpp
{self.reference_example}
```

Key examples from angle_set.h:
- Class: "/// Angles for a given groupset" (SHORT noun phrase)
- Method: "/// Get the number of angles in the angleset." (SHORT verb phrase)
- Variable: "/// Unique ID of the angleset." (SHORT noun phrase)
- Constructor with params: Uses /** */ with brief \\param descriptions

=== STRICT GUIDELINES ===
{self.guidelines}

=== CODE TO DOCUMENT ===
```cpp
{context}
```

Entity: {entity['type']} at line {entity['line']}
Code: {entity['content']}

IMPORTANT: Document ONLY this specific {entity['type']} on line {entity['line']}.
DO NOT generate documentation for other entities (like constructors, other methods, etc.).
Focus ONLY on the entity shown above.

=== CRITICAL RULES ===
1. **BE CONCISE**: Match angle_set.h brevity - NO long descriptions
2. **Single-line when possible**: Use /// for simple getters, variables, simple methods
3. **Multi-line only for constructors/complex methods**: Use /** */ with \\param
4. **Brief descriptions**:
   - Classes: SHORT noun phrase (3-6 words max)
   - Methods: SHORT verb phrase starting with verb (5-8 words max)
   - Variables: SHORT noun phrase (3-6 words max)
5. **NO generic descriptions**: Be specific to OpenSn context but BRIEF
6. **Follow angle_set.h patterns EXACTLY**:
   - "/// Get the [thing]." NOT "/// This method retrieves the [thing] from..."
   - "/// [Noun phrase]." NOT "/// This is a [noun phrase] that..."
7. **Parameters**: Brief, specific descriptions (one line each)
8. **NO explanations, NO verbose text, NO implementation details**

=== EXAMPLES OF CORRECT STYLE ===
GOOD: "/// Geometry manager for mesh operations."
BAD:  "/// This class manages geometry operations and provides an interface for mesh handling..."

GOOD: "/// Build the geometry structures."
BAD:  "/// This method builds and initializes all geometry structures required for the simulation..."

GOOD: "/// Spatial dimension of the domain."
BAD:  "/// This variable stores the spatial dimension (1D, 2D, or 3D) of the computational domain..."

Generate ONLY the Doxygen comment block.
Match angle_set.h style EXACTLY - be CONCISE.
Return ONLY the comment, nothing else.

CRITICAL: 
- Do NOT include markdown code fences (```cpp or ```).
- Do NOT include any explanatory text.
- Do NOT include the code itself.
- ONLY return the /// or /** */ comment itself.
- Do NOT regenerate or repeat the code being documented.

Example of CORRECT output for a class:
/// Geometry manager for meshes

Example of WRONG output (includes code):
/// Geometry manager for meshes
class GeometryManager { ... }

Return ONLY the comment!"""

        messages = [
            {
                "role": "system", 
                "content": "You are an expert at writing CONCISE Doxygen documentation for OpenSn (https://github.com/Open-Sn/opensn). You follow angle_set.h style EXACTLY - brief, clear, no verbose descriptions. You understand OpenSn's radiation transport framework but keep descriptions SHORT. Single-line comments when possible, multi-line only for constructors/complex methods with parameters."
            },
            {"role": "user", "content": prompt}
        ]
        
        try:
            doc = self.llm_client._call_with_fallback(messages, temperature=0.2, max_tokens=500)
            
            # Clean up the response
            doc = doc.strip()
            
            # Remove markdown code fences if present
            if '```' in doc:
                # Remove opening fence
                doc = re.sub(r'^```\w*\n?', '', doc)
                # Remove closing fence
                doc = re.sub(r'\n?```$', '', doc)
            
            # Remove any code that was accidentally included
            # Stop at first line that looks like code (class, struct, void, int, etc.)
            lines = doc.split('\n')
            comment_lines = []
            for line in lines:
                stripped = line.strip()
                # Stop if we hit actual code
                if stripped and not stripped.startswith('///') and not stripped.startswith('/**') and not stripped.startswith('*'):
                    # Check if it's code (starts with keywords)
                    if any(stripped.startswith(kw) for kw in ['class ', 'struct ', 'void ', 'int ', 'bool ', 'size_t ', 'const ', 'virtual ', 'public:', 'private:', 'protected:', '{']):
                        break
                comment_lines.append(line)
            
            doc = '\n'.join(comment_lines).strip()
            
            return doc
        except Exception as e:
            return f"/// TODO: Add documentation (error: {e})"
    
    def fix_file(self, file_content: str, validation_result: Dict) -> str:
        """Fix all documentation issues in the file"""
        lines = file_content.split('\n')
        
        # Separate issues into missing docs and style issues
        missing_doc_issues = [
            issue for issue in validation_result['issues']
            if issue['issue_type'] == 'missing_documentation'
        ]
        
        style_issues = [
            issue for issue in validation_result['issues']
            if issue['issue_type'] in ['wrong_style', 'wrong_command', 'wrong_format']
        ]
        
        # Fix style issues first (don't change line count)
        for issue in style_issues:
            lines = self._fix_style_issue(lines, issue)
        
        # For missing documentation, we need to be careful about line numbers
        # Sort by line number in REVERSE order so insertions don't affect later line numbers
        missing_doc_issues.sort(key=lambda x: x['entity']['line'], reverse=True)
        
        for issue in missing_doc_issues:
            entity = issue['entity']
            line_idx = entity['line'] - 1
            
            # Validate line index
            if line_idx < 0 or line_idx >= len(lines):
                continue
            
            # Generate documentation using CURRENT state of file
            current_content = '\n'.join(lines)
            doc = self.fix_entity(entity, current_content)
            
            # Skip if doc is empty or just whitespace
            if not doc or not doc.strip():
                continue
            
            # Get indentation from the target line
            target_line = lines[line_idx]
            indent = len(target_line) - len(target_line.lstrip())
            indent_str = ' ' * indent
            
            # Split documentation into lines and add indentation
            doc_lines = [line.strip() for line in doc.split('\n') if line.strip()]
            
            # Insert documentation lines BEFORE the entity (in reverse to maintain order)
            for doc_line in reversed(doc_lines):
                lines.insert(line_idx, indent_str + doc_line)
        
        return '\n'.join(lines)
    
    def _fix_style_issue(self, lines: List[str], issue: Dict) -> List[str]:
        """Fix a style issue in existing documentation"""
        entity = issue['entity']
        line_idx = entity['line'] - 1
        
        # Find the documentation block above this entity
        doc_start = -1
        doc_end = -1
        
        for i in range(line_idx - 1, max(0, line_idx - 15), -1):
            line = lines[i].strip()
            if line.startswith('/**') or line.startswith('///'):
                doc_start = i
                break
            elif line.startswith('*') or line.startswith('*/'):
                doc_end = i if doc_end == -1 else doc_end
        
        if doc_start == -1:
            return lines
        
        if doc_end == -1:
            doc_end = line_idx - 1
        
        # Fix the documentation block
        for i in range(doc_start, doc_end + 1):
            # Fix @-style to backslash-style
            if issue['issue_type'] == 'wrong_style':
                lines[i] = lines[i].replace('@param', '\\param')
                lines[i] = lines[i].replace('@return', '\\return')
                lines[i] = lines[i].replace('@throw', '\\throw')
                lines[i] = lines[i].replace('@tparam', '\\tparam')
                lines[i] = lines[i].replace('@note', '\\note')
                lines[i] = lines[i].replace('@warning', '\\warning')
            
            # Remove \brief and \details
            elif issue['issue_type'] == 'wrong_command':
                lines[i] = lines[i].replace('\\brief ', '')
                lines[i] = lines[i].replace('\\details ', '')
        
        return lines
