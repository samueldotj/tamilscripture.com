"""Unit tests for tools/translate. Run: python -m unittest discover -s tools/translate/tests
No API calls; nothing here needs the build except where noted."""

import sys
import tempfile
import unittest.mock
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from translate_tool import checks, prompts, repo, translate  # noqa: E402
from translate_tool.repo import Name, Term  # noqa: E402


def article(paragraphs, licence="PD", refs=()):
    return {
        "id": "eastons/justification",
        "title": "Justification",
        "licence": licence,
        "hash": "1e3d44dd",
        "refs": list(refs),
        "paragraphs": [{"id": f"eastons/justification#p{i}-x", "text": t} for i, t in enumerate(paragraphs, 1)],
    }


TERMS = {
    "justification": Term("justification", "நீதிமானாக்கப்படுதல்", ["நீதிமானாக்கப்படுதல்", "நீதிமானாக்கு"], ["நியாயப்படுத்துதல்"], ["justified", "justify"], "", False),
}
NAMES = {"Vashti": Name("Vashti", "வஸ்தி", ["வஸ்தி", "வஸ்தியின்"])}


class RefTests(unittest.TestCase):
    def test_forms(self):
        self.assertEqual(repo.parse_ref("Romans 5:1-3"), ["ROM.5.1", "ROM.5.2", "ROM.5.3"])
        self.assertEqual(repo.parse_ref("Rom. 5:1"), ["ROM.5.1"])
        self.assertEqual(repo.parse_ref("EST 1:10"), ["EST.1.10"])
        self.assertEqual(repo.parse_ref("1 Cor. 13:4"), ["1CO.13.4"])
        self.assertEqual(repo.parse_ref("Song of Solomon 2:1"), ["SNG.2.1"])

    def test_not_verses(self):
        self.assertEqual(repo.parse_ref("Psalm 23"), [])  # whole chapter
        self.assertEqual(repo.parse_ref("Chapter 3:4"), [])  # not a book
        self.assertEqual(repo.parse_ref("Gen 1:5-2"), ["GEN.1.5"])  # reversed range


class StrongsTests(unittest.TestCase):
    def test_usfm(self):
        usfm = (
            "\\id ROM - Berean Study Bible\n\\c 4\n\\v 25 \\w He|strong=\"G3739\"\\w* was raised "
            "\\w for|strong=\"G1223\"\\w* \\w our|strong=\"G1473\"\\w* \\w justification|strong=\"G1347\"\\w*.\n"
            "\\c 5\n\\v 1 \\w justified|strong=\"G01344\"\\w*\n"
        )
        rows = repo.parse_usfm_strongs(usfm)
        self.assertIn(("ROM.4.25", "justification", "G1347"), rows)
        self.assertIn(("ROM.5.1", "justified", "G1344"), rows)

    def test_normalise(self):
        self.assertEqual(repo.normalise_strongs("g01344"), "G1344")
        self.assertEqual(repo.normalise_strongs("H7225a"), "H7225")
        with self.assertRaises(ValueError):
            repo.normalise_strongs("X12")


class GlossaryTests(unittest.TestCase):
    def test_load_skips_unreviewed(self):
        toml = (
            '["justification"]\nta = "நீதிமானாக்கப்படுதல்"\nalso = ["justified"]\n\n'
            '["propitiation"]\nta = "கிருபாதாரபலி"\nreview = true\n'
        )
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "g.toml"
            p.write_text(toml, encoding="utf-8")
            self.assertEqual(set(repo.load_glossary(p)), {"justification", "propitiation"})
            self.assertEqual(set(repo.reviewed_terms(p)), {"justification"})
            self.assertEqual(repo.reviewed_terms(p)["justification"].also, ["justified"])

    def test_terms_in(self):
        self.assertEqual(checks.terms_in("By Justification we mean", TERMS), [TERMS["justification"]])
        self.assertEqual(checks.terms_in("he was justified by faith", TERMS), [TERMS["justification"]])
        self.assertEqual(checks.terms_in("justice", TERMS), [])


