import tempfile
import unittest
from pathlib import Path

from m8agent.db import (
    Document,
    connect,
    init_db,
    replace_doc_chunks,
    retrieve,
    upsert_document,
)


class DbTest(unittest.TestCase):
    def test_retrieve_document_chunks(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "m8.sqlite"
            source_file = Path(tmp) / "manual.txt"
            source_file.write_text("table modulation", encoding="utf-8")
            conn = connect(db_path)
            init_db(conn)
            upsert_document(
                conn,
                Document(
                    document_id="manual",
                    title="Manual",
                    source_type="manual",
                    authority="official",
                    url="https://example.com/manual.pdf",
                    version="test",
                ),
            )
            replace_doc_chunks(
                conn,
                document_id="manual",
                source_type="manual",
                authority="official",
                source_file=source_file,
                chunks=[
                    (
                        "p. 1",
                        "https://example.com/manual.pdf#page=1",
                        "Tables can be used for modulation.",
                    )
                ],
            )
            conn.commit()

            results = retrieve(conn, "table modulation", sources={"manual"})
            conn.close()

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].source_type, "manual")
        self.assertEqual(results[0].authority, "official")
        self.assertEqual(results[0].location, "p. 1")
        self.assertEqual(results[0].citation_url, "https://example.com/manual.pdf#page=1")


if __name__ == "__main__":
    unittest.main()
