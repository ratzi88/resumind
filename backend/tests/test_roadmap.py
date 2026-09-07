import unittest

from matching import analyze_job_skills
from roadmap import resolve_role_progress, build_job_roadmap, apply_job_progress


class RoadmapTest(unittest.TestCase):
    def test_cv_recovers_failed_onboarding_detection_without_mutating_input(self):
        rows = [dict(skill_name='Python', acquired=False), dict(skill_name='Docker', acquired=False)]
        resolved = resolve_role_progress(rows, 'Python developer')
        self.assertTrue(resolved[0]['acquired'])
        self.assertTrue(resolved[0]['detected_in_resume'])
        self.assertFalse(resolved[1]['acquired'])
        self.assertFalse(rows[0]['acquired'])

    def test_explicit_uncheck_is_not_overridden_by_cv(self):
        rows = [dict(skill_name='Python', acquired=False, manual_override=True)]
        self.assertFalse(resolve_role_progress(rows, 'Python developer')[0]['acquired'])

    def test_saved_detection_or_manual_check_survives_missing_cv_mention(self):
        rows = [dict(skill_name='Docker', acquired=True),
                dict(skill_name='Kubernetes', acquired=True, manual_override=True)]
        self.assertTrue(all(r['acquired'] for r in resolve_role_progress(rows, 'Python')))

    def test_roadmap_aliases_match_cv(self):
        names = ['Linux CLI', 'Bash & Terminal', 'Networking Basics']
        rows = [dict(skill_name=name, acquired=False) for name in names]
        self.assertTrue(all(r['acquired'] for r in resolve_role_progress(rows, 'Linux, Bash, networking')))

    def test_git_in_cv_also_acquires_github(self):
        rows = [dict(skill_name='Git', acquired=False), dict(skill_name='GitHub', acquired=False)]
        resolved = resolve_role_progress(rows, 'Used Git for version control')
        self.assertTrue(all(row['acquired'] for row in resolved))
        self.assertTrue(all(row['detected_in_resume'] for row in resolved))

    def test_saved_github_progress_also_acquires_git(self):
        rows = [dict(skill_name='Git', acquired=False), dict(skill_name='GitHub', acquired=True)]
        self.assertTrue(all(row['acquired'] for row in resolve_role_progress(rows, 'Python')))

    def test_unchecking_linked_git_skills_overrides_cv_detection(self):
        rows = [
            dict(skill_name='Git', acquired=False, manual_override=True),
            dict(skill_name='GitHub', acquired=False, manual_override=True),
        ]
        self.assertFalse(any(row['acquired'] for row in resolve_role_progress(rows, 'Git and GitHub')))

    def test_job_roadmap_uses_posting_not_onboarding_role(self):
        analysis = analyze_job_skills('Python developer', None, 'Python and Docker required')
        catalog = [dict(skill_name='Python', category='Language', stage=1),
                   dict(skill_name='Docker', category='Infrastructure', stage=3),
                   dict(skill_name='React', category='Frontend', stage=2)]
        plan = build_job_roadmap(analysis, catalog, [])
        self.assertEqual([s['skill_name'] for s in plan], ['Python', 'Docker'])
        self.assertEqual([s['stage'] for s in plan], [1, 3])
        self.assertEqual([s['acquired'] for s in plan], [True, False])
        self.assertTrue(all(s['impact'] == 1 for s in plan))

    def test_job_progress_overrides_cv_and_keeps_gap_panel_consistent(self):
        analysis = analyze_job_skills('Python developer', 'Python; Docker', '')
        progress = [dict(skill_name='Python', acquired=False), dict(skill_name='Docker', acquired=True)]
        plan = build_job_roadmap(analysis, [], progress)
        result = apply_job_progress(analysis, plan)
        self.assertEqual(result['matched_skills'], ['Docker'])
        self.assertEqual(result['missing_skills'], ['Python'])
        self.assertEqual(result['coverage_pct'], 50.0)
        self.assertEqual(result['skill_details'][0]['evidence'], '')
        self.assertIn('Marked as learned', result['skill_details'][1]['evidence'])
        self.assertEqual(analysis['matched_skills'], ['Python'])

    def test_empty_posting_does_not_invent_a_plan_or_coverage(self):
        analysis = analyze_job_skills('Python', None, 'Join our team')
        plan = build_job_roadmap(analysis, [], [])
        self.assertEqual(plan, [])
        self.assertIsNone(apply_job_progress(analysis, plan)['coverage_pct'])


if __name__ == '__main__':
    unittest.main()
