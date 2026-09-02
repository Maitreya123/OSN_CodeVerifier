#!/usr/bin/env python3
"""
Code Verifier - Ensures AI-generated code doesn't modify non-comment content
"""

import re

from tree_sitter import Language, Node, Parser
import tree_sitter_cpp as cpp


class CodeVerifier:
    """Verifies that AI changes only affect comments, not actual code"""

    _parser = Parser(Language(cpp.language()))
    
    @staticmethod
    def strip_comments_and_empty_lines(code: str) -> str:
        """
        Strip all comments and empty lines from C++ code
        Returns only the actual code content
        """
        source = code.encode("utf-8")
        tree = CodeVerifier._parser.parse(source)
        comment_ranges = CodeVerifier._comment_ranges(tree.root_node)

        uncommented = []
        last_end = 0
        for start, end in comment_ranges:
            uncommented.append(source[last_end:start].decode("utf-8"))
            last_end = end
        uncommented.append(source[last_end:].decode("utf-8"))

        return "\n".join(line.strip() for line in "".join(uncommented).splitlines() if line.strip())

    @staticmethod
    def _comment_ranges(node: Node) -> list[tuple[int, int]]:
        """Return source-byte ranges for comments recognized by the C++ parser."""
        ranges = []
        if node.type == "comment":
            ranges.append((node.start_byte, node.end_byte))
        for child in node.children:
            ranges.extend(CodeVerifier._comment_ranges(child))
        return ranges
    
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