class CheckTests(unittest.TestCase):
    EN = "A forensic term, opposed to condemnation (Rom. 5:1-10). Vashti was queen."

    def good(self):
        return "நீதிமானாக்கப்படுதல் என்பது நீதிமன்றச் சொல் (ரோமர் 5:1-10). வஸ்தி ராணியாக இருந்தாள்."

    def test_clean(self):
        a = article([self.EN.replace("A forensic term", "Justification: a forensic term")])
        ps = checks.check_draft(a, "நீதிமானாக்கப்படுதல்", [{"id": a["paragraphs"][0]["id"], "text": self.good()}], TERMS, NAMES)
        self.assertEqual(ps, [])

    def test_problems(self):
        a = article([self.EN.replace("A forensic term", "Justification: a forensic term"), "Second paragraph."])
        bad = "நியாயப்படுத்துதல் என்பது (ரோமர் 5). and then it was left in plain English words here."
        ps = [str(p) for p in checks.check_draft(a, "Justification", [{"id": a["paragraphs"][0]["id"], "text": bad}], TERMS, NAMES)]
        joined = "\n".join(ps)
        self.assertIn("title: no Tamil script", joined)
        self.assertIn("ids differ", joined)
        self.assertIn("untranslated English", joined)
        self.assertIn("verse references missing: 5:1", joined)
        self.assertIn("“justification” should be", joined)
        self.assertIn("“நியாயப்படுத்துதல்” is not used", joined)
        self.assertIn("name: Vashti", joined)

    def test_avoid_ignores_own_and_other_terms_words(self):
        terms = {
            "baptism": Term("baptism", "ஞானஸ்நானம்", ["ஞானஸ்நானம்"], ["ஸ்நானம் (bathing)", "திருமுழுக்கு"], [], "", False),
            "covenant": Term("covenant", "உடன்படிக்கை", ["உடன்படிக்கை"], ["வாக்குத்தத்தம்", "ஒப்பந்தம்"], [], "", False),
            "promise": Term("promise", "வாக்குத்தத்தம்", ["வாக்குத்தத்தம்"], [], [], "", False),
        }
        self.assertEqual(checks.usable_avoid(terms["baptism"], terms), ["திருமுழுக்கு"])
        self.assertEqual(checks.usable_avoid(terms["covenant"], terms), ["ஒப்பந்தம்"])
        a = article(["The covenant and its promise; baptism."])
        ok = "உடன்படிக்கையும் அதின் வாக்குத்தத்தமும்; ஞானஸ்நானம்."
        self.assertEqual(checks.check_draft(a, "நீதி", [{"id": a["paragraphs"][0]["id"], "text": ok}], terms, {}), [])
        bad = "ஒப்பந்தமும் வாக்குத்தத்தமும்; ஞானஸ்நானம்."
        ps = [str(p) for p in checks.check_draft(a, "நீதி", [{"id": a["paragraphs"][0]["id"], "text": bad}], terms, {})]
        self.assertTrue(any("ஒப்பந்தம்" in p for p in ps))

    def test_inflected_name_counts(self):
        self.assertTrue(checks.uses_any("வஸ்தியை அழைத்தான்", ["வஸ்தி"]))

    def test_common_words_are_not_names(self):
        names = {"On": Name("On", "ஓன்", ["ஓன்"])}
        self.assertEqual(checks.names_in("On the third day", names), [])

    def test_hard_problems(self):
        self.assertTrue(translate.is_hard(checks.Problem("p1", "no Tamil script")))
        self.assertTrue(translate.is_hard(checks.Problem("response", "refused (None)")))
        self.assertFalse(translate.is_hard(checks.Problem("p1", "glossary: “x” should be y")))


