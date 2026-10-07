"""Structural regression checks for the API-only Agent Bar boundary.

These intentionally avoid importing the full Flask stack so they can run in a
clean source checkout before Docker dependencies are installed.
"""

import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent


class AgentBarApiContractTests(unittest.TestCase):
    def test_api_exposes_only_read_routes(self):
        api_path = ROOT / "aggregator/blueprints/api.py"
        tree = ast.parse(api_path.read_text(encoding="utf-8"))
        decorators = [
            decorator
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            for decorator in node.decorator_list
        ]
        methods = [
            decorator.func.attr
            for decorator in decorators
            if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute)
        ]
        self.assertTrue(methods)
        self.assertEqual(set(methods), {"get"})
        self.assertIn("@api.after_request", api_path.read_text(encoding="utf-8"))

    def test_api_does_not_expose_scraped_article_content(self):
        source = (ROOT / "aggregator/blueprints/api.py").read_text(encoding="utf-8")
        self.assertNotIn('"content": article.content', source)
        self.assertNotIn('"content": result.', source)

    def test_headline_summary_exposes_the_priority_baseline(self):
        source = (ROOT / "aggregator/blueprints/api.py").read_text(encoding="utf-8")
        self.assertIn('"priority": 10', source)

    def test_app_registers_api_without_web_blueprints(self):
        source = (ROOT / "aggregator/__init__.py").read_text(encoding="utf-8")
        self.assertIn("app.register_blueprint(api)", source)
        self.assertNotIn("app.register_blueprint(public)", source)
        self.assertNotIn("app.register_blueprint(admin", source)
        self.assertNotIn("app.register_blueprint(auth", source)


if __name__ == "__main__":
    unittest.main()
