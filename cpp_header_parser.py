"""C++ header declaration extraction backed by Tree-sitter."""

import re
from typing import Dict, List, Optional

from tree_sitter import Language, Node, Parser
import tree_sitter_cpp as cpp


class CppHeaderParser:
    """Extract documentable declarations without inspecting function bodies."""

    def __init__(self) -> None:
        self.parser = Parser(Language(cpp.language()))
        self.source = b""

    def parse(self, content: str) -> List[Dict]:
        """Return documentable C++ header declarations in source order."""
        self.source = content.encode("utf-8")
        tree = self.parser.parse(self.source)
        entities: List[Dict] = []
        self._visit_container(tree.root_node, entities, None, "public")
        return sorted(entities, key=lambda entity: entity["line"])

    def _visit_container(
        self,
        node: Node,
        entities: List[Dict],
        class_name: Optional[str],
        access: str,
        declaration_start: Optional[Node] = None,
    ) -> None:
        if node.type == "template_declaration":
            target = node.named_children[-1] if node.named_children else None
            if target is not None:
                self._visit_container(target, entities, class_name, access, node)
            return

        if node.type == "namespace_definition":
            if not any(child.type == "namespace_identifier" for child in node.named_children):
                return
            for child in node.named_children:
                self._visit_container(child, entities, None, "public", declaration_start)
            return

        if node.type in {"class_specifier", "struct_specifier", "union_specifier"}:
            self._visit_class(node, entities, declaration_start)
            return

        if node.type == "enum_specifier":
            self._add_enum(node, entities, class_name, access, declaration_start)
            return

        if node.type in {"function_definition", "declaration", "field_declaration"}:
            self._visit_declaration(node, entities, class_name, access, declaration_start)
            return

        for child in node.named_children:
            self._visit_container(child, entities, class_name, access, declaration_start)

    def _visit_class(self, node: Node, entities: List[Dict], declaration_start: Optional[Node]) -> None:
        body = next((child for child in node.named_children if child.type == "field_declaration_list"), None)
        name_node = next(
            (child for child in node.named_children if child.type in {"type_identifier", "identifier"}), None
        )
        if body is None or name_node is None:
            return

        class_name = self._text(name_node)
        kind = node.type.removesuffix("_specifier")
        self._add_entity(
            entities,
            entity_type="class",
            name=class_name,
            node=node,
            declaration_start=declaration_start,
            access="public",
            cpp_kind=kind,
        )

        current_access = "public" if kind in {"struct", "union"} else "private"
        for child in body.named_children:
            if child.type == "access_specifier":
                current_access = self._text(child)
                continue
            self._visit_container(child, entities, class_name, current_access)

    def _visit_declaration(
        self,
        node: Node,
        entities: List[Dict],
        class_name: Optional[str],
        access: str,
        declaration_start: Optional[Node],
    ) -> None:
        nested_class = next(
            (
                self._find_descendant(node, node_type)
                for node_type in ("class_specifier", "struct_specifier", "union_specifier")
                if self._find_descendant(node, node_type) is not None
            ),
            None,
        )
        if nested_class is not None:
            self._visit_class(nested_class, entities, declaration_start)
            return

        enum_specifier = self._find_descendant(node, "enum_specifier")
        if enum_specifier is not None:
            self._add_enum(enum_specifier, entities, class_name, access, declaration_start)
            return

        function_declarator = self._find_descendant(node, "function_declarator")
        if function_declarator is not None:
            name_node = function_declarator.child_by_field_name("declarator")
            if name_node is not None and name_node.type == "parenthesized_declarator":
                self._add_variable(node, entities, class_name, access, declaration_start)
                return
            name = self._declarator_name(name_node)
            if name:
                self._add_function(
                    node, entities, class_name, access, declaration_start, name, function_declarator
                )
            return

        self._add_variable(node, entities, class_name, access, declaration_start)

    def _add_function(
        self,
        node: Node,
        entities: List[Dict],
        class_name: Optional[str],
        access: str,
        declaration_start: Optional[Node],
        name: str,
        function_declarator: Node,
    ) -> None:
        text = self._text(node)
        if class_name is None and re.search(r"\bstatic\b", text):
            return
        is_constructor = class_name is not None and name == class_name
        is_destructor = name.startswith("~")
        parameters = self._parameters(function_declarator)
        is_default_constructor = is_constructor and (not parameters or "= default" in text or "= delete" in text)
        is_copy_or_move = is_constructor and any(class_name in parameter and "&" in parameter for parameter in parameters)
        is_trivial = self._is_trivial_accessor(node)

        if is_destructor or is_default_constructor or is_copy_or_move or is_trivial:
            return

        self._add_entity(
            entities,
            entity_type="method" if class_name else "function",
            name=name,
            node=node,
            declaration_start=declaration_start,
            access=access,
            class_name=class_name,
            is_constructor=is_constructor,
            is_static=bool(re.search(r"\bstatic\b", text)),
            parameters=parameters,
        )

    def _add_variable(
        self,
        node: Node,
        entities: List[Dict],
        class_name: Optional[str],
        access: str,
        declaration_start: Optional[Node],
    ) -> None:
        if node.type not in {"declaration", "field_declaration"}:
            return
        text = self._text(node)
        if text.lstrip().startswith(("using ", "typedef ", "friend ")):
            return
        name_node = self._find_declarator_name(node)
        if name_node is None:
            return
        entity_type = "member_variable" if class_name else "variable"
        if not class_name and not re.search(r"\b(extern|constexpr)\b", text):
            return
        self._add_entity(
            entities,
            entity_type=entity_type,
            name=self._text(name_node),
            node=node,
            declaration_start=declaration_start,
            access=access,
            class_name=class_name,
            is_static=bool(re.search(r"\bstatic\b", text)),
        )

    def _add_enum(
        self,
        node: Node,
        entities: List[Dict],
        class_name: Optional[str],
        access: str,
        declaration_start: Optional[Node],
    ) -> None:
        name_node = next(
            (child for child in node.named_children if child.type in {"type_identifier", "identifier"}), None
        )
        if name_node is None:
            return
        self._add_entity(
            entities,
            entity_type="enum",
            name=self._text(name_node),
            node=node,
            declaration_start=declaration_start,
            access=access,
            class_name=class_name,
        )

    def _add_entity(self, entities: List[Dict], entity_type: str, name: str, node: Node, **metadata) -> None:
        declaration_start = metadata.pop("declaration_start", None) or node
        entity = {
            "type": entity_type,
            "name": name,
            "line": declaration_start.start_point.row + 1,
            "content": self._text(node).splitlines()[0],
            **metadata,
        }
        if entity.get("class_name"):
            entity["class"] = entity.pop("class_name")
        entities.append(entity)

    def _parameters(self, function_declarator: Node) -> List[str]:
        parameter_list = function_declarator.child_by_field_name("parameters")
        if parameter_list is None:
            return []
        names = []
        for parameter in parameter_list.named_children:
            name_node = self._find_declarator_name(parameter)
            if name_node is not None:
                names.append(self._text(name_node))
        return names

    def _is_trivial_accessor(self, node: Node) -> bool:
        body = next((child for child in node.named_children if child.type == "compound_statement"), None)
        if body is None:
            return False
        statements = body.named_children
        if len(statements) != 1:
            return False
        statement = statements[0]
        text = self._text(statement)
        if statement.type == "return_statement":
            return bool(re.fullmatch(r"return\s+[*&]?[A-Za-z_]\w*_\s*;", text))
        return bool(re.fullmatch(r"[A-Za-z_]\w*_\s*=\s*[A-Za-z_]\w*\s*;", text))

    def _find_declarator_name(self, node: Node) -> Optional[Node]:
        for child in node.named_children:
            if child.type in {"identifier", "field_identifier"}:
                return child
            found = self._find_declarator_name(child)
            if found is not None:
                return found
        return None

    def _declarator_name(self, node: Optional[Node]) -> str:
        if node is None:
            return ""
        if node.type in {"identifier", "field_identifier", "destructor_name"}:
            return self._text(node)
        name_node = self._find_declarator_name(node)
        return self._text(name_node) if name_node is not None else ""

    def _find_descendant(self, node: Node, node_type: str) -> Optional[Node]:
        if node.type == node_type:
            return node
        for child in node.named_children:
            found = self._find_descendant(child, node_type)
            if found is not None:
                return found
        return None

    def _text(self, node: Node) -> str:
        return self.source[node.start_byte : node.end_byte].decode("utf-8")