class PromptTests(unittest.TestCase):
    def test_chunks(self):
        long = " ".join(["word"] * 1500)
        a = article([long, long, "short", long])
        parts = prompts.chunks(a)
        self.assertEqual([len(p) for p in parts], [1, 2, 1])
        self.assertEqual(sum(parts, []), a["paragraphs"])

    def test_system_prompt_is_fixed_and_glossary_goes_with_the_article(self):
        self.assertEqual(prompts.system_blocks(), prompts.system_blocks())
        self.assertNotIn("நீதிமானாக்கப்படுதல்", prompts.system_blocks()[0]["text"])
        terms = {**TERMS, "grace": Term("grace", "கிருபை", ["கிருபை"], [], [], "[Claude: high] The IRV's word.", False)}
        a = article(["Justification is by grace alone."])
        msg = prompts.user_message(a, a["paragraphs"], (1, 1), {}, None, terms)
        self.assertIn("justification (justified, justify) → நீதிமானாக்கப்படுதல்", msg)
        self.assertIn("grace → கிருபை; note: The IRV's word.", msg)  # review tag stripped
        other = {**article(["A city of Judah."]), "title": "Adullam"}
        self.assertNotIn("Glossary", prompts.user_message(other, other["paragraphs"], (1, 1), {}, None, terms))

    def test_custom_id_shape(self):
        cid = translate.custom_id("aquifer/a-very-long-slug-" + "x" * 80, 12)
        self.assertRegex(cid, r"^[A-Za-z0-9_-]{1,64}$")

    def test_draft_folder_follows_licence(self):
        self.assertIn("ta-sa", str(repo.draft_path({**article([]), "id": "aquifer/abagtha", "licence": "CC BY-SA 4.0"})))
        self.assertNotIn("ta-sa", str(repo.draft_path(article([]))))


