import unittest

from m8agent.vtt import chunk_cues, collapse_repeated_sequences, format_timestamp, parse_vtt


class VttTest(unittest.TestCase):
    def test_parse_vtt_and_chunk_cues(self):
        content = """WEBVTT

    00:00:01.000 --> 00:00:03.000
    Hello <c>Dirtywave</c>

    00:00:03.500 --> 00:00:05.000
    M8 tables
    """

        cues = parse_vtt(content)
        self.assertEqual(len(cues), 2)
        self.assertEqual(cues[0].start_ms, 1000)
        self.assertEqual(cues[0].text, "Hello Dirtywave")

        chunks = chunk_cues(cues, max_chars=1000, max_seconds=90)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].text, "Hello Dirtywave M8 tables")

    def test_format_timestamp(self):
        self.assertEqual(format_timestamp(65_000), "01:05")
        self.assertEqual(format_timestamp(3_665_000), "01:01:05")

    def test_collapse_repeated_sequences(self):
        text = "use tables use tables use tables for chords for chords now"
        self.assertEqual(collapse_repeated_sequences(text), "use tables for chords now")


if __name__ == "__main__":
    unittest.main()
