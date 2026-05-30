// Minimal, dependency-free YAML serializer tailored to the Resume schema.
// Handles strings, numbers, booleans, arrays (incl. arrays of objects), and nested objects.

function escapeStr(s) {
  const str = String(s)
  if (str === '') return '""'
  // Quote if contains chars that would confuse YAML
  if (/[:#\-?&*!|>'"%@`{}[\],\n]/.test(str) || /^\s|\s$/.test(str)) {
    return JSON.stringify(str)
  }
  return str
}

function isEmpty(v) {
  if (v === null || v === undefined) return true
  if (typeof v === 'string' && v.trim() === '') return true
  if (Array.isArray(v) && v.length === 0) return true
  if (typeof v === 'object' && Object.keys(v).length === 0) return true
  return false
}

function emit(value, indent = 0) {
  const pad = '  '.repeat(indent)

  if (Array.isArray(value)) {
    if (value.length === 0) return '[]'
    return value
      .map((item) => {
        if (item !== null && typeof item === 'object' && !Array.isArray(item)) {
          const entries = Object.entries(item).filter(([, v]) => !isEmpty(v))
          if (entries.length === 0) return `${pad}- {}`
          const [firstKey, firstVal] = entries[0]
          const restEntries = entries.slice(1)
          const firstLine = `${pad}- ${firstKey}: ${formatScalar(firstVal, indent + 1)}`
          const restLines = restEntries
            .map(([k, v]) => `${'  '.repeat(indent + 1)}${k}: ${formatScalar(v, indent + 1)}`)
            .join('\n')
          return restLines ? `${firstLine}\n${restLines}` : firstLine
        }
        return `${pad}- ${formatScalar(item, indent)}`
      })
      .join('\n')
  }

  if (value !== null && typeof value === 'object') {
    return Object.entries(value)
      .filter(([, v]) => !isEmpty(v))
      .map(([k, v]) => `${pad}${k}: ${formatScalar(v, indent)}`)
      .join('\n')
  }

  return formatScalar(value, indent)
}

function formatScalar(v, indent) {
  if (v === null || v === undefined) return '~'
  if (typeof v === 'number' || typeof v === 'boolean') return String(v)
  if (Array.isArray(v) || typeof v === 'object') {
    if (isEmpty(v)) return Array.isArray(v) ? '[]' : '{}'
    return '\n' + emit(v, indent + 1)
  }
  return escapeStr(v)
}

export function toYaml(obj) {
  return emit(obj, 0)
}
