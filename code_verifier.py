#!/usr/bin/env python3
"""
Code Verifier - Ensures AI-generated code doesn't modify non-comment content
"""

import re


class CodeVerifier:
    """Verifies that AI changes only affect comments, not actual code"""
    
    @staticmethod
    def strip_comments_and_empty_lines(code: str) -> str:
        """
        Strip all comments and empty lines from C++ code
        Returns only the actual code content
        """
        lines = code.split('\n')
        stripped_lines = []
        
        in_multiline_comment = False
        
        for line in lines:
            # Handle multi-line comments
            if '/*' in line:
                # Start of multi-line comment
                before_comment = line[:line.index('/*')]
                if '*/' in line[line.index('/*'):]:
                    # Comment ends on same line
                    after_comment = line[line.index('*/') + 2:]
                    line = before_comment + after_comment
                else:
                    # Comment continues
                    in_multiline_comment = True
                    line = before_comment
            
            if in_multiline_comment:
                if '*/' in line:
                    # End of multi-line comment
                    line = line[line.index('*/') + 2:]
                    in_multiline_comment = False
                else:
                    # Still in comment, skip line
                    continue
            
            # Remove single-line comments (// and ///)
            if '//' in line:
                line = line[:line.index('//')]
            
            # Strip whitespace
            line = line.strip()
            
            # Add non-empty lines
            if line:
                stripped_lines.append(line)
        
        return '\n'.join(stripped_lines)
    
    @staticmethod
    def verify_code_unchanged(original: str, modified: str) -> tuple[bool, str]:
        """
        Verify that only comments were changed, not actual code
        
        Returns:
            (is_valid, message) - True if code is unchanged, False otherwise
        """
        # Strip comments and empty lines from both
        original_code = CodeVerifier.strip_comments_and_empty_lines(original)
        modified_code = CodeVerifier.strip_comments_and_empty_lines(modified)
        
        # Compare
        if original_code == modified_code:
            return True, "✅ Verification passed: Only comments were modified"
        else:
            # Find differences
            orig_lines = original_code.split('\n')
            mod_lines = modified_code.split('\n')
            
            differences = []
            max_lines = max(len(orig_lines), len(mod_lines))
            
            for i in range(max_lines):
                orig_line = orig_lines[i] if i < len(orig_lines) else "[MISSING]"
                mod_line = mod_lines[i] if i < len(mod_lines) else "[MISSING]"
                
                if orig_line != mod_line:
                    differences.append(f"Line {i+1}:")
                    differences.append(f"  Original: {orig_line}")
                    differences.append(f"  Modified: {mod_line}")
                    
                    if len(differences) >= 20:  # Limit output
                        differences.append("... (more differences)")
                        break
            
            message = "❌ Verification failed: Code was modified\n\n" + "\n".join(differences)
            return False, message


if __name__ == "__main__":
    # Test the verifier
    print("Testing Code Verifier...")
    print("=" * 80)
    
    # Test 1: Only comments changed (should pass)
    original1 = """
class Test {
public:
  void Method();
private:
  int value_;
};
"""
    
    modified1 = """
/// Test class.
class Test {
public:
  /// Method description.
  void Method();
private:
  /// Value member.
  int value_;
};
"""
    
    is_valid, message = CodeVerifier.verify_code_unchanged(original1, modified1)
    print("Test 1: Only comments added")
    print(message)
    print()
    
    # Test 2: Code changed (should fail)
    original2 = """
class Test {
public:
  void Method();
};
"""
    
    modified2 = """
/// Test class.
class Test {
public:
  /// Method description.
  void Method(int x);  // Added parameter!
};
"""
    
    is_valid, message = CodeVerifier.verify_code_unchanged(original2, modified2)
    print("Test 2: Code modified (added parameter)")
    print(message)
    print()