class NamesFileTests(unittest.TestCase):
    def test_every_line_round_trips(self):
        """name_line writes exactly what entity-ingest's names::save writes."""
        lines = [l for l in repo.NAMES.read_text(encoding="utf-8").splitlines() if l.startswith('"')]
        names = repo.load_names()
        self.assertEqual(len(lines), len(names))
        for line in lines:
            name = next(n for n in [line.split('" = ', 1)[0][1:]] if n in names)
            self.assertEqual(repo.name_line(name, names[name]), line)

    def test_save_replaces_and_inserts_in_order(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "names.toml"
            p.write_text('# header\n\n"Abana" = { label = "x", forms = ["x"], confidence = 0.50, n = 1, review = true }\n'
                         '"Abda" = { label = "y", forms = ["y"], confidence = 0.50, n = 1, review = true }\n', encoding="utf-8")
            repo.save_name("Abana", {"label": "ஆப்னா", "forms": ["ஆப்னாவும்"], "confidence": 1.0, "n": 1}, p)
            repo.save_name("Abb", {"label": "அ", "forms": ["அ"], "n": 0}, p)
            names = repo.load_names(p)
            self.assertEqual(list(names), ["Abana", "Abb", "Abda"])
            self.assertNotIn("review", names["Abana"])
            self.assertEqual(set(repo.reviewed_names(p)), {"Abana", "Abb"})
            self.assertTrue(p.read_text(encoding="utf-8").startswith("# header\n\n"))


class ReviewTests(unittest.TestCase):
    def test_skeletons(self):
        from translate_tool import review
        self.assertEqual(review.skeleton_ta("அபக்தா"), review.skeleton_en("Abagtha"))
        self.assertEqual(review.skeleton_ta("வஸ்தி"), review.skeleton_en("Vashti"))
        self.assertGreater(review.sounds_like("அபக்தா", "Abagtha"), review.sounds_like("பிக்தா", "Abagtha"))
        self.assertLess(review.sounds_like("அழைத்துவரவேண்டுமென்று", "Abagtha"), 0.5)

    def test_neighbours(self):
        from translate_tool import review
        self.assertEqual(review.neighbours("EST.1.10"), ("EST.1.9", "EST.1.11"))
        self.assertEqual(review.neighbours("GEN.1.1"), (None, "GEN.1.2"))


class SessionTests(unittest.TestCase):
    def test_base_forms(self):
        from translate_tool.review import base_of
        from translate_tool.session import guess_label
        cases = {"ஆப்னாவும்": "ஆப்னா", "அப்தாவின்": "அப்தா", "அப்தெயேலின்": "அப்தெயேல்", "ஆரோனை": "ஆரோன்",
                 "ஆரோனுக்குப்": "ஆரோன்", "தமஸ்குவை": "தமஸ்கு", "வஸ்தியின்": "வஸ்தி", "எருசலேமில்": "எருசலேம்",
                 "யோசேப்": "யோசேப்", "அபக்தா": "அபக்தா"}
        for word, base in cases.items():
            self.assertEqual(base_of(word), base, word)
        self.assertEqual(guess_label([("ஆரோனின்", 5), ("ஆரோன்", 3), ("ஆரோனை", 2)]), "ஆரோன்")

    def test_more_base_forms(self):
        from translate_tool.review import base_of
        cases = {"நேபாத்தின்": "நேபாத்", "அம்மிஷதாயின்": "அம்மிஷதாய்", "மல்கிசூவாவையும்": "மல்கிசூவா",
                 "ஆரோனையும்": "ஆரோன்", "வஸ்தியையும்": "வஸ்தி", "அம்சிக்குப்": "அம்சி", "ஏலிமைவிட்டு": "ஏலிம்",
                 "தாபோரிலுள்ள": "தாபோர்", "லேவியின்": "லேவி"}
        for word, base in cases.items():
            self.assertEqual(base_of(word), base, word)

    def test_auto_accept_and_revert(self):
        from translate_tool import session
        with tempfile.TemporaryDirectory() as d:
            copy = Path(d) / "names-ta.toml"
            original = repo.NAMES.read_text(encoding="utf-8")
            copy.write_text(original, encoding="utf-8")
            real, repo.NAMES = repo.NAMES, copy
            real_log, session.AUTO_LOG = session.AUTO_LOG, Path(d) / "auto.jsonl"
            real_work, repo.WORK = repo.WORK, Path(d)
            try:
                dry = session.auto_accept(0.9, 0.7, dry_run=True)
                self.assertEqual(copy.read_text(encoding="utf-8"), original)
                done = session.auto_accept(0.9, 0.7)
                names = repo.load_names()
                self.assertEqual(len(done), len(dry))
                for r in done:
                    self.assertNotIn("-", r["name"])
                    self.assertGreater(r["confidence"], 0.7)
                    self.assertNotIn("review", names[r["name"]])
                self.assertEqual(session.auto_revert(), len([r for r in done if "after" in r]))
                self.assertEqual(copy.read_text(encoding="utf-8"), original)
            finally:
                repo.NAMES, session.AUTO_LOG, repo.WORK = real, real_log, real_work

    def test_below_filters_by_confidence(self):
        from translate_tool import session
        items = session.queue("verses", None, False, False, below=0.6)
        self.assertTrue(items)
        self.assertTrue(all(i.entry.get("confidence", 1) < 0.6 for i in items))
        self.assertLess(len(items), len(session.queue("verses", None, False, False)))

    def test_scripted_session(self):
        """Accept, reject, skip, undo and quit against a copy of names-ta.toml
        (needs the built content)."""
        from translate_tool import session
        with tempfile.TemporaryDirectory() as d:
            copy = Path(d) / "names-ta.toml"
            copy.write_text(repo.NAMES.read_text(encoding="utf-8"), encoding="utf-8")
            real, repo.NAMES = repo.NAMES, copy
            try:
                # The first three names still to review, whatever they are now.
                first = [i.name for i in session.queue("alpha", None, False, False)[:3]]
                answers = iter(["", "r", "s", "u", "2", "q"])
                with unittest.mock.patch("sys.stdout", new=__import__("io").StringIO()):
                    counts = session.run(order="alpha", shown=1, color=False, read=lambda _: next(answers))
                names = repo.load_names()
            finally:
                repo.NAMES = real
        one, two, three = first
        self.assertNotIn("review", names[one])
        # The second was rejected, undone, then given suggestion 2; the third was skipped.
        self.assertNotIn("review", names[two])
        self.assertTrue(names[three].get("review"))
        self.assertEqual(counts, {"accepted": 2, "rejected": 0, "skipped": 1, "undone": 1})


class AiNamesTests(unittest.TestCase):
    """The checks on Claude's answers; no API call."""

    def item(self, name):
        from translate_tool import session
        return next(i for i in session.queue("verses", None, True, True) if i.name == name)

    def test_phrase_found_in_the_irv_is_accepted(self):
        from translate_tool import ai_names
        d = ai_names.decide(self.item("City of David"), {
            "label": "தாவீதின் நகரம்", "forms": ["தாவீதின் நகரம்", "தாவீதின் நகரத்தில்"],
            "source": "irv", "confidence": "high", "note": ""})
        self.assertEqual(d["action"], "accept")
        self.assertEqual(d["entry"]["forms"], ["தாவீதின் நகரம்", "தாவீதின் நகரத்தில்"])
        self.assertNotIn("review", d["entry"])

    def test_forms_not_in_the_verses_make_a_draft(self):
        from translate_tool import ai_names
        d = ai_names.decide(self.item("City of David"), {
            "label": "தாவீதின் பட்டணம்", "forms": ["தாவீதின் பட்டணம்"],
            "source": "irv", "confidence": "high", "note": ""})
        self.assertEqual(d["action"], "draft")
        self.assertTrue(d["entry"]["review"])
        self.assertIn("not in the verses", d["why"])

    def test_composed_names_are_drafts(self):
        from translate_tool import ai_names
        d = ai_names.decide(self.item("Abagtha"), {
            "label": "அபக்தா", "forms": [], "source": "composed", "confidence": "medium", "note": ""})
        self.assertEqual(d["action"], "draft")
        self.assertEqual(d["entry"]["label"], "அபக்தா")

    def test_found_in_the_next_verse(self):
        from translate_tool import ai_names
        d = ai_names.decide(self.item("Abagtha"), {
            "label": "அபக்தா", "forms": ["அபக்தா"], "source": "irv", "confidence": "high", "note": ""})
        self.assertEqual(d["action"], "accept")

    def test_groups_share_verses_and_stay_small(self):
        from translate_tool import ai_names, session
        todo = session.queue("verses", None, True, True, only={"Abagtha", "Bigtha", "Biztha", "Harbona", "Mehuman", "Zethar", "City of David"})
        gs = ai_names.groups(todo)
        self.assertEqual(sum(len(g) for g in gs), len(todo))
        self.assertTrue(all(len(g) <= ai_names.GROUP_NAMES for g in gs))
        esther = next(g for g in gs if any(i.name == "Abagtha" for i in g))
        self.assertGreaterEqual(len(esther), 5)
        msg = ai_names.group_message(esther)
        self.assertEqual(msg.count("\nEST.1.10\n"), 1)  # the shared verse is sent once

    def test_group_answers_are_matched_by_name(self):
        from translate_tool import ai_names, session
        with tempfile.TemporaryDirectory() as d:
            copy = Path(d) / "names-ta.toml"
            copy.write_text(repo.NAMES.read_text(encoding="utf-8"), encoding="utf-8")
            saved = repo.NAMES, ai_names.LOG, repo.WORK
            repo.NAMES, ai_names.LOG, repo.WORK = copy, Path(d) / "ai.jsonl", Path(d)
            try:
                group = session.queue("verses", None, True, True, only={"Abagtha", "Bigtha"})
                data = {"answers": [
                    {"name": "Bigtha", "label": "பிக்தா", "forms": ["பிக்தா"], "source": "irv", "confidence": "high", "note": ""},
                    {"name": "Abagtha", "label": "அபக்தா", "forms": ["அபக்தா"], "source": "irv", "confidence": "high", "note": ""},
                ]}
                rows = ai_names.apply_group(group, data, None, dry_run=False)
                names = repo.load_names()
                self.assertEqual({r["name"]: r["action"] for r in rows}, {"Abagtha": "accept", "Bigtha": "accept"})
                self.assertEqual(names["Bigtha"]["label"], "பிக்தா")
                self.assertEqual(ai_names.accepted(), {"Abagtha", "Bigtha"})
                missing = ai_names.apply_group(group, None, "errored: overloaded", dry_run=False)
                self.assertTrue(all(r["action"] == "skip" for r in missing))
            finally:
                repo.NAMES, ai_names.LOG, repo.WORK = saved

    def test_english_is_skipped(self):
        from translate_tool import ai_names
        d = ai_names.decide(self.item("Abagtha"), {
            "label": "Abagtha", "forms": [], "source": "composed", "confidence": "low", "note": ""})
        self.assertEqual(d["action"], "skip")


class ParallelRunTests(unittest.TestCase):
    """client.run_many and the direct runs built on it; the API is faked."""

    def test_requests_overlap_and_come_back_matched(self):
        import threading
        import time
        from translate_tool import client

        active, peak, lock = [0], [0], threading.Lock()

        def fake(p, cid):
            with lock:
                active[0] += 1
                peak[0] = max(peak[0], active[0])
            time.sleep(0.2)
            with lock:
                active[0] -= 1
            return client.Reply({"echo": p["n"]}, None, "")

        with unittest.mock.patch.object(client, "run_direct", fake), \
             unittest.mock.patch.object(client, "client", lambda: None):
            start = time.time()
            got = dict(client.run_many([(f"c{k}", {"n": k}) for k in range(12)], workers=6))
            took = time.time() - start
        self.assertEqual({k: r.data["echo"] for k, r in got.items()}, {k: k for k in range(12)})
        self.assertEqual(peak[0], 6)
        self.assertLess(took, 1.2)  # 12 × 0.2 s one at a time would be 2.4 s

    def test_terms_direct_run_writes_every_answer(self):
        from translate_tool import client, repo, terms

        def fake(p, cid):
            names = [l.split(". ", 1)[1].split("  (")[0] for l in p["messages"][0]["content"].splitlines()
                     if l[:1].isdigit() and ". " in l]
            return client.Reply({"answers": [{"term": n, "ta": "சோதனை", "forms": [], "avoid": [], "source": "curated",
                                              "confidence": "low", "note": ""} for n in names]}, None, "")

        with tempfile.TemporaryDirectory() as d:
            saved = repo.GLOSSARY, terms.LOG, repo.WORK
            repo.GLOSSARY, terms.LOG, repo.WORK = Path(d) / "g.toml", Path(d) / "t.jsonl", Path(d)
            try:
                seeds = {s.en: s for s in terms.load_seed()}
                items = terms.evidence([seeds[t] for t in ["Trinity", "Godhead", "incarnation", "deity", "justification"]])
                with unittest.mock.patch.object(client, "run_direct", fake), \
                     unittest.mock.patch.object(client, "client", lambda: None), \
                     unittest.mock.patch("sys.stdout", new=__import__("io").StringIO()):
                    rows = terms.run_direct(items, "m", "low", False, workers=3)
                self.assertEqual(sum(r["action"] == "draft" for r in rows), 5)
                self.assertEqual(len(terms.load_file()), 5)
            finally:
                repo.GLOSSARY, terms.LOG, repo.WORK = saved


class PilotTests(unittest.TestCase):
    """Two faked models on two articles: separate folders, blind order, adopt."""

    def test_pilot_run_compare_and_adopt(self):
        import json
        from translate_tool import client, pilot, pilotweb, translate

        def fake_for(tag):
            def fake(p, cid):
                msg = p["messages"][-1]["content"]
                if "Article:\n" not in msg:
                    return client.Reply(json.loads(p["messages"][1]["content"]), None, p["messages"][1]["content"])
                art = json.loads(msg[msg.index("Article:\n") + 9:])
                data = {"title": "சோதனை", "paragraphs": [{"id": x["id"], "text": f"{tag} சோதனை"} for x in art["paragraphs"]]}
                return client.Reply(data, None, json.dumps(data, ensure_ascii=False))
            return fake

        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "pilot.txt").write_text("# pilot\neastons/abagtha\naquifer/abagtha\n", encoding="utf-8")
            saved = (pilot.LIST, pilot.ROOT, pilot.RATINGS, repo.DRAFTS, repo.ENTITIES, translate.REPORT, translate.FLAGGED)
            pilot.LIST, pilot.ROOT, pilot.RATINGS = d / "pilot.txt", d / "pilot", d / "pilot" / "ratings.jsonl"
            repo.ENTITIES = d / "entities"
            try:
                with unittest.mock.patch.object(client, "client", lambda: None), \
                     unittest.mock.patch("sys.stdout", new=__import__("io").StringIO()):
                    for m in ("model-one", "model-two"):
                        with unittest.mock.patch.object(client, "run_direct", fake_for(m)):
                            pilot.run(m, "low", 2)
                self.assertEqual(pilot.models(), ["model-one", "model-two"])
                # each model's drafts in its own folder; ShareAlike (Aquifer) under ta-sa
                self.assertTrue((d / "pilot" / "model-one" / "drafts" / "ta" / "eastons" / "abagtha.json").exists())
                self.assertTrue((d / "pilot" / "model-two" / "drafts" / "ta-sa" / "aquifer" / "abagtha.json").exists())
                s = pilotweb.PilotSession(pilot.models())
                v = s.view()
                a_model, b_model = s.order(v["id"])
                self.assertTrue(v["rows"][0]["a"].startswith(a_model))
                s.rate("a", "better")
                s.rate("w", "")
                res = s.results()
                self.assertEqual(res[a_model]["better"], 1)
                self.assertEqual(res[b_model]["worse"], 1)
                self.assertEqual(res[a_model]["both need work"], 1)
                copied, skipped = pilot.adopt("model-two")
                self.assertEqual((copied, skipped), (2, 0))
                adopted = json.loads((d / "entities" / "drafts" / "ta" / "eastons" / "abagtha.json").read_text(encoding="utf-8"))
                self.assertTrue(adopted["paragraphs"][0]["text"].startswith("model-two"))
            finally:
                (pilot.LIST, pilot.ROOT, pilot.RATINGS, repo.DRAFTS, repo.ENTITIES, translate.REPORT,
                 translate.FLAGGED) = saved


