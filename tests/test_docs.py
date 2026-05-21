import tempfile
import unittest
from pathlib import Path

from m8agent.docs import extract_companion_chapter_urls, parse_companion_html


class DocsTest(unittest.TestCase):
    def test_extract_companion_chapter_urls(self):
        html = """
        <a href="Introduction.html">Introduction</a>
        <a href="Working_with_tables.html#part">Tables</a>
        <a href="https://example.com/elsewhere.html">External</a>
        <a href="Introduction.html">Duplicate</a>
        """

        urls = extract_companion_chapter_urls(
            html,
            "https://cs.uwaterloo.ca/~plragde/flaneries/TM8C/",
        )

        self.assertEqual(
            urls,
            [
                "https://cs.uwaterloo.ca/~plragde/flaneries/TM8C/Introduction.html",
                "https://cs.uwaterloo.ca/~plragde/flaneries/TM8C/Working_with_tables.html",
            ],
        )

    def test_parse_companion_html_uses_heading_and_anchor(self):
        html = """
        <html><body>
          <div class="tocview"><p>This should not be indexed.</p></div>
          <div class="main">
            <h2><a name="part_tables"></a>Working with tables</h2>
            <p>Tables can create arpeggios and modulation.</p>
            <h3><a name="part_lfos"></a>LFOs and Envelopes</h3>
            <ul><li>Use table tick to shape movement.</li></ul>
          </div>
        </body></html>
        """

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "Working_with_tables.html"
            path.write_text(html, encoding="utf-8")
            chunks = parse_companion_html(
                path,
                "https://cs.uwaterloo.ca/~plragde/flaneries/TM8C/Working_with_tables.html",
            )

        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0][0], "Working with tables")
        self.assertEqual(
            chunks[0][1],
            "https://cs.uwaterloo.ca/~plragde/flaneries/TM8C/Working_with_tables.html#part_tables",
        )
        self.assertEqual(chunks[1][0], "LFOs and Envelopes")
        self.assertIn("table tick", chunks[1][2])


if __name__ == "__main__":
    unittest.main()
