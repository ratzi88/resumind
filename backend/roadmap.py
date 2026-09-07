"""Roadmap progress grounded in the CV with explicit user overrides."""

from matching import normalize_skill_name, skill_present


# These are shown as separate roadmap cards because they are useful concepts to
# explain independently, but progress is shared: practical Git use normally
# includes working with a hosted repository such as GitHub.
LINKED_ROLE_SKILLS = (
    frozenset(("Git", "GitHub")),
)


def linked_role_skill_names(skill_name: str) -> tuple[str, ...]:
    key = normalize_skill_name(skill_name)
    for group in LINKED_ROLE_SKILLS:
        if key in {normalize_skill_name(name) for name in group}:
            return tuple(sorted(group))
    return (skill_name,)


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

    # Keep linked cards consistent. An explicit user choice has priority over
    # CV detection; otherwise either saved skill or either CV term acquires both.
    for group in LINKED_ROLE_SKILLS:
        linked = [
            skill for skill in resolved
            if normalize_skill_name(skill['skill_name']) in {
                normalize_skill_name(name) for name in group
            }
        ]
        if len(linked) < 2:
            continue
        detected = any(skill_present(name, resume_text) for name in group)
        manual = [skill for skill in linked if skill.get('manual_override')]
        acquired = (
            any(skill['acquired'] for skill in manual)
            if manual
            else detected or any(skill['acquired'] for skill in linked)
        )
        for skill in linked:
            skill['detected_in_resume'] = detected
            skill['acquired'] = acquired
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
