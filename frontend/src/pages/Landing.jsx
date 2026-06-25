import { Link } from 'react-router-dom'
import { useAuth } from '../lib/AuthContext.jsx'

function AuthLink({ to, children, className }) {
  const { token } = useAuth()
  return <Link to={token ? to : '/login'} className={className}>{children}</Link>
}

export default function Landing() {
  return (
    <>
      <Hero />
      <Flows />
      <HowItWorks />
      <Stats />
      <CTA />
    </>
  )
}

function Hero() {
  return (
    <section className="relative overflow-hidden">
      <div className="absolute inset-0 bg-grid-fade pointer-events-none" />
      <div className="absolute inset-0 bg-grid opacity-40 [mask-image:radial-gradient(ellipse_at_top,black,transparent_70%)]" />
      <div className="relative mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 pt-20 pb-24 sm:pt-28 sm:pb-32">
        <div className="max-w-3xl">
          <span className="chip mb-5">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
            AI-powered career platform
          </span>
          <h1 className="text-4xl sm:text-6xl font-extrabold tracking-tight text-fg leading-[1.05]">
            Smart Resumes.
            <br />
            <span className="bg-gradient-to-r from-brand-500 via-brand-400 to-brand-300 bg-clip-text text-transparent">
              Smarter Careers.
            </span>
          </h1>
          <p className="mt-6 text-lg text-muted max-w-2xl">
            Upload your CV, get matched to the jobs that actually fit, and follow a
            personalized roadmap that closes the skill gaps holding you back — all in
            one place, powered by local AI.
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-3">
            <AuthLink to="/resume" className="btn-primary">
              Upload your CV
              <Arrow />
            </AuthLink>
            <AuthLink to="/jobs" className="btn-ghost">
              Explore matched jobs
            </AuthLink>
          </div>
          <div className="mt-10 flex flex-wrap gap-2">
            <span className="chip">Qwen 3.5 80b</span>
            <span className="chip">Sentence-BERT</span>
            <span className="chip">PGVector RAG</span>
            <span className="chip">English-only · bias-aware</span>
          </div>
        </div>

        <FloatingMockup />
      </div>
    </section>
  )
}

function Arrow() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M5 12h14M13 5l7 7-7 7" />
    </svg>
  )
}

function FloatingMockup() {
  return (
    <div className="hidden lg:block absolute right-8 top-24 w-[420px]">
      <div className="card rotate-2 hover:rotate-0 transition-transform duration-500">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs uppercase tracking-wider text-muted">Match score</p>
            <p className="text-4xl font-bold text-fg mt-1">87<span className="text-brand-400">%</span></p>
          </div>
          <span className="chip border-emerald-400/40 text-emerald-500 dark:text-emerald-300">Strong fit</span>
        </div>
        <div className="mt-5 h-2 rounded-full bg-surface-2 overflow-hidden">
          <div className="h-full w-[87%] bg-gradient-to-r from-brand-400 to-emerald-400" />
        </div>
        <p className="mt-4 text-sm text-muted">Backend Engineer · Stripe</p>
        <div className="mt-4 flex flex-wrap gap-1.5">
          {['Python', 'PostgreSQL', 'Docker', '+REST'].map((s) => (
            <span key={s} className="chip">{s}</span>
          ))}
        </div>
      </div>
      <div className="card mt-4 -rotate-1 hover:rotate-0 transition-transform duration-500">
        <p className="text-xs uppercase tracking-wider text-muted">Next on your roadmap</p>
        <p className="text-base font-semibold text-fg mt-1">Learn Kubernetes basics</p>
        <p className="mt-1 text-sm text-muted">+12% predicted match boost</p>
      </div>
    </div>
  )
}

