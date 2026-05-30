export default function Footer() {
  return (
    <footer className="border-t border-line bg-bg/80">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-8 flex flex-col sm:flex-row items-center justify-between gap-3 text-sm text-muted">
        <p>ResuMind &middot; Final Project &middot; Gal Ratzon, Noa Negri, Aviya Omisi</p>
        <p className="flex items-center gap-3">
          <span className="chip">Local-first</span>
          <span className="chip">Privacy by Design</span>
        </p>
      </div>
    </footer>
  )
}
