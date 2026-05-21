import tempfile
import unittest
from pathlib import Path

from m8agent.cli import collect_ingest_urls, parse_sources
from m8agent.youtube import DEFAULT_CHANNEL_URL


class CliTest(unittest.TestCase):
    def test_collect_ingest_urls_defaults_to_dirtywave_channel(self):
        urls = collect_ingest_urls(channel_urls=None, source_urls=None, urls_file=None)

        self.assertEqual(urls, [DEFAULT_CHANNEL_URL])

    def test_collect_ingest_urls_combines_file_and_flags(self):
        with tempfile.TemporaryDirectory() as tmp:
            urls_file = Path(tmp) / "sources.txt"
            urls_file.write_text(
                "\n".join(
                    [
                        "# comments are ignored",
                        "https://www.youtube.com/playlist?list=abc",
                        "",
                        "https://www.youtube.com/watch?v=video1",
                    ]
                ),
                encoding="utf-8",
            )

            urls = collect_ingest_urls(
                channel_urls=["https://www.youtube.com/@Dirtywave/videos"],
                source_urls=[
                    "https://www.youtube.com/watch?v=video1",
                    "https://www.youtube.com/watch?v=video2",
                ],
                urls_file=urls_file,
            )

        self.assertEqual(
            urls,
            [
                "https://www.youtube.com/@Dirtywave/videos",
                "https://www.youtube.com/watch?v=video1",
                "https://www.youtube.com/watch?v=video2",
                "https://www.youtube.com/playlist?list=abc",
            ],
        )

    def test_parse_sources_accepts_companion(self):
        self.assertEqual(parse_sources("manual,companion"), {"manual", "companion"})


if __name__ == "__main__":
    unittest.main()
