"""Regression tests for C++ declaration extraction."""

import unittest

from cpp_header_parser import CppHeaderParser
from code_verifier import CodeVerifier
from doxygen_validator import DoxygenValidator


class CppHeaderParserTests(unittest.TestCase):
    def setUp(self) -> None:
        self.parser = CppHeaderParser()

    def test_ignores_calls_and_local_statements(self) -> None:
        source = """
class Range
{
public:
  bool IsAllowed(int value)
  {
    std::stringstream output;
    output << value;
    return output.str().empty() || values_.emplace_back(value), true;
  }

private:
  std::vector<int> values_;
};
"""

        entities = self.parser.parse(source)
        names = {entity["name"] for entity in entities}

        self.assertIn("Range", names)
        self.assertIn("IsAllowed", names)
        self.assertIn("values_", names)
        self.assertNotIn("str", names)
        self.assertNotIn("empty", names)
        self.assertNotIn("emplace_back", names)

    def test_tracks_templates_access_and_header_only_definitions(self) -> None:
        source = """
template <typename T>
class Container
{
public:
  explicit Container(T value) : value_(value) {}

  static Container Make(T value)
  {
    return Container(value);
  }

protected:
  T value_;
};

extern int global_count;
inline constexpr int max_count = 4;
static void LocalOnly();
"""

        entities = self.parser.parse(source)
        by_name = {entity["name"]: entity for entity in entities}
        class_entity = next(
            entity for entity in entities if entity["type"] == "class" and entity["name"] == "Container"
        )

        self.assertEqual(class_entity["line"], 2)
        constructor = next(entity for entity in entities if entity.get("is_constructor"))
        self.assertTrue(constructor["is_constructor"])
        self.assertEqual(constructor["parameters"], ["value"])
        self.assertTrue(by_name["Make"]["is_static"])
        self.assertEqual(by_name["value_"]["access"], "protected")
        self.assertEqual(by_name["global_count"]["type"], "variable")
        self.assertEqual(by_name["max_count"]["type"], "variable")
        self.assertNotIn("LocalOnly", by_name)

    def test_code_verifier_allows_trailing_enum_documentation(self) -> None:
        original = "enum class Mode\n{\n  FAST,\n};\n"
        documented = "enum class Mode\n{\n  FAST, ///< Fast execution mode.\n};\n"

        valid, message = CodeVerifier.verify_code_unchanged(original, documented)

        self.assertTrue(valid, message)

    def test_code_verifier_preserves_comment_markers_in_strings(self) -> None:
        original = 'const char* url = "https://open-sn.github.io";\n'
        documented = '/// Documentation URL.\nconst char* url = "https://open-sn.github.io";\n'

        valid, message = CodeVerifier.verify_code_unchanged(original, documented)

        self.assertTrue(valid, message)

    def test_fixer_revalidates_locations_after_insertions(self) -> None:
        source = """
class Widget
{
public:
  /// Returns the stored value.
  int GetValue() const;
  void SetValue(int value);

private:
  int value_;
};
"""
        validator = object.__new__(DoxygenValidator)
        validator.cpp_parser = CppHeaderParser()
        validator.verify_code = True

        def generate_documentation(entity, _content):
            if entity["type"] == "class":
                return "/// Widget value container."
            if entity["type"] == "member_variable":
                return "/// Stored value."
            return "/// Get the stored value."

        validator.fix_entity = generate_documentation
        fixed = validator.fix_file(source)

        self.assertIn("  /// Get the stored value.\n  int GetValue() const;", fixed)
        self.assertIn("  /// Get the stored value.\n  void SetValue(int value);", fixed)
        self.assertIn("  /// Stored value.\n  int value_;", fixed)
        valid, message = CodeVerifier.verify_code_unchanged(source, fixed)
        self.assertTrue(valid, message)


if __name__ == "__main__":
    unittest.main()
