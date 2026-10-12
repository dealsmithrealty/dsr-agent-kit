import importlib, json, os, sys, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))


def fresh(config):
    """Import ytconfig against a throwaway config file (None = no file)."""
    d = tempfile.mkdtemp()
    path = os.path.join(d, "config.json")
    if config is not None:
        json.dump(config, open(path, "w"))
    os.environ["YT_CONFIG"] = path
    os.environ.pop("YT_ROOT", None)
    os.environ.pop("HF", None)
    import ytconfig
    return importlib.reload(ytconfig)


class YtConfigTest(unittest.TestCase):
    def tearDown(self):
        os.environ.pop("YT_CONFIG", None)

    def test_missing_config_is_a_problem(self):
        y = fresh(None)
        self.assertFalse(y.HAS_CONFIG)
        self.assertIn("/video-setup", y.problems()[0])

    def test_defaults_merge_and_workdir(self):
        y = fresh({"creator_name": "A", "workdir": "~/vids", "compliance": {"broker_name": "B"}})
        self.assertEqual(y.problems(), [])
        self.assertEqual(y.ROOT, os.path.expanduser("~/vids"))
        self.assertEqual(y.HF, os.path.join(os.path.expanduser("~/vids"), "node_modules", ".bin", "hyperframes"))
        self.assertEqual(y.CFG["delivery"]["mode"], "local")

    def test_broker_required_when_compliance_on(self):
        y = fresh({"creator_name": "A"})
        self.assertTrue(any("broker_name" in p for p in y.problems()))
        y = fresh({"creator_name": "A", "compliance": {"enabled": False}})
        self.assertEqual(y.problems(), [])

    def test_palette_sub_hex_and_rgba(self):
        y = fresh({"creator_name": "A", "compliance": {"enabled": False},
                   "brand": {"highlight": "#123456", "anchor": "#8F6A10", "punchline": "#ABCDEF"}})
        out = y.palette_sub("a{color:#FFBB00} b{color:#ffbb00} c{box-shadow:0 0 4px rgba(255,187,0,.9)} "
                            "d{color:#8F6A10} e{background:rgba(252, 239, 174, .5)} f{color:#FCEFAE}")
        self.assertNotIn("FFBB00", out.upper())
        self.assertIn("#123456", out)
        self.assertIn("rgba(18,52,86,.9)", out)
        self.assertIn("#8F6A10", out)          # unchanged role stays
        self.assertIn("rgba(171,205,239, .5)", out)
        self.assertIn("#ABCDEF", out)

    def test_palette_sub_rejects_bad_colour(self):
        y = fresh({"creator_name": "A", "brand": {"highlight": "gold"}})
        with self.assertRaises(SystemExit):
            y.palette_sub("#FFBB00")


if __name__ == "__main__":
    unittest.main()
