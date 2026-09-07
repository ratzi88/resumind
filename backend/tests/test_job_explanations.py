import json
import unittest

import numpy as np

from job_explanations import explain_job_match, posting_plain_text, related_passages, split_passages
from matching import compute_match_pct, redact_pii


class FakeTokenizer:
    def encode(self, text, **kwargs):
        return list(range(len(text.split()) + 2))


class FakeEmbedder:
    max_seq_length = 256
    tokenizer = FakeTokenizer()

    def __init__(self):
        self.calls = []

    def encode(self, texts, normalize_embeddings):
        self.calls.append(list(texts))
        vectors = np.array([[1.0, 0.0] if 'Python' in text else [0.0, 1.0] for text in texts])
        return vectors


class JobExplanationTest(unittest.TestCase):
    def explain(self, job=None, resume='Built Python services for internal teams.', acquired='', score=0.8, embedder=None):
        return explain_job_match(
            job or dict(job_id='42', description='Build Python services using Docker and Kubernetes.', skills_desc=None),
            resume, redact_pii(resume) + acquired, score, embedder or FakeEmbedder(),
        )

    def test_breakdown_uses_existing_fit_formula(self):
        result = self.explain(acquired='\nAcquired roadmap skills: Docker')
        breakdown = result['breakdown']
        self.assertEqual(result['match_pct'], compute_match_pct(0.8, 2, 3))
        self.assertEqual(breakdown['semantic_weight'], 0.75)
        self.assertEqual(breakdown['skill_weight'], 0.25)
        self.assertEqual(breakdown['semantic_points'], 60)
        self.assertEqual(breakdown['skill_points'], 16.67)
        self.assertEqual(breakdown['matched_count'], 2)
        self.assertEqual(breakdown['required_count'], 3)
        self.assertEqual(result['missing_skills'], ['Kubernetes'])

    def test_evidence_distinguishes_cv_from_acquired_progress(self):
        result = self.explain(acquired='\nAcquired roadmap skills: Docker')
        by_skill = {item['skill']: item for item in result['skill_evidence']}
        self.assertEqual(by_skill['Python']['source'], 'CV')
        self.assertIn('Built Python', by_skill['Python']['profile_evidence'])
        self.assertIn('Build Python', by_skill['Python']['job_evidence'])
        self.assertEqual(by_skill['Docker']['source'], 'Roadmap progress')
        self.assertIn('no explicit CV mention', by_skill['Docker']['profile_evidence'])
        self.assertIn('only if you have that experience', result['improvements'][0])
        self.assertNotIn('Kubernetes', by_skill)

    def test_alias_evidence_points_to_real_cv_text(self):
        result = self.explain(job=dict(job_id='1', skills_desc='PostgreSQL'), resume='Implemented Postgres storage for internal applications.')
        evidence = result['skill_evidence'][0]
        self.assertEqual(evidence['skill'], 'PostgreSQL')
        self.assertEqual(evidence['source'], 'CV')
        self.assertIn('Postgres', evidence['profile_evidence'])

    def test_no_skill_data_falls_back_to_semantic_only(self):
        result = self.explain(job=dict(job_id=7, description=None), score=0.721)
        self.assertEqual(result['job_id'], '7')
        self.assertEqual(result['match_pct'], 72.1)
        self.assertEqual(result['breakdown']['semantic_weight'], 1)
        self.assertEqual(result['breakdown']['skill_weight'], 0)
        self.assertIsNone(result['breakdown']['coverage_pct'])
        self.assertEqual(result['breakdown']['skill_points'], 0)
        self.assertEqual(result['semantic_evidence']['pairs'], [])

    def test_breakdown_is_bounded_like_matching(self):
        for score, expected in [(-0.5, 0), (1.2, 100)]:
            result = self.explain(job=dict(job_id='1'), score=score)
            self.assertEqual(result['match_pct'], expected)
            self.assertEqual(result['breakdown']['semantic_pct'], expected)

    def test_contact_details_redacted_before_excerpt_embedding_and_response(self):
        embedder = FakeEmbedder()
        result = self.explain(
            job=dict(job_id='2', description='Use Python, contact hiring@example.test or +972 54 123 4567.'),
            resume='Python developer: cv@example.test +972 52 123 4567.', embedder=embedder,
        )
        all_text = json.dumps([result, embedder.calls])
        self.assertNotIn('@example.test', all_text)
        self.assertNotIn('123 4567', all_text)
        self.assertIn('[email]', all_text)

    def test_token_diagnostics_remain_without_a_user_facing_warning(self):
        result = self.explain(resume='Python ' + 'experience ' * 270)
        self.assertTrue(result['input_window']['truncated'])
        self.assertEqual(result['input_window']['profile_tokens'], 273)
        self.assertEqual(result['input_window']['max_tokens'], 256)
        self.assertFalse(any('profile has' in note or 'tokens' in note for note in result['limitations']))
        self.assertFalse(self.explain()['input_window']['truncated'])

    def test_excerpt_similarity_is_separate_from_overall_score(self):
        result = self.explain(score=0.6)
        self.assertEqual(result['semantic_evidence']['pairs'][0]['similarity_pct'], 100)
        self.assertEqual(result['breakdown']['semantic_pct'], 60)
        self.assertIn('not an exact explanation', result['limitations'][0])

    def test_html_display_preserves_full_text_without_executing_markup(self):
        text = '<p>Python &amp; Docker</p><ul><li>Cloud experience</li></ul>'
        text += '<script>steal()</script><style>body{display:none}</style>'
        text += '<img src=x onerror=steal()>' + 'Saved detail. ' * 400 + 'END OF POSTING'
        result = posting_plain_text(text)
        self.assertIn('Python & Docker', result)
        self.assertIn('\n• Cloud experience', result)
        self.assertNotIn('steal', result)
        self.assertNotIn('display:none', result)
        self.assertNotIn('<img', result)
        self.assertTrue(result.endswith('END OF POSTING'))
        self.assertGreater(len(result), 4000)
        self.assertEqual(posting_plain_text(None), '')
        self.assertEqual(posting_plain_text('Cost < 10 & time > 2'), 'Cost < 10 & time > 2')

    def test_passages_are_bounded_deduplicated_and_sample_document_tail(self):
        lines = [f'Experience item {i}: delivered reliable infrastructure.' for i in range(100)]
        result = split_passages('\n'.join(lines))
        self.assertEqual(len(result), 32)
        self.assertEqual(result[0], lines[0])
        self.assertEqual(result[-1], lines[-1])
        self.assertEqual(result, split_passages('\n'.join(lines)))
        self.assertEqual(split_passages(lines[0] + '\n' + lines[0]), [lines[0]])
        self.assertEqual(split_passages('\n'.join(lines), limit=1), [lines[0]])
        self.assertTrue(all(len(piece) <= 320 for piece in split_passages('x' * 2000)))
        for args in [dict(limit=0), dict(width=0)]:
            with self.assertRaises(ValueError):
                split_passages('some input', **args)

    def test_related_excerpts_are_exact_unique_and_sorted(self):
        resume = 'Created Python applications for internal teams.\nAutomated Docker container deployments.'
        posting = 'Seeking Python engineers to build applications.\nMaintain Docker containers for customers.'
        result = related_passages(resume, posting, FakeEmbedder())
        self.assertEqual(len(result['pairs']), 2)
        for pair in result['pairs']:
            self.assertIn(pair['resume_excerpt'], resume)
            self.assertIn(pair['job_excerpt'], posting)
        self.assertEqual(len({pair['resume_excerpt'] for pair in result['pairs']}), 2)
        self.assertEqual(len({pair['job_excerpt'] for pair in result['pairs']}), 2)
        self.assertEqual([p['similarity_pct'] for p in result['pairs']], [100, 100])

    def test_related_passages_skip_empty_text_and_cap_inference(self):
        embedder = FakeEmbedder()
        self.assertEqual(related_passages('', 'A long description with useful context.', embedder)['pairs'], [])
        self.assertEqual(embedder.calls, [])
        lines = '\n'.join(f'Python experience item number {i} with outcomes.' for i in range(100))
        result = related_passages(lines, lines, embedder)
        self.assertEqual(len(embedder.calls[0]), 64)
        self.assertEqual(len(result['pairs']), 3)


if __name__ == '__main__':
    unittest.main()
