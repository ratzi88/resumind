import { useEffect, useId, useRef } from 'react'

export function safeApplyUrl(value) {
  try {
    const url = new URL(value)
    return ['https:', 'http:'].includes(url.protocol) && !url.username && !url.password ? url.href : null
  } catch { return null }
}

function salaryDetails(job) {
  const amount = value => value == null || value === '' || !Number.isFinite(Number(value)) ? null : Number(value).toLocaleString()
  const low = amount(job.min_salary), high = amount(job.max_salary), median = amount(job.med_salary)
  const range = low && high ? `${low}–${high}` : median ? `${median} (median)` : low ? `From ${low}` : high ? `Up to ${high}` : null
  return range ? `${job.currency || 'Currency unspecified'} ${range}${job.pay_period ? ` / ${job.pay_period}` : ''}` : 'Not provided'
}

function formatPostingDate(value) {
  if (value == null || value === '') return null
  const number = Number(value)
  if (!Number.isFinite(number) || number <= 0) return null
  const date = new Date(number < 1e12 ? number * 1000 : number)
  return Number.isNaN(date.getTime()) ? null : date.toLocaleDateString()
}

export default function JobDetailsDialog({ job, onClose }) {
  const dialogRef = useRef(null)
  const headingId = useId()
  const applyUrl = safeApplyUrl(job.apply_url)
  useEffect(() => {
    const dialog = dialogRef.current
    const previouslyFocused = document.activeElement
    const previousOverflow = document.body.style.overflow
    dialog.showModal()
    document.body.style.overflow = 'hidden'
    return () => {
      if (dialog.open) dialog.close()
      document.body.style.overflow = previousOverflow
      if (previouslyFocused?.isConnected) previouslyFocused.focus()
    }
  }, [])
  const metadata = [
    ['Company', job.company || 'Not provided'], ['Location', job.location || 'Not provided'],
    ['Work arrangement', job.remote === true ? 'Remote allowed' : job.remote === false ? 'Remote not indicated' : 'Not provided'],
    ['Work type', job.work_type || 'Not provided'], ['Experience level', job.experience_level || 'Not provided'],
    ['Salary', salaryDetails(job)], ['Compensation type', job.compensation_type], ['Industry', job.industry],
    ['Company size (source category)', job.company_size], ['Employee count', job.employee_count],
    ['Posted', formatPostingDate(job.listed_time)], ['Expiry', formatPostingDate(job.expiry)],
    ['Closed', formatPostingDate(job.closed_time)], ['Job ID', job.job_id],
  ].filter(([, value]) => value !== null && value !== undefined && value !== '')
  return (
    <dialog ref={dialogRef} aria-labelledby={headingId} onClose={event => { if (!event.currentTarget.open) onClose() }}
      onClick={event => { if (event.target === event.currentTarget) onClose() }}
      className="m-auto w-[92vw] max-w-3xl max-h-[88vh] overflow-y-auto rounded-2xl border border-line bg-bg text-fg p-0 shadow-2xl backdrop:bg-black/60">
      <div>
        <header className="sticky top-0 z-10 border-b border-line bg-bg p-5 flex items-start justify-between gap-4">
          <div className="min-w-0"><p className="text-xs uppercase tracking-wide text-muted">Full job details</p><h2 id={headingId} className="mt-1 text-xl font-semibold break-words">{job.title}</h2></div>
          <button autoFocus onClick={onClose} className="btn-ghost shrink-0" aria-label="Close job details">Close</button>
        </header>
        <div className="p-5 sm:p-6 space-y-6">
          <dl className="grid sm:grid-cols-2 gap-4 text-sm">{metadata.map(([label, value]) => <div key={label} className="min-w-0"><dt className="text-xs text-muted">{label}</dt><dd className="mt-1 text-fg break-words">{value}</dd></div>)}</dl>
          <section><h3 className="text-sm font-semibold mb-2">Full saved description</h3><p className="whitespace-pre-wrap break-words text-sm text-muted leading-relaxed">{job.description_text || job.description || 'No description was provided for this posting.'}</p></section>
          {(job.skills_text || job.skills_desc) && <section><h3 className="text-sm font-semibold mb-2">Skills and requirements supplied by the posting</h3><p className="whitespace-pre-wrap break-words text-sm text-muted leading-relaxed">{job.skills_text || job.skills_desc}</p></section>}
          {job.match_details?.required_skills?.length > 0 && <section><h3 className="text-sm font-semibold mb-2">Skills detected in the posting</h3><div className="flex flex-wrap gap-2">{job.match_details.required_skills.map(skill => <span className="chip" key={skill}>{skill}</span>)}</div><p className="mt-2 text-xs text-muted">Mentions can include preferred skills or alternatives, not just mandatory requirements.</p></section>}
          {job.benefits?.length > 0 && <section><h3 className="text-sm font-semibold mb-2">Benefits</h3><ul className="list-disc pl-5 text-sm text-muted space-y-1">{job.benefits.map((benefit, i) => <li key={i}>{benefit}</li>)}</ul></section>}
          <p className="rounded-xl border border-line bg-surface-2/30 p-3 text-xs text-muted">This shows all information saved in ResuMind. Imported descriptions may be shortened, and the original listing may have changed or closed. Check the source before applying.</p>
          <div className="flex flex-wrap gap-2">{applyUrl ? <a href={applyUrl} target="_blank" rel="noopener noreferrer" className="btn-primary">Apply on original site ↗</a> : <p className="text-sm text-muted">No valid application link was provided.</p>}<button onClick={onClose} className="btn-ghost">Back to matches</button></div>
        </div>
      </div>
    </dialog>
  )
}
