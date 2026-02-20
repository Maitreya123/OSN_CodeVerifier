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
        class_brace_count = 0
        access_level = 'private'  # default for class
        in_function_body = False
        function_brace_depth = 0
        prev_was_method_decl = False  # Track if previous line was a method declaration
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # Skip empty lines, preprocessor directives, comments, and license headers
            if not stripped or stripped.startswith('#') or stripped.startswith('//'):
                continue
            
            # Skip namespace declarations
            if stripped.startswith('namespace'):
                continue
            
            # Skip type aliases (using/typedef) - per guidelines
            if stripped.startswith('using ') or stripped.startswith('typedef '):
                continue
            
            # Track class/struct scope
            if re.match(r'(class|struct)\s+\w+', stripped) and not stripped.endswith(';'):
                match = re.search(r'(class|struct)\s+(\w+)', stripped)
                if match:
                    in_class = True
                    class_name = match.group(2)
                    class_brace_count = 0
                    access_level = 'private'  # Reset access level for new class
                    entities.append({
                        'type': 'class',
                        'name': class_name,
                        'line': i + 1,
                        'content': line,
                        'access': 'public'
                    })
                    # Count braces on the class declaration line
                    class_brace_count += stripped.count('{') - stripped.count('}')
                    continue
            
            # Track braces for class scope
            if in_class:
                class_brace_count += stripped.count('{') - stripped.count('}')
                
                # Exit class when braces balance
                if class_brace_count <= 0:
                    in_class = False
                    class_name = None
                    access_level = 'private'
                    continue
            
            # Skip if not in class
            if not in_class:
                continue
            
            # Track access level
            if stripped in ['public:', 'protected:', 'private:']:
                access_level = stripped.rstrip(':')
                continue
            
            # Track function body scope (to skip documentation inside functions)
            if in_function_body:
                function_brace_depth += stripped.count('{') - stripped.count('}')
                if function_brace_depth <= 0:
                    in_function_body = False
                    function_brace_depth = 0
                continue
            
            # Check if this line is just an opening brace (start of function body)
            # But NOT if it's the class body opening brace
            if stripped == '{' and prev_was_method_decl:
                in_function_body = True
                function_brace_depth = 1
                prev_was_method_decl = False
                continue
            
            # Reset the flag if we see any other line
            if stripped != '{':
                prev_was_method_decl = False
            
            # Member variables (but not method calls or inside function bodies)
            if ';' in stripped and '(' not in stripped:
                # Check if it's a variable declaration
                if re.search(r'\b(const\s+)?(static\s+)?\w+[\*&\s<>]+\w+\s*[;=]', stripped):
                    # Skip if it's inside a method body or constructor initializer
                    if not any(x in stripped for x in ['return', 'if', 'for', 'while']):
                        entities.append({
                            'type': 'member_variable',
                            'class': class_name,
                            'line': i + 1,
                            'content': line,
                            'access': access_level
                        })
            
            # Methods/functions
            if '(' in stripped and ')' in stripped:
                # Skip constructor initializer lists
                if ':' in stripped and '(' in stripped and i > 0:
                    prev_line = lines[i-1].strip()
                    if ')' in prev_line:  # This is an initializer list
                        continue
                
                # Check if it's a method declaration/definition
                is_declaration = ';' in stripped or 'virtual' in stripped or '= 0' in stripped
                is_definition = '{' in stripped and not ';' in stripped
                
                if is_declaration or is_definition:
                    # Extract method name and check if it's a constructor/destructor
                    method_match = re.search(r'(\w+)\s*\([^)]*\)', stripped)
                    if method_match:
                        method_name = method_match.group(1)
                        
                        # Check if it's a constructor (same name as class)
                        is_constructor = (method_name == class_name)
                        
                        # Check if it's a destructor
                        is_destructor = '~' in stripped
                        
                        # Check if it's a default constructor or copy/move constructor (should NOT be documented)
                        is_default_ctor = False
                        is_copy_move_ctor = False
                        
                        if is_constructor:
                            # Check for = default or = delete
                            if '= default' in stripped or '= delete' in stripped:
                                is_default_ctor = True
                            else:
                                param_section = re.search(r'\(([^)]*)\)', stripped)
                                if param_section:
                                    params = param_section.group(1).strip()
                                    # Default constructor: no params
                                    if not params:
                                        is_default_ctor = True
                                    # Copy constructor: ClassName(const ClassName&)
                                    elif f'const {class_name}&' in params or f'{class_name} const&' in params:
                                        is_copy_move_ctor = True
                                    # Move constructor: ClassName(ClassName&&)
                                    elif f'{class_name}&&' in params:
                                        is_copy_move_ctor = True
                        
                        # Check if it's a trivial getter/setter
                        is_trivial = False
                        if '{' in stripped and '}' in stripped:
                            # Single-line getter: returns member variable
                            if 'return' in stripped and re.search(r'return\s+[\*&]?\w+_', stripped):
                                is_trivial = True
                            # Single-line setter: assigns to member variable
                            elif '=' in stripped and re.search(r'\w+_\s*=', stripped):
                                is_trivial = True
                        
                        # Track function body BEFORE filtering (so we skip content inside ALL functions)
                        if is_definition and not is_declaration:
                            in_function_body = True
                            function_brace_depth = stripped.count('{') - stripped.count('}')
                        
                        # If this is a declaration without {, mark that next { might be function body
                        if is_declaration and not is_definition and not ';' in stripped:
                            prev_was_method_decl = True
                        
                        # Only add if not a default constructor, copy/move constructor, destructor, or trivial getter/setter
                        if not is_default_ctor and not is_copy_move_ctor and not is_destructor and not is_trivial:
                            entities.append({
                                'type': 'method',
                                'class': class_name,
                                'name': method_name,
                                'line': i + 1,
                                'content': line,
                                'access': access_level,
                                'is_constructor': is_constructor,
                                'is_definition': is_definition and not is_declaration
                            })        
        return entities
    
    def _validate_entity(self, entity: Dict, lines: List[str]) -> List[Dict]:
        """Validate a single entity for Doxygen compliance"""
        issues = []
        line_idx = entity['line'] - 1
        
        # Check for documentation above the entity
        has_doc = False
        doc_lines = []
        doc_start_line = -1
        
        # Look backwards for documentation (up to 15 lines)
        for i in range(line_idx - 1, max(0, line_idx - 15), -1):
            line = lines[i].strip()
            
            # Found Doxygen comment
            if line.startswith('///') or line.startswith('/**') or (line.startswith('*') and not line.startswith('*/')):
                has_doc = True
                doc_lines.insert(0, line)
                doc_start_line = i
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
            # Skip if this is a function definition (documentation should be at declaration only)
            if entity.get('is_definition', False):
                # Flag as error if documentation is present at definition
                if has_doc:
                    issues.append({
                        'entity': entity,
                        'issue_type': 'wrong_location',
                        'severity': 'error',
                        'message': 'Documentation should be at declaration in header, not at definition'
                    })
                return issues
            
            # Public methods need documentation (already filtered out trivial getters/setters and destructors in parser)
            if entity.get('access') == 'public':
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
            if re.search(r'@(param|return|throw|tparam|note|warning|brief)', doc_text):
                issues.append({
                    'entity': entity,
                    'issue_type': 'wrong_style',
                    'severity': 'error',
                    'message': 'Use backslash-style commands (\\param, \\return, \\note) not @-style (@param, @return, @note, @brief)'
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
            
            # Validate method documentation starts with verb in base form
            if entity['type'] == 'method' and not entity.get('is_constructor', False):
                # Extract the brief description (first sentence or first line after ///)
                brief = ''
                for line in doc_lines:
                    if line.startswith('///'):
                        brief = line.replace('///', '').strip()
                        break
                    elif line.startswith('/**'):
                        brief = line.replace('/**', '').strip()
                        break
                    elif line.startswith('*') and not line.startswith('*/'):
                        text = line.replace('*', '').strip()
                        if text and not text.startswith('\\param') and not text.startswith('\\return'):
                            brief = text
                            break
                
                # Check if brief starts with a verb in base form
                if brief:
                    first_word = brief.split()[0] if brief.split() else ''
                    first_word_lower = first_word.lower()
                    
                    # Check if it starts with common non-verb patterns
                    bad_patterns = ['this', 'the', 'a', 'an', 'method', 'function', 'given']
                    if first_word_lower in bad_patterns:
                        issues.append({
                            'entity': entity,
                            'issue_type': 'wrong_brief_style',
                            'severity': 'warning',
                            'message': 'Method brief should start with verb in base form (e.g., "Get", "Set", "Build", "Initialize")'
                        })
                    # Check if verb ends with 's' or 'es' (wrong form)
                    # Common verbs that should be in base form
                    elif first_word_lower.endswith('s') and len(first_word) > 2:
                        # Check if it's likely a verb in wrong form (not a noun like "class")
                        # Common verb patterns: Sets, Gets, Returns, Creates, Builds, Checks, Counts, etc.
                        verb_indicators = ['set', 'get', 'return', 'create', 'build', 'check', 'count', 
                                         'make', 'find', 'add', 'remove', 'update', 'compute', 'calculate',
                                         'initialize', 'clear', 'reset', 'validate', 'process']
                        base_form = first_word_lower.rstrip('s')
                        # Handle 'es' ending (e.g., "Creates" → "Create")
                        if base_form.endswith('e'):
                            suggested_form = first_word.rstrip('s')
                        else:
                            suggested_form = first_word.rstrip('s').rstrip('e').capitalize()
                            if not suggested_form:
                                suggested_form = first_word.rstrip('s').capitalize()
                        
                        if base_form.rstrip('e') in verb_indicators or base_form in verb_indicators:
                            issues.append({
                                'entity': entity,
                                'issue_type': 'wrong_brief_style',
                                'severity': 'warning',
                                'message': f'Method brief should use base form verb "{suggested_form}" not "{first_word}"'
                            })
            
            # Check for empty lines between \param entries (should be compact)
            if '\\param' in doc_text:
                param_lines = [i for i, line in enumerate(doc_lines) if '\\param' in line]
                for i in range(len(param_lines) - 1):
                    if param_lines[i+1] - param_lines[i] > 1:
                        # Check if there's an empty line between params
                        between_lines = doc_lines[param_lines[i]+1:param_lines[i+1]]
                        if any(line.strip() in ['*', ''] for line in between_lines):
                            issues.append({
                                'entity': entity,
                                'issue_type': 'wrong_format',
                                'severity': 'warning',
                                'message': 'Remove empty lines between \\param entries'
                            })
                            break
        
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
        
        # Determine entity-specific instructions
        entity_type = entity['type']
        is_constructor = entity.get('is_constructor', False)
        
        # Build entity-specific guidance
        if entity_type == 'class':
            entity_guidance = """
ENTITY TYPE: Class
STYLE: Use /// for single-line noun phrase
PATTERN: "/// [Noun phrase describing what this class represents]."
EXAMPLES FROM angle_set.h:
  - "/// Angles for a given groupset"
RULES:
  - Start with a noun (NOT "Class that..." or "This class...")
  - 3-6 words maximum
  - End with period
  - NO verbs, NO complete sentences
  - NEVER use \\brief or @brief
"""
        elif entity_type == 'method':
            if is_constructor:
                entity_guidance = """
ENTITY TYPE: Constructor
STYLE: Use /** */ multi-line with \\param for each parameter
PATTERN:
  /**
   * [Verb phrase describing what constructor does].
   * \\param param1 [Brief description].
   * \\param param2 [Brief description].
   */
EXAMPLES FROM angle_set.h:
  /**
   * Construct an AngleSet.
   * \\param id Unique id of the angleset.
   * \\param num_groups Number of energy groups in the groupset.
   * \\param spds Associated SPDS.
   */
RULES:
  - Brief: Start with verb in base form (Construct, Initialize, Create, Build)
  - Each \\param on separate line, NO empty lines between params
  - Param descriptions: noun phrases, brief (3-6 words)
  - NO @param, use \\param
  - NEVER use \\brief or @brief - just write the description directly
"""
            else:
                entity_guidance = """
ENTITY TYPE: Method
STYLE: Use /// for single-line verb phrase (or /** */ if has parameters)
PATTERN: "/// [Verb in base form] [object]."
EXAMPLES FROM angle_set.h:
  - "/// Get the number of angles in the angleset."
  - "/// Check if the angleset has the given angle index."
  - "/// Return the maximum buffer size from the sweepbuffer."
  - "/// Set the maximum buffer size for the sweepbuffer."
  - "/// Block the current thread until all send buffers are flushed."
RULES:
  - Start with VERB in BASE FORM (Get, Set, Build, Initialize, Check, Return, Add, Remove, Update, etc.)
  - NOT "Gets", "Sets", "Builds" (no 's' or 'es')
  - NOT "This method...", "Method to...", "Function that..."
  - 5-10 words maximum
  - End with period
  - If method has parameters, use /** */ with \\param entries
"""
        elif entity_type == 'member_variable':
            entity_guidance = """
ENTITY TYPE: Member Variable
STYLE: Use /// for single-line noun phrase
PATTERN: "/// [Noun phrase describing what this variable represents]."
EXAMPLES FROM angle_set.h:
  - "/// Unique ID of the angleset."
  - "/// Associated SPDS."
  - "/// Associated FLUDS."
  - "/// Angle indices associated with the angleset."
  - "/// Sweep boundaries."
  - "/// Flag indicating if the angleset has completed its sweep."
RULES:
  - Start with a noun (NOT "Variable that..." or "This variable...")
  - Describe PURPOSE or MEANING, not just the name
  - 3-8 words maximum
  - End with period
  - NO verbs, NO complete sentences
"""
        else:
            entity_guidance = "Follow angle_set.h style exactly."
        
        # Build prompt for LLM with reference example
        prompt = f"""Generate proper Doxygen documentation for this C++ code following OpenSn guidelines.

=== REFERENCE EXAMPLE (angle_set.h) - YOUR STYLE GUIDE ===
Study these EXACT examples from angle_set.h and match their brevity and style:

```cpp
{self.reference_example}
```

{entity_guidance}

=== CODE TO DOCUMENT ===
```cpp
{context}
```

Entity: {entity['type']} at line {entity['line']}
Code: {entity['content']}

IMPORTANT: Document ONLY this specific {entity['type']} on line {entity['line']}.
DO NOT generate documentation for other entities.
Focus ONLY on the entity shown above.

=== CRITICAL FORMATTING RULES ===
1. Return ONLY the comment block (/// or /** */)
2. Do NOT include markdown code fences (```cpp or ```)
3. Do NOT include any explanatory text
4. Do NOT include the code itself
5. Do NOT regenerate or repeat the code being documented
6. For multi-line comments with \\param:
   - NO empty lines between \\param entries
   - Each \\param on its own line
   - Compact format like angle_set.h

=== EXAMPLES OF CORRECT OUTPUT ===

For a class:
/// Geometry manager for mesh operations.

For a simple method:
/// Get the spatial dimension.

For a constructor with params:
/**
 * Construct a GeometryManager.
 * \\param dimension Spatial dimension (1–3).
 * \\param mesh Associated mesh handler.
 */

For a member variable:
/// Spatial dimension of the domain.

Return ONLY the comment!"""

        messages = [
            {
                "role": "system", 
                "content": """You are an expert at writing CONCISE Doxygen documentation for OpenSn (radiation transport code). 

CRITICAL RULES:
1. Classes: Noun phrases ONLY (e.g., "Geometry manager for meshes")
2. Methods: Start with VERB in BASE FORM (Get, Set, Build, Initialize, Check, Return, Add, Remove, Update)
   - NEVER "Gets", "Sets", "Builds" (no 's' or 'es')
   - NEVER "This method...", "Method to...", "Function that..."
3. Variables: Noun phrases describing PURPOSE (e.g., "Spatial dimension of the domain")
4. Constructors: Use /** */ with \\param entries, NO empty lines between params
5. Be EXTREMELY BRIEF: 3-8 words for most descriptions
6. Follow angle_set.h style EXACTLY
7. Return ONLY the comment block, NO code, NO markdown fences, NO explanations
8. NEVER use \\brief or \\details commands - they are FORBIDDEN
9. NEVER use @param, @return, @brief - use \\param, \\return instead"""
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
        
        # Separate issues into different categories
        missing_doc_issues = [
            issue for issue in validation_result['issues']
            if issue['issue_type'] == 'missing_documentation'
        ]
        
        # Issues that need documentation regeneration
        # - wrong_brief_style: wrong verb forms
        # - wrong_command: \brief or \details usage
        # - wrong_style for classes with @brief (will become \brief after fix, still wrong)
        regenerate_issues = [
            issue for issue in validation_result['issues']
            if issue['issue_type'] in ['wrong_brief_style', 'wrong_command'] or
               (issue['issue_type'] == 'wrong_style' and issue['entity']['type'] == 'class' and '@brief' in issue.get('message', ''))
        ]
        
        # Simple style fixes (can be done with find/replace)
        style_issues = [
            issue for issue in validation_result['issues']
            if issue['issue_type'] in ['wrong_style', 'wrong_format'] and issue not in regenerate_issues
        ]
        
        # Fix simple style issues first (don't change line count)
        for issue in style_issues:
            lines = self._fix_style_issue(lines, issue)
        
        # Regenerate documentation for issues that can't be fixed with find/replace
        # Sort by line number in REVERSE order
        regenerate_issues.sort(key=lambda x: x['entity']['line'], reverse=True)
        for issue in regenerate_issues:
            lines = self._regenerate_documentation(lines, issue)
        
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
                lines[i] = lines[i].replace('@brief', '\\brief')
            
            # Remove \brief and \details
            elif issue['issue_type'] == 'wrong_command':
                lines[i] = lines[i].replace('\\brief ', '')
                lines[i] = lines[i].replace('\\details ', '')
        
        # Remove empty lines between \param entries
        if issue['issue_type'] == 'wrong_format' and 'empty lines' in issue.get('message', ''):
            new_lines = []
            in_param_section = False
            for i in range(doc_start, doc_end + 1):
                line = lines[i]
                if '\\param' in line:
                    in_param_section = True
                    new_lines.append(line)
                elif in_param_section:
                    # Skip empty lines in param section
                    if line.strip() in ['*', '']:
                        continue
                    else:
                        new_lines.append(line)
                        if not ('\\param' in line or line.strip().startswith('*')):
                            in_param_section = False
                else:
                    new_lines.append(line)
            
            # Replace the lines
            lines[doc_start:doc_end+1] = new_lines
        
        return lines
    
    def _regenerate_documentation(self, lines: List[str], issue: Dict) -> List[str]:
        """Regenerate documentation for an entity with wrong brief style"""
        entity = issue['entity']
        line_idx = entity['line'] - 1
        
        # Find and remove the old documentation block
        doc_start = -1
        doc_end = -1
        
        for i in range(line_idx - 1, max(0, line_idx - 15), -1):
            line = lines[i].strip()
            if line.startswith('/**'):
                doc_start = i
                # Find the end of this block
                for j in range(i, line_idx):
                    if '*/' in lines[j]:
                        doc_end = j
                        break
                break
            elif line.startswith('///'):
                # Single-line or multi-line /// comments
                doc_start = i
                # Find all consecutive /// lines
                for j in range(i, line_idx):
                    if not lines[j].strip().startswith('///'):
                        doc_end = j - 1
                        break
                else:
                    doc_end = line_idx - 1
                break
        
        if doc_start == -1:
            return lines
        
        # Remove old documentation
        del lines[doc_start:doc_end+1]
        
        # Adjust line index after deletion
        new_line_idx = line_idx - (doc_end - doc_start + 1)
        
        # Update entity line number for regeneration
        entity['line'] = new_line_idx + 1
        
        # Generate new documentation
        current_content = '\n'.join(lines)
        new_doc = self.fix_entity(entity, current_content)
        
        if not new_doc or not new_doc.strip():
            return lines
        
        # Get indentation from the target line
        target_line = lines[new_line_idx]
        indent = len(target_line) - len(target_line.lstrip())
        indent_str = ' ' * indent
        
        # Split documentation into lines and add indentation
        doc_lines = [line.strip() for line in new_doc.split('\n') if line.strip()]
        
        # Insert new documentation lines
        for doc_line in reversed(doc_lines):
            lines.insert(new_line_idx, indent_str + doc_line)
        
        return lines
