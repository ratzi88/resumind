"""Evidence for a match, without changing ranking or inventing model reasoning."""

import re
from html.parser import HTMLParser

import numpy as np

from matching import analyze_job_skills, compute_match_pct, evidence_for_skill, redact_pii


class _PostingText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.hidden += 1
        elif not self.hidden and tag in ('p', 'div', 'br', 'li', 'ul', 'ol', 'h1', 'h2', 'h3', 'tr'):
            self.parts.append('\n• ' if tag == 'li' else '\n')

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self.hidden = max(0, self.hidden - 1)
        elif not self.hidden and tag in ('p', 'div', 'li', 'ul', 'ol', 'h1', 'h2', 'h3', 'tr'):
            self.parts.append('\n')

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def posting_plain_text(value: str | None) -> str:
    parser = _PostingText()
    parser.feed(str(value or ''))
    parser.close()
    text = re.sub(r'[ \t\r\f\v]+', ' ', ''.join(parser.parts))
    return re.sub(r'\n\s*\n', '\n\n', text).strip()


def split_passages(text: str, limit: int = 32, width: int = 320) -> list[str]:
    """Bound inference work and sample across the whole available document."""

    if limit < 1 or width < 20:
        raise ValueError('Passage limit must be positive and width at least 20.')
    pieces = []
    for line in re.split(r'\n+|(?<=[.!?])\s+', text):
        line = line.strip(' •\t')
        while len(line) > width:
            cut = line.rfind(' ', 0, width + 1)
            cut = cut if cut > 0 else width
            pieces.append(line[:cut].strip())
            line = line[cut:].strip()
        if len(line) >= 20:
            pieces.append(line)
    pieces = list(dict.fromkeys(piece for piece in pieces if len(piece) >= 20))
    if len(pieces) > limit:
        pieces = pieces[:1] if limit == 1 else [pieces[round(i * (len(pieces) - 1) / (limit - 1))] for i in range(limit)]
    return pieces


def related_passages(resume_text: str, job_text: str, embedder) -> dict:
    resume = split_passages(resume_text)
    posting = split_passages(job_text)
    if not resume or not posting:
        return {'pairs': [], 'resume_passages': len(resume), 'job_passages': len(posting)}
    vectors = np.asarray(embedder.encode(resume + posting, normalize_embeddings=True))
    similarities = vectors[:len(resume)] @ vectors[len(resume):].T
    # Use each excerpt once so several near-identical job sentences do not
    # crowd out other experience. These are a separate illustrative comparison,
    # not additive contributions to the stored whole-document similarity.
    candidates = sorted(
        ((float(similarities[i, j]), i, j) for i in range(len(resume)) for j in range(len(posting))),
        key=lambda item: (-item[0], item[1], item[2]),
    )
    used_resume, used_job, pairs = set(), set(), []
    for score, i, j in candidates:
        if i in used_resume or j in used_job or score <= 0:
            continue
        pairs.append({'resume_excerpt': resume[i], 'job_excerpt': posting[j], 'similarity_pct': round(min(score, 1) * 100, 1)})
        used_resume.add(i)
        used_job.add(j)
        if len(pairs) == 3:
            break
    return {'pairs': pairs, 'resume_passages': len(resume), 'job_passages': len(posting)}


def explain_job_match(job: dict, resume_text: str, career_text: str, raw_score: float, embedder) -> dict:
    resume = redact_pii(resume_text)
    description = redact_pii(posting_plain_text(job.get('description')))
    skills_text = redact_pii(posting_plain_text(job.get('skills_desc')))
    analysis = analyze_job_skills(career_text, job.get('skills_desc'), job.get('description'))
    matched, missing = analysis['matched_skills'], analysis['missing_skills']
    required_count = len(analysis['required_skills'])
    semantic_pct = max(0.0, min(1.0, float(raw_score))) * 100
    coverage = len(matched) / required_count * 100 if required_count else None
    evidence = []
    for name in matched:
        cv_excerpt = evidence_for_skill(name, resume)
        job_excerpt = evidence_for_skill(name, description) or evidence_for_skill(name, skills_text)
        evidence.append({
            'skill': name,
            'source': 'CV' if cv_excerpt else 'Roadmap progress',
            'profile_evidence': cv_excerpt or f'{name} is marked acquired in your roadmap; no explicit CV mention was found.',
            'job_evidence': job_excerpt,
        })

    max_tokens = int(embedder.max_seq_length)
    # Count without truncation; the full token list is never fed into the model.
    token_count = len(embedder.tokenizer.encode(career_text, add_special_tokens=True, truncation=False, verbose=False))
    truncated = token_count > max_tokens
    limitations = [
        'Related excerpts are a separate semantic comparison, not an exact explanation or percentage breakdown of the embedding model’s reasoning.',
        'A missing mention does not prove you lack a skill. Posting mentions may be preferred skills or alternatives.',
        'Estimated fit is a relevance score, not a probability of being hired.',
        'Job similarity uses a stored embedding; the saved posting and original listing may be shortened or outdated.',
    ]
    improvements = []
    if missing:
        improvements.append('For ' + ', '.join(missing[:5]) + ': add a concrete project or work example only if you have that experience; otherwise use Build roadmap to plan your learning.')
    roadmap_only = [item['skill'] for item in evidence if item['source'] == 'Roadmap progress']
    if roadmap_only:
        improvements.append('Your roadmap records ' + ', '.join(roadmap_only[:5]) + ', but your CV does not name them. If you can demonstrate them, describe where you used them and what you achieved.')
    improvements.append('Describe relevant responsibilities, tools and measurable outcomes clearly. Do not add unsupported experience or repeat keywords just to raise the score.')

    return {
        'job_id': str(job['job_id']),
        'match_pct': compute_match_pct(raw_score, len(matched), required_count),
        'summary': (f'Your profile covers {len(matched)} of {required_count} skills detected in this posting.'
                    if required_count else 'No reliable skill list was detected in this posting, so fit uses semantic similarity alone.'),
        'breakdown': {
            'semantic_pct': round(semantic_pct, 2),
            'coverage_pct': round(coverage, 2) if coverage is not None else None,
            'semantic_weight': 0.75 if required_count else 1.0,
            'skill_weight': 0.25 if required_count else 0.0,
            'semantic_points': round(semantic_pct * (0.75 if required_count else 1.0), 2),
            'skill_points': round(coverage * 0.25, 2) if coverage is not None else 0.0,
            'matched_count': len(matched), 'required_count': required_count,
        },
        'skill_evidence': evidence,
        'missing_skills': missing,
        'semantic_evidence': related_passages(resume, '\n'.join(filter(None, [description, skills_text])), embedder),
        'input_window': {'profile_tokens': token_count, 'max_tokens': max_tokens, 'truncated': truncated},
        'improvements': improvements,
        'limitations': limitations,
    }
