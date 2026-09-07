import unittest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

import api


class RoadmapApiTest(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(api.app)
        api.app.dependency_overrides[api.get_current_user_id] = lambda: 701
        self.addCleanup(api.app.dependency_overrides.clear)

    def test_toggling_git_saves_the_same_progress_for_github(self):
        database = MagicMock()
        cursor = database.cursor.return_value
        cursor.fetchone.side_effect = [{'desired_role': 'devops'}, {'exists': 1}]
        cursor.fetchall.return_value = [{'skill_name': 'Git'}, {'skill_name': 'GitHub'}]

        with patch.object(api, 'get_db', return_value=database), \
             patch.object(api.psycopg2.extras, 'execute_values') as execute_values:
            response = self.client.post(
                '/api/user/skills/toggle',
                data={'skill_name': 'Git', 'acquired': 'true'},
            )

        self.assertEqual(response.status_code, 200)
        records = execute_values.call_args.args[2]
        self.assertEqual(
            set(records),
            {(701, 'devops', 'Git', True, True), (701, 'devops', 'GitHub', True, True)},
        )
        database.commit.assert_called_once()
        database.close.assert_called_once()

    def test_toggling_cicd_only_updates_cicd(self):
        database = MagicMock()
        cursor = database.cursor.return_value
        cursor.fetchone.side_effect = [{'desired_role': 'devops'}, {'exists': 1}]
        cursor.fetchall.return_value = [{'skill_name': 'CI/CD'}]

        with patch.object(api, 'get_db', return_value=database), \
             patch.object(api.psycopg2.extras, 'execute_values') as execute_values:
            response = self.client.post(
                '/api/user/skills/toggle',
                data={'skill_name': 'CI/CD', 'acquired': 'true'},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            execute_values.call_args.args[2],
            [(701, 'devops', 'CI/CD', True, True)],
        )


if __name__ == '__main__':
    unittest.main()
