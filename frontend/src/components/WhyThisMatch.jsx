import { useEffect, useState } from 'react'
import { useAuth } from '../lib/AuthContext.jsx'

export default function WhyThisMatch({ job }) {
  const { token } = useAuth()
  const [expanded, setExpanded] = useState(false)
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [retry, setRetry] = useState(0)

  useEffect(() => {
    if (!expanded || !token) return
    const controller = new AbortController()
    setData(null)
    setError(null)
    setLoading(true)
    fetch(`/api/user/jobs/${encodeURIComponent(job.job_id)}/explanation`, {
      headers: { Authorization: `Bearer ${token}` }, signal: controller.signal,
    })
      .then(async response => {
        let result
        try { result = JSON.parse(await response.text()) }
        catch { throw new Error('The server returned an unexpected response. Please try again.') }
        if (!response.ok) throw new Error(typeof result.detail === 'string' ? result.detail : 'Could not explain this match.')
        return result
      })
      .then(result => { if (!controller.signal.aborted) setData(result) })
      .catch(err => { if (!controller.signal.aborted) setError(err.message) })
      .finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [expanded, token, job.job_id, retry])

  return (
    <section className="rounded-xl border border-brand-400/30 bg-brand-500/5 p-4">
      <button className="w-full flex items-center justify-between gap-3 text-sm font-semibold text-fg text-left rounded focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-400"
        aria-expanded={expanded} aria-controls={`why-match-${job.job_id}`} onClick={() => setExpanded(value => !value)}>
        Why this match? <span aria-hidden="true">{expanded ? '−' : '+'}</span>
      </button>
      <p className="mt-1 text-xs text-muted">See score contributions, related experience and ways to strengthen your CV.</p>
      {expanded && <div id={`why-match-${job.job_id}`} className="mt-4 space-y-4">
        {loading && <p role="status" className="text-sm text-muted">Comparing your CV with this posting…</p>}
        {error && <div role="alert" className="text-sm text-red-400 space-y-2">
          <p>{error}</p><button className="btn-ghost" onClick={() => setRetry(value => value + 1)}>Retry explanation</button>
        </div>}
        {data && <>
          <p className="text-sm text-fg">{data.summary}</p>
          <dl className="rounded-xl border border-line bg-surface/60 p-3 text-xs space-y-2">
            <div className="flex justify-between gap-3"><dt className="text-muted">Semantic similarity ({Math.round(data.breakdown.semantic_weight * 100)}% weight)</dt><dd className="text-fg tabular-nums whitespace-nowrap">{data.breakdown.semantic_pct}% → {data.breakdown.semantic_points} pts</dd></div>
            <div className="flex justify-between gap-3"><dt className="text-muted">Skill coverage ({Math.round(data.breakdown.skill_weight * 100)}% weight)</dt><dd className="text-fg tabular-nums whitespace-nowrap">{data.breakdown.coverage_pct == null ? 'Not available' : `${data.breakdown.coverage_pct}% → ${data.breakdown.skill_points} pts`}</dd></div>
            <div className="flex justify-between gap-3 border-t border-line pt-2 font-semibold"><dt>Current estimated fit</dt><dd>{data.match_pct}%</dd></div>
          </dl>
          {Math.abs(data.match_pct - job.match_pct) > 0.05 && <p className="text-xs text-amber-600 dark:text-amber-300">Your profile has changed since these jobs loaded. Refresh matches to update the list.</p>}
          <p className="text-[11px] text-muted">Contributions are rounded. This score estimates relevance, not your chance of being hired.</p>

          <div className="space-y-2">
            <h4 className="text-xs font-semibold uppercase tracking-wide text-fg">Related CV and job excerpts</h4>
            <p className="text-xs text-muted">The same embedding model compares short excerpts separately. These examples do not add up to—or fully explain—the overall semantic score.</p>
            {data.semantic_evidence.pairs.length === 0 && <p className="text-xs text-muted">Not enough usable text to show related excerpts.</p>}
            {data.semantic_evidence.pairs.map((pair, i) => <div key={i} className="rounded-xl border border-line bg-surface/60 p-3 space-y-2">
              <p className="text-[11px] text-muted">Excerpt similarity: {pair.similarity_pct}% · not a score contribution</p>
              <blockquote className="text-xs text-fg leading-relaxed whitespace-pre-wrap break-words"><span className="font-semibold text-brand-500">Your CV: </span>{pair.resume_excerpt}</blockquote>
              <blockquote className="text-xs text-fg leading-relaxed whitespace-pre-wrap break-words"><span className="font-semibold text-brand-500">Job posting: </span>{pair.job_excerpt}</blockquote>
            </div>)}
          </div>

          {data.skill_evidence.length > 0 && <details className="rounded-xl border border-line p-3">
            <summary className="text-xs font-semibold text-fg cursor-pointer">Evidence for covered skills ({data.skill_evidence.length})</summary>
            <div className="mt-3 space-y-3">{data.skill_evidence.map(item => <div key={item.skill} className="text-xs space-y-1">
              <p className="font-semibold text-emerald-600 dark:text-emerald-300">{item.skill} · {item.source}</p>
              <blockquote className="text-muted break-words">{item.profile_evidence}</blockquote>
              {item.job_evidence && <blockquote className="text-muted break-words"><span className="font-medium">Posting: </span>{item.job_evidence}</blockquote>}
            </div>)}</div>
          </details>}

          <div className="space-y-2">
            <h4 className="text-xs font-semibold uppercase tracking-wide text-fg">How to strengthen your CV</h4>
            {data.improvements.map((advice, i) => <p key={i} className="text-xs text-muted leading-relaxed">{advice}</p>)}
          </div>
          <details className="text-xs text-muted">
            <summary className="cursor-pointer font-medium">How this explanation works</summary>
            <div className="mt-2 space-y-2">
              <p>Model: {data.embedding_model}. Compared up to {data.semantic_evidence.resume_passages} CV excerpts with {data.semantic_evidence.job_passages} posting excerpts. No AI-generated reasoning or invented experience.</p>
              {data.limitations.map((note, i) => <p key={i}>{note}</p>)}
            </div>
          </details>
        </>}
      </div>}
    </section>
  )
}