class GlossaryTermsTests(unittest.TestCase):
    """The theological glossary (translate ai-terms / review-terms); no API call."""

    def test_seed_parses(self):
        from translate_tool import terms
        seeds = {s.en: s for s in terms.load_seed()}
        self.assertIn("justification", seeds)
        self.assertEqual(seeds["justification"].also, ["justify", "justified", "justifies"])
        self.assertTrue(seeds["Trinity"].curated)
        self.assertEqual(seeds["LORD"].key, "LORD")
        self.assertEqual(seeds["Lord"].key, "lord")

    def test_lord_and_LORD_stay_apart(self):
        from translate_tool import checks
        self.assertTrue(checks.mentions("The LORD is my shepherd", "LORD"))
        self.assertFalse(checks.mentions("The LORD is my shepherd", "Lord"))
        self.assertTrue(checks.mentions("the Lord Jesus", "Lord"))
        self.assertTrue(checks.mentions("the Lord’s Supper", "Lord's Supper"))

    def test_strongs_from_the_bsb(self):
        from translate_tool import terms
        seeds = {s.en: s for s in terms.load_seed()}
        self.assertIn("G1344", terms.strongs_for(seeds["justification"]))
        self.assertEqual(terms.strongs_for(seeds["LORD"]), ["H3068"])
        self.assertNotIn("H3068", terms.strongs_for(seeds["Lord"]))

    def test_entry_keeps_only_forms_in_the_irv(self):
        from translate_tool import terms
        seeds = {s.en: s for s in terms.load_seed()}
        ev = terms.Evidence(seeds["justification"], ["G1344"], ["ROM.3.20", "ROM.8.30"], 68, "")
        e = terms.entry_from(ev, {"ta": "நீதிமானாக்குதல்", "forms": ["நீதிமானாக்கப்படுவது", "நீதிமான்களாக்கினாரோ", "நியாயமாக்குதல்"],
                                  "avoid": ["நியாயப்படுத்துதல்"], "source": "irv", "confidence": "high", "note": ""})
        self.assertIn("நீதிமானாக்கப்படுவது", e["forms"])
        self.assertNotIn("நியாயமாக்குதல்", e["forms"])
        self.assertIn("dropped: நியாயமாக்குதல்", e["note"])
        self.assertTrue(e["review"])

    def test_file_round_trip_and_review_session(self):
        from translate_tool import repo, terms, termweb
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "glossary.toml"
            saved = repo.GLOSSARY
            repo.GLOSSARY = path
            try:
                terms.save_file({
                    "justification": {"en": "justification", "ta": "நீதிமானாக்குதல்", "forms": ["நீதிமானாக்குதல்"],
                                      "also": ["justified"], "avoid": ["நியாயப்படுத்துதல்"], "source": "irv",
                                      "note": "x \"quoted\"", "review": True},
                    "LORD": {"en": "LORD", "ta": "யெகோவா", "forms": ["யெகோவா"], "source": "irv", "review": True},
                })
                self.assertEqual(set(terms.load_file()), {"justification", "LORD"})
                self.assertEqual(repo.reviewed_terms(), {})  # nothing approved yet
                s = termweb.TermSession(termweb.queue())
                first = s.current
                s.approve("நீதிமானாக்குதல்", ["நீதிமான்களாக்கினாரோ"], ["நியாயப்படுத்துதல்"], "ok")
                approved = repo.reviewed_terms()
                self.assertEqual(list(approved), [first])
                s.undo()
                self.assertEqual(repo.reviewed_terms(), {})
                self.assertEqual(terms.load_file()["justification"]["note"], "x \"quoted\"")
                with self.assertRaises(ValueError):
                    s.approve("justification", [], [], "")
            finally:
                repo.GLOSSARY = saved


if __name__ == "__main__":
    unittest.main()