function Flows() {
  const flows = [
    {
      step: '01',
      title: 'Upload or build your CV',
      desc: 'Drop a PDF or fill a guided form — we convert it to a clean YAML profile and a polished PDF you can keep.',
      to: '/resume',
      cta: 'Go to Resume',
      icon: (
        <svg className="h-6 w-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
          <path d="M6 4h9l3 3v13H6z" strokeLinejoin="round" />
          <path d="M9 12h6M9 16h4" strokeLinecap="round" />
        </svg>
      ),
    },
    {
      step: '02',
      title: 'See jobs that actually fit',
      desc: 'Semantic vector matching surfaces only roles above an 80% match — with a transparent breakdown of why.',
      to: '/jobs',
      cta: 'Browse Jobs',
      icon: (
        <svg className="h-6 w-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
          <rect x="3" y="6" width="18" height="14" rx="2" />
          <path d="M8 6V4h8v2" />
        </svg>
      ),
    },
    {
      step: '03',
      title: 'Follow your roadmap',
      desc: 'Personal skill tree shows the gaps. Check off what you learn and the system updates your CV and re-ranks jobs.',
      to: '/roadmap',
      cta: 'See Roadmap',
      icon: (
        <svg className="h-6 w-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
          <path d="M5 6h6M5 12h14M5 18h10" strokeLinecap="round" />
          <circle cx="3" cy="6" r="1" fill="currentColor" />
          <circle cx="3" cy="12" r="1" fill="currentColor" />
          <circle cx="3" cy="18" r="1" fill="currentColor" />
        </svg>
      ),
    },
  ]

  return (
    <section className="py-20 sm:py-28">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="max-w-2xl">
          <h2 className="section-title">Three flows. One career engine.</h2>
          <p className="section-sub">
            Every step feeds the next. Improve your CV, the matches update. Acquire a skill,
            the matches update again.
          </p>
        </div>
        <div className="mt-12 grid md:grid-cols-3 gap-6">
          {flows.map((f) => (
            <AuthLink
              to={f.to}
              key={f.step}
              className="card group hover:border-brand-400/40 hover:shadow-glow transition-all"
            >
              <div className="flex items-start justify-between">
                <div className="h-11 w-11 rounded-xl grid place-items-center bg-brand-500/15 text-brand-500 dark:text-brand-300 border border-brand-400/20">
                  {f.icon}
                </div>
                <span className="text-xs font-mono text-subtle">{f.step}</span>
              </div>
              <h3 className="mt-5 text-xl font-semibold text-fg">{f.title}</h3>
              <p className="mt-2 text-muted text-sm">{f.desc}</p>
              <p className="mt-5 inline-flex items-center gap-1.5 text-sm font-medium text-brand-500 dark:text-brand-300 group-hover:text-brand-400">
                {f.cta} <Arrow />
              </p>
            </AuthLink>
          ))}
        </div>
      </div>
    </section>
  )
}

function HowItWorks() {
  const steps = [
    {
      title: 'Vectorize',
      desc: 'Your CV and job descriptions are embedded with Sentence-BERT (all-MiniLM-L6-v2) and stored in PGVector.',
    },
    {
      title: 'Match',
      desc: 'Semantic search ranks jobs by similarity. Only matches ≥ 80% reach you — false positives stay out.',
    },
    {
      title: 'Explain',
      desc: 'A contrastive explanation tells you exactly which skills boosted the score and which dragged it down.',
    },
    {
      title: 'Grow',
      desc: 'Your roadmap turns the gaps into a learning plan. Each acquired skill re-scores the whole board.',
    },
  ]
  return (
    <section className="py-20 sm:py-24 border-t border-line bg-surface-2/30">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="max-w-2xl">
          <h2 className="section-title">How it works under the hood</h2>
          <p className="section-sub">
            A privacy-first RAG architecture. Your data stays on your machine — the AI comes
            to it, not the other way around.
          </p>
        </div>
        <ol className="mt-12 grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {steps.map((s, i) => (
            <li key={s.title} className="card relative">
              <span className="absolute -top-3 left-5 chip bg-brand-500/20 text-brand-500 dark:text-brand-200 border-brand-400/40">
                Step {i + 1}
              </span>
              <h3 className="mt-2 text-lg font-semibold text-fg">{s.title}</h3>
              <p className="mt-2 text-sm text-muted">{s.desc}</p>
            </li>
          ))}
        </ol>
      </div>
    </section>
  )
}

function Stats() {
  const stats = [
    { value: '85%', label: 'Target recommendation accuracy' },
    { value: '80%', label: 'Minimum match threshold' },
    { value: '384', label: 'Embedding dimensions' },
    { value: '100%', label: 'Local processing — no cloud' },
  ]
  return (
    <section className="py-16">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {stats.map((s) => (
            <div key={s.label} className="card text-center">
              <p className="text-3xl sm:text-4xl font-bold text-fg">{s.value}</p>
              <p className="mt-1 text-xs sm:text-sm text-muted">{s.label}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

function CTA() {
  return (
    <section className="py-20">
      <div className="mx-auto max-w-5xl px-4 sm:px-6 lg:px-8">
        <div className="card text-center bg-gradient-to-br from-brand-500/15 via-surface to-surface border-brand-400/30">
          <h2 className="section-title">Ready to find roles that match the real you?</h2>
          <p className="section-sub mx-auto">Upload a CV in seconds. ResuMind handles the rest.</p>
          <div className="mt-6 flex items-center justify-center gap-3">
            <AuthLink to="/resume" className="btn-primary">
              Start now
              <Arrow />
            </AuthLink>
          </div>
        </div>
      </div>
    </section>
  )
}
