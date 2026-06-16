import unittest

from scripts.collect_news_multi import parse_locale_spec


class CollectNewsMultiTests(unittest.TestCase):
    def test_parse_locale_spec_defaults_language_to_en(self):
        self.assertEqual(parse_locale_spec("US"), ("US", "en"))

    def test_parse_locale_spec_accepts_language_pair(self):
        self.assertEqual(parse_locale_spec("JP:ja"), ("JP", "ja"))


if __name__ == "__main__":
    unittest.main()
