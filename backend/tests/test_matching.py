import unittest

from matching import (
    analyze_job_skills,
    analyze_skills,
    compute_match_pct,
    extract_job_skills,
    job_market_statistics,
    parse_required_skills,
    rank_job_matches,
    redact_pii,
    skill_present,
)


class MatchingHelpersTest(unittest.TestCase):
    def test_fit_is_ranked_before_pagination(self):
        rows = [
            dict(job_id='1', title='A', raw_score=0.9, skills_desc='Python; Docker; Kubernetes'),
            dict(job_id='2', title='B', raw_score=0.8, skills_desc='Python'),
        ]
        self.assertEqual(rank_job_matches(rows, 'Python', limit=1)[0]['job_id'], '2')
        self.assertEqual(rank_job_matches(rows, 'Python', page=2, limit=1)[0]['job_id'], '1')
        self.assertEqual(rank_job_matches(rows, 'Python', page=3, limit=1), [])
        self.assertEqual(rows[0]['job_id'], '1')

    def test_fit_sort_handles_no_skill_data_and_stable_ties(self):
        rows = [dict(job_id=str(i), title='Same title', raw_score=0.7) for i in (3, 1, 2)]
        self.assertEqual([r['job_id'] for r in rank_job_matches(rows, '')], ['1', '2', '3'])

    def test_title_sort_remains_case_insensitive(self):
        rows = [dict(job_id='1', title='zulu', raw_score=0.9), dict(job_id='2', title='Alpha', raw_score=0.7)]
        self.assertEqual(rank_job_matches(rows, '', sort='title')[0]['job_id'], '2')

    def test_fit_sort_does_not_cache_resume_or_progress(self):
        rows = [dict(job_id='1', title='A', raw_score=0.8, skills_desc='Python'),
                dict(job_id='2', title='B', raw_score=0.8, skills_desc='Docker')]
        self.assertEqual(rank_job_matches(rows, 'Python')[0]['job_id'], '1')
        self.assertEqual(rank_job_matches(rows, 'Docker')[0]['job_id'], '2')

    def test_market_statistics_count_each_skill_once_per_recommended_job(self):
        rows = [
            dict(job_id='1', raw_score=0.8, skills_desc='Python; Docker; Docker'),
            dict(job_id='2', raw_score=0.7, skills_desc='Docker; Kubernetes'),
            dict(job_id='3', raw_score=0.9, description='Join our growing team!'),
        ]
        result = job_market_statistics(rows, 'Built Python services.')
        self.assertEqual(result['total_jobs'], 3)
        self.assertEqual(result['jobs_with_detected_skills'], 2)
        docker = next(item for item in result['all_skills'] if item['name'] == 'Docker')
        self.assertEqual(docker['job_count'], 2)
        self.assertEqual(docker['percentage'], 66.7)
        self.assertFalse(docker['in_profile'])
        self.assertEqual(result['strongest_skills'][0]['name'], 'Python')
        self.assertEqual(result['skills_to_strengthen'][0]['name'], 'Docker')
        self.assertEqual(result['fit_bands'], {'strong': 1, 'good': 1, 'exploratory': 1})
        self.assertEqual(result['average_fit'], 71.7)

    def test_market_statistics_deduplicate_aliases_and_handle_no_jobs(self):
        rows = [dict(job_id='1', raw_score=0.8, skills_desc='Postgres; PostgreSQL')]
        result = job_market_statistics(rows, 'Used PostgreSQL.')
        self.assertEqual(len(result['all_skills']), 1)
        self.assertEqual(result['all_skills'][0]['job_count'], 1)
        self.assertTrue(result['all_skills'][0]['in_profile'])
        self.assertEqual(job_market_statistics([], ''), {
            'total_jobs': 0, 'jobs_with_detected_skills': 0, 'average_fit': None,
            'fit_bands': {'strong': 0, 'good': 0, 'exploratory': 0},
            'strongest_skills': [], 'skills_to_strengthen': [], 'all_skills': [],
        })

    def test_cached_extraction_returns_independent_lists(self):
        first = extract_job_skills('Python; Docker', '')
        first['required_skills'].clear()
        first['skill_sources'].append('bad')
        self.assertEqual(extract_job_skills('Python; Docker', '')['required_skills'], ['Python', 'Docker'])
        self.assertEqual(extract_job_skills('Python; Docker', '')['skill_sources'], ['skills_desc'])

    def test_missing_skills_column_uses_job_description_for_both_panels(self):
        result = analyze_job_skills(
            'Built Python services using Postgres.',
            None,
            'Requirements: Python, PostgreSQL and Docker. Deploy services on Kubernetes.',
        )
        self.assertEqual(result['matched_skills'], ['Python', 'PostgreSQL'])
        self.assertEqual(result['missing_skills'], ['Docker', 'Kubernetes'])
        self.assertEqual(result['coverage_pct'], 50.0)
        self.assertEqual(result['skill_sources'], ['description'])
        self.assertIn('Postgres', result['skill_details'][1]['evidence'])

    def test_real_java_posting_has_skills_without_separate_skills_field(self):
        description = (
            'Must Have Technical/Functional Skills: experience in JDK 1.8, '
            'Springs 3.x, Hibernate 4.0, JPA 2.0. Good knowledge of Spring boot '
            'and Angular 8.0, jQuery, Ajax, Bootstrap. Experience working in '
            'Agile framework and Microservices. Experience in CICD tools like '
            'Jenkins, Liquibase. Eclipse, XML, SOAP/REST Web Services.'
        )
        result = analyze_job_skills('Java developer using Spring Boot and Git.', None, description)
        self.assertIn('Java', result['matched_skills'])
        self.assertIn('Spring Boot', result['matched_skills'])
        self.assertIn('Angular', result['missing_skills'])
        self.assertIn('Jenkins', result['missing_skills'])
        self.assertIn('CI/CD', result['missing_skills'])
        self.assertIn('REST APIs', result['missing_skills'])
        self.assertNotIn('Git', result['required_skills'])

    def test_structured_skills_are_merged_with_prose_and_aliases_deduplicated(self):
        result = extract_job_skills('Postgres; Figma; D3.js; Docker', 'Use PostgreSQL and Kubernetes.')
        self.assertEqual(result['required_skills'], ['PostgreSQL', 'Figma', 'D3.js', 'Docker', 'Kubernetes'])
        self.assertEqual(result['skill_sources'], ['skills_desc', 'description'])

    def test_skills_field_containing_prose_is_not_used_as_a_skill_label(self):
        result = extract_job_skills('Experience with Java and Angular; Good knowledge of Docker.')
        self.assertEqual(result['required_skills'], ['Java', 'Angular', 'Docker'])

    def test_html_and_line_breaks_do_not_prevent_matching(self):
        result = analyze_job_skills(
            'Built RESTful APIs and used Amazon Web\nServices with nodejs.',
            None,
            '<ul><li>REST&nbsp;APIs</li><li>AWS</li><li>Node.js</li></ul>',
        )
        self.assertEqual(result['matched_skills'], ['REST APIs', 'AWS', 'Node.js'])
        self.assertEqual(result['missing_skills'], [])
        self.assertEqual(result['coverage_pct'], 100.0)

    def test_cicd_spacing_and_roadmap_skills_match(self):
        result = analyze_job_skills(
            'Python developer.\nAcquired roadmap skills: Kubernetes, CI/CD',
            None,
            'Knowledge of k8s and CI / CD required.',
        )
        self.assertEqual(result['matched_skills'], ['Kubernetes', 'CI/CD'])
        self.assertEqual(result['missing_skills'], [])

    def test_skill_boundaries_do_not_confuse_similar_technology_names(self):
        result = extract_job_skills(None, 'TypeScript and JavaScript. Go above and beyond in an agile team.')
        self.assertEqual(result['required_skills'], ['TypeScript', 'JavaScript', 'Agile'])
        self.assertFalse(skill_present('Java', 'JavaScript'))
        self.assertFalse(skill_present('C#', 'C++'))
        self.assertFalse(skill_present('Git', 'GitHub'))

    def test_absent_information_is_distinct_from_fully_covered_skills(self):
        for field in (None, '', 'N/A', 'None'):
            with self.subTest(field=field):
                result = analyze_job_skills('Python, Docker', field, 'Join our growing team!')
                self.assertEqual(result['required_skills'], [])
                self.assertEqual(result['skill_sources'], [])
                self.assertEqual(result['matched_skills'], [])
                self.assertEqual(result['missing_skills'], [])
                self.assertIsNone(result['coverage_pct'])

    def test_known_job_skills_and_empty_profile_have_zero_coverage(self):
        result = analyze_job_skills('', None, 'Python and Docker required.')
        self.assertEqual(result['matched_skills'], [])
        self.assertEqual(result['missing_skills'], ['Python', 'Docker'])
        self.assertEqual(result['coverage_pct'], 0.0)

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
