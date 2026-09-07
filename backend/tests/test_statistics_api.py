import unittest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

import api


class StatisticsApiTest(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(api.app)
        api.app.dependency_overrides[api.get_current_user_id] = lambda: 701
        self.addCleanup(api.app.dependency_overrides.clear)

    def test_statistics_use_all_recommended_jobs_and_do_not_write_data(self):
        rows = [
            {'job_id': '1', 'raw_score': 0.8, 'skills_desc': 'Python; Docker'},
            {'job_id': '2', 'raw_score': 0.7, 'skills_desc': 'Docker; Kubernetes'},
        ]
        database = MagicMock()
        embedder = MagicMock()
        embedder.encode.return_value.tolist.return_value = [0.1, 0.2]
        with patch.object(api, 'get_db', return_value=database), \
             patch.object(api, '_load_matching_profile', return_value={'career_text': 'Python developer'}), \
             patch.object(api, 'get_embedder', return_value=embedder), \
             patch.object(api, '_query_job_matches', return_value=(rows, set())) as query:
            response = self.client.get('/api/user/statistics')

        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result['total_jobs'], 2)
        self.assertEqual(result['skills_to_strengthen'][0]['name'], 'Docker')
        self.assertEqual(result['skills_to_strengthen'][0]['percentage'], 100.0)
        self.assertEqual(result['strongest_skills'][0]['name'], 'Python')
        self.assertEqual(response.headers['cache-control'], 'no-store')
        embedder.encode.assert_called_once_with('Python developer', normalize_embeddings=True)
        query.assert_called_once_with(database.cursor.return_value, [0.1, 0.2])
        database.commit.assert_not_called()
        database.close.assert_called_once()

    def test_statistics_require_authentication_before_database_access(self):
        api.app.dependency_overrides.clear()
        with patch.object(api, 'get_db') as database:
            self.assertIn(self.client.get('/api/user/statistics').status_code, (401, 403))
            database.assert_not_called()


if __name__ == '__main__':
    unittest.main()
