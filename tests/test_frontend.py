"""Lexer + parser tests."""
import unittest

from regexlab.lexer import ParseError, tokenize
from regexlab.parser import Node, ast_lines, ast_size, parse


class LexerTests(unittest.TestCase):
    def test_token_types(self):
        types = [t.type for t in tokenize("(a|b)*c+d?")]
        self.assertEqual(types, ["LPAREN", "CHAR", "UNION", "CHAR", "RPAREN", "STAR",
                                 "CHAR", "PLUS", "CHAR", "QMARK"])

    def test_escape_makes_literal(self):
        toks = tokenize(r"\*\|\\")
        self.assertTrue(all(t.type == "CHAR" for t in toks))
        self.assertEqual([t.value for t in toks], ["*", "|", "\\"])

    def test_positions(self):
        self.assertEqual([t.pos for t in tokenize("ab|c")], [0, 1, 2, 3])

    def test_dangling_backslash(self):
        with self.assertRaises(ParseError):
            tokenize("ab\\")


class ParserTests(unittest.TestCase):
    def test_precedence_union_lowest(self):
        ast = parse("ab|c")
        self.assertEqual(ast.kind, "alt")
        self.assertEqual([k.kind for k in ast.kids], ["cat", "chr"])

    def test_repetition_binds_tightest(self):
        ast = parse("ab*")
        self.assertEqual(ast.kind, "cat")
        self.assertEqual([k.kind for k in ast.kids], ["chr", "star"])

    def test_stacked_operators(self):
        self.assertEqual(parse("a*?").kind, "opt")

    def test_empty_alternative_is_epsilon(self):
        ast = parse("a|")
        self.assertEqual(ast.kids[1], Node("eps"))

    def test_empty_group(self):
        self.assertEqual(parse("()"), Node("eps"))

    def test_errors(self):
        cases = {"(a|": "Missing", "a)": "Unmatched", "*a": "Nothing to repeat",
                 "a|*": "Nothing to repeat", "(*a)": "Nothing to repeat"}
        for src, msg in cases.items():
            with self.subTest(src=src):
                with self.assertRaises(ParseError) as cm:
                    parse(src)
                self.assertIn(msg, str(cm.exception))

    def test_error_positions(self):
        with self.assertRaises(ParseError) as cm:
            parse("ab)")
        self.assertEqual(cm.exception.pos, 2)

    def test_tree_printer_and_size(self):
        ast = parse("a|b")
        self.assertEqual(ast_size(ast), 3)
        self.assertEqual(ast_lines(ast)[0], "|  union")
        self.assertEqual(len(ast_lines(ast)), 3)


if __name__ == "__main__":
    unittest.main()
