import unittest
from urllib.parse import parse_qs, urlsplit

from learning_resources import RESOURCE_CATALOG, learning_resources_for_skill, with_learning_resources
from matching import JOB_SKILL_NAMES


class LearningResourcesTest(unittest.TestCase):
    def test_common_skill_has_learning_path_and_official_tutorial(self):
        links = learning_resources_for_skill('Docker')
        self.assertEqual({link['url'] for link in links}, {
            'https://roadmap.sh/docker', 'https://docs.docker.com/get-started/',
        })
        self.assertEqual({link['kind'] for link in links}, {'Learning path', 'Official guide'})

    def test_aliases_and_roadmap_labels_share_relevant_resources(self):
        for alias, canonical in [('k8s', 'Kubernetes'), ('Postgres', 'PostgreSQL'),
                                 ('Linux CLI', 'Linux'), ('JavaScript (ES6+)', 'JavaScript'),
                                 ('Bash & Terminal', 'Bash'), ('Apache Kafka', 'Kafka'),
                                 ('Testing (JUnit)', 'JUnit')]:
            with self.subTest(alias=alias):
                self.assertEqual(learning_resources_for_skill(alias), learning_resources_for_skill(canonical))

    def test_every_extracted_job_skill_has_resources(self):
        for skill in JOB_SKILL_NAMES:
            with self.subTest(skill=skill):
                self.assertTrue(learning_resources_for_skill(skill))
                self.assertTrue(any(link['kind'] != 'Search' for link in learning_resources_for_skill(skill)))

    def test_unknown_skill_has_honest_encoded_search_fallback(self):
        label = 'Special Tool C++ & x=y/#'
        links = learning_resources_for_skill(label)
        self.assertTrue(all(link['kind'] == 'Search' for link in links))
        self.assertEqual(parse_qs(urlsplit(links[0]['url']).query)['q'], [f'site:roadmap.sh {label}'])
        self.assertEqual(urlsplit(links[0]['url']).netloc, 'www.google.com')

    def test_exact_matching_does_not_confuse_java_and_javascript(self):
        java = learning_resources_for_skill('Java')
        javascript = learning_resources_for_skill('JavaScript')
        self.assertNotEqual(java, javascript)
        self.assertIn('https://roadmap.sh/java', [link['url'] for link in java])

    def test_resources_are_https_deduplicated_and_have_display_metadata(self):
        for name in RESOURCE_CATALOG:
            links = learning_resources_for_skill(name)
            self.assertLessEqual(len(links), 3)
            self.assertEqual(len({link['url'] for link in links}), len(links))
            for link in links:
                url = urlsplit(link['url'])
                self.assertEqual(url.scheme, 'https')
                self.assertFalse(url.username or url.password)
                self.assertEqual(link['source'], url.hostname)
                self.assertTrue(link['title'])

    def test_resource_attachment_does_not_change_progress_or_expose_profile(self):
        skills = [dict(skill_name='Python', stage=1, impact=10, acquired=True)]
        result = with_learning_resources(skills)
        self.assertEqual({k: v for k, v in result[0].items() if k != 'learning_resources'}, skills[0])
        self.assertNotIn('learning_resources', skills[0])
        self.assertTrue(result[0]['learning_resources'])
        self.assertEqual(with_learning_resources([]), [])

    def test_mutating_a_response_does_not_mutate_the_catalog(self):
        first = learning_resources_for_skill('Docker')
        original = first[0]['url']
        first[0]['url'] = 'https://invalid.example/'
        first.clear()
        self.assertEqual(learning_resources_for_skill('Docker')[0]['url'], original)


if __name__ == '__main__':
    unittest.main()
