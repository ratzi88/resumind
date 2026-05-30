import { jsPDF } from 'jspdf'

const MARGIN = 18        // mm from each edge
const PAGE_W = 210       // A4 width
const PAGE_H = 297       // A4 height
const CONTENT_W = PAGE_W - MARGIN * 2
const LH = 5             // line height (mm)

/**
 * Build a real, openable PDF from a resume payload object.
 * @param {object} payload – the yamlPayload from Resume.jsx
 * @returns {jsPDF}
 */
export function buildResumePdf(payload) {
  const doc = new jsPDF({ unit: 'mm', format: 'a4', putOnlyUsedFonts: true })

  // ── cursor keeps track of the current Y position ──────────────────────────
  const cursor = { y: MARGIN }

  const advance = (mm) => { cursor.y += mm }

  const checkPage = (needed = 12) => {
    if (cursor.y + needed > PAGE_H - MARGIN) {
      doc.addPage()
      cursor.y = MARGIN
    }
  }

  const setFont = (style = 'normal', size = 10) => {
    doc.setFont('helvetica', style)
    doc.setFontSize(size)
  }

  const setColor = (r, g, b) => doc.setTextColor(r, g, b)

  // Print text at current cursor, optional right-aligned value
  const line = (str, opts = {}) => {
    if (opts.rightText) {
      setFont(opts.rightFont || 'normal', opts.rightSize || 9)
      setColor(...(opts.rightColor || [100, 116, 139]))
      doc.text(String(opts.rightText), MARGIN + CONTENT_W, cursor.y, { align: 'right' })
    }
    setFont(opts.font || 'normal', opts.size || 10)
    setColor(...(opts.color || [30, 30, 30]))
    doc.text(String(str || ''), MARGIN, cursor.y)
    advance(opts.after ?? LH)
  }

  const rule = (r = 200, g = 200, b = 200, thickness = 0.3) => {
    doc.setDrawColor(r, g, b)
    doc.setLineWidth(thickness)
    doc.line(MARGIN, cursor.y, MARGIN + CONTENT_W, cursor.y)
    advance(4)
  }

  const sectionTitle = (label) => {
    checkPage(14)
    advance(MARGIN > 18 ? 3 : 3)   // gap before heading
    setFont('bold', 8.5)
    setColor(58, 107, 255)
    doc.text(label, MARGIN, cursor.y)
    advance(4)
    doc.setDrawColor(58, 107, 255)
    doc.setLineWidth(0.2)
    doc.line(MARGIN, cursor.y, MARGIN + CONTENT_W, cursor.y)
    advance(4)
  }

  const multiline = (text, indent = 0, size = 9.5, color = [40, 40, 40]) => {
    setFont('normal', size)
    setColor(...color)
    const lines = doc.splitTextToSize(String(text || ''), CONTENT_W - indent)
    lines.forEach((l) => {
      checkPage()
      doc.text(l, MARGIN + indent, cursor.y)
      advance(LH)
    })
  }

  // ─── HEADER ─────────────────────────────────────────────────────────────────
  line(payload.name || 'Your Name', { font: 'bold', size: 22, color: [15, 23, 42], after: 7 })

  if (payload.headline) {
    line(payload.headline, { size: 11, color: [71, 85, 105], after: 5 })
  }

  const contactParts = [
    payload.contact?.email,
    payload.contact?.phone,
    payload.contact?.location,
  ].filter(Boolean)

  if (contactParts.length) {
    line(contactParts.join('  ·  '), { size: 9, color: [100, 116, 139], after: 5 })
  }

  advance(1)
  rule(58, 107, 255, 0.6)   // brand-blue underline

  // ─── SUMMARY ────────────────────────────────────────────────────────────────
  if (payload.summary) {
    sectionTitle('SUMMARY')
    multiline(payload.summary)
    advance(2)
  }

  // ─── EXPERIENCE ─────────────────────────────────────────────────────────────
  const exp = (payload.experience || []).filter((e) => e.title || e.company)
  if (exp.length) {
    sectionTitle('EXPERIENCE')
    exp.forEach((e) => {
      checkPage(12)
      // Title left, period right
      line(e.title || '', {
        font: 'bold',
        size: 10,
        color: [15, 23, 42],
        rightText: e.period || '',
        rightSize: 8.5,
        rightColor: [100, 116, 139],
        after: 5,
      })
      if (e.company) {
        line(e.company, { size: 9, color: [71, 85, 105], after: 4 })
      }
      if (e.description) {
        multiline(e.description, 0, 9.5, [50, 50, 50])
      }
      advance(3)
    })
  }

  // ─── EDUCATION ──────────────────────────────────────────────────────────────
  const edu = (payload.education || []).filter((e) => e.degree || e.school)
  if (edu.length) {
    sectionTitle('EDUCATION')
    edu.forEach((e) => {
      checkPage(10)
      line(e.degree || '', {
        font: 'bold',
        size: 10,
        color: [15, 23, 42],
        rightText: e.period || '',
        rightSize: 8.5,
        rightColor: [100, 116, 139],
        after: 5,
      })
      if (e.school) {
        line(e.school, { size: 9, color: [71, 85, 105], after: 4 })
      }
      advance(2)
    })
  }

  // ─── PROJECTS ───────────────────────────────────────────────────────────────
  const projects = (payload.projects || []).filter((p) => p.name)
  if (projects.length) {
    sectionTitle('PROJECTS')
    projects.forEach((p) => {
      checkPage(10)
      line(p.name, { font: 'bold', size: 10, color: [15, 23, 42], after: 5 })
      if (p.link) {
        line(p.link, { size: 8.5, color: [58, 107, 255], after: 4 })
      }
      if (p.description) {
        multiline(p.description, 0, 9.5, [50, 50, 50])
      }
      advance(3)
    })
  }

  // ─── SKILLS ─────────────────────────────────────────────────────────────────
  const { technical = [], tools = [], soft = [] } = payload.skills || {}
  const skillGroups = [
    { label: 'Technical', items: technical },
    { label: 'Tools', items: tools },
    { label: 'Soft', items: soft },
  ].filter((g) => g.items.length > 0)

  if (skillGroups.length) {
    sectionTitle('SKILLS')
    skillGroups.forEach((g) => {
      checkPage(8)
      // Print bold label then normal items on same line
      setFont('bold', 9.5)
      setColor(15, 23, 42)
      const labelW = doc.getTextWidth(`${g.label}: `)
      doc.text(`${g.label}: `, MARGIN, cursor.y)
      setFont('normal', 9.5)
      setColor(50, 50, 50)
      const itemsStr = g.items.join(', ')
      const wrapped = doc.splitTextToSize(itemsStr, CONTENT_W - labelW)
      wrapped.forEach((l, i) => {
        doc.text(l, i === 0 ? MARGIN + labelW : MARGIN, cursor.y)
        if (i < wrapped.length - 1) advance(LH)
      })
      advance(LH)
    })
  }

  // ─── FOOTER (page numbers) ───────────────────────────────────────────────────
  const total = doc.getNumberOfPages()
  for (let i = 1; i <= total; i++) {
    doc.setPage(i)
    setFont('normal', 7.5)
    setColor(180, 180, 180)
    doc.text(
      `Generated by ResuMind · ${new Date().toLocaleDateString()}`,
      MARGIN,
      PAGE_H - 8,
    )
    if (total > 1) {
      doc.text(`${i} / ${total}`, MARGIN + CONTENT_W, PAGE_H - 8, { align: 'right' })
    }
  }

  return doc
}
