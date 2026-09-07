"""Roadmap progress grounded in the CV with explicit user overrides."""

from matching import normalize_skill_name, skill_present


def resolve_role_progress(skills: list[dict], resume_text: str) -> list[dict]:
    resolved = []
    for row in skills:
        skill = dict(row)
        detected = skill_present(skill['skill_name'], resume_text)
        skill['detected_in_resume'] = detected
        if not skill.get('manual_override'):
            skill['acquired'] = bool(skill.get('acquired')) or detected
        else:
            skill['acquired'] = bool(skill.get('acquired'))
        resolved.append(skill)
    return resolved


def build_job_roadmap(analysis: dict, catalog: list[dict], progress: list[dict]) -> list[dict]:
    """Build a plan from this posting's skills, using known learning stages."""

    metadata = {}
    for row in sorted(catalog, key=lambda row: (row['stage'], row['skill_name'])):
        metadata.setdefault(normalize_skill_name(row['skill_name']), row)
    saved = {normalize_skill_name(row['skill_name']): row for row in progress}
    matched = {normalize_skill_name(name) for name in analysis['matched_skills']}
    skills = []
    for name in analysis['required_skills']:
        key = normalize_skill_name(name)
        source = metadata.get(key, {})
        override = saved.get(key)
        acquired = bool(override['acquired']) if override else key in matched
        skills.append({
            'skill_name': name,
            'category': source.get('category', 'Job skills'),
            'stage': source.get('stage', 2),
            # Equal weight keeps job progress aligned with skill coverage.
            'impact': 1,
            'acquired': acquired,
        })
    return sorted(skills, key=lambda row: (row['stage'], row['skill_name'].casefold()))


def apply_job_progress(analysis: dict, skills: list[dict]) -> dict:
    """Keep the job coverage panel consistent with manually tracked learning."""

    acquired = {row['skill_name'] for row in skills if row['acquired']}
    matched = [name for name in analysis['required_skills'] if name in acquired]
    missing = [name for name in analysis['required_skills'] if name not in acquired]
    details = []
    for detail in analysis['skill_details']:
        present = detail['name'] in acquired
        details.append({
            **detail,
            'status': 'matched' if present else 'missing',
            'evidence': (detail['evidence'] or 'Marked as learned for this job.') if present else '',
        })
    return {
        **analysis,
        'matched_skills': matched,
        'missing_skills': missing,
        'skill_details': details,
        'coverage_pct': round(len(matched) / len(skills) * 100, 1) if skills else None,
    }
