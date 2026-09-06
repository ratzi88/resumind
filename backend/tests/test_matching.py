import unittest

from matching import (
    analyze_skills,
    compute_match_pct,
    parse_required_skills,
    redact_pii,
    skill_present,
)


class MatchingHelpersTest(unittest.TestCase):
    def test_skill_aliases_are_detected(self):
        resume = "Built APIs with Python and PostgreSQL; deployed services on k8s."
        self.assertTrue(skill_present("Python", resume))
        self.assertTrue(skill_present("Postgres", resume))
        self.assertTrue(skill_present("Kubernetes", resume))

    def test_skill_detection_returns_evidence_and_gaps(self):
        result = analyze_skills(
            "Python developer who built REST APIs.",
            ["Python", "REST APIs", "Docker"],
        )
        self.assertEqual(result["matched_skills"], ["Python", "REST APIs"])
        self.assertEqual(result["missing_skills"], ["Docker"])
        self.assertIn("Python", result["skill_details"][0]["evidence"])

    def test_required_skill_parser_deduplicates_bullets(self):
        skills = parse_required_skills("Python, Docker; Python\n• PostgreSQL")
        self.assertEqual(skills, ["Python", "Docker", "PostgreSQL"])

    def test_score_is_bounded_and_explainable(self):
        self.assertEqual(compute_match_pct(1.0, 3, 3), 100.0)
        self.assertGreaterEqual(compute_match_pct(-1.0), 0.0)
        self.assertLessEqual(compute_match_pct(1.0), 100.0)

    def test_common_contact_pii_is_redacted(self):
        redacted = redact_pii("Reach me at jane@example.com or +972 50-123-4567")
        self.assertNotIn("jane@example.com", redacted)
        self.assertNotIn("50-123-4567", redacted)
        self.assertIn("[email]", redacted)
        self.assertIn("[phone]", redacted)


if __name__ == "__main__":
    unittest.main()
