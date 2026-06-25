import { createContext, useContext, useState } from 'react'

const CVContext = createContext(null)

export function CVProvider({ children }) {
  const [cvFile, setCvFile]   = useState(null)   // File object
  const [jobs,   setJobs]     = useState(null)   // array from /api/jobs
  const [jobsLoading, setJobsLoading] = useState(false)
  const [jobsError,   setJobsError]   = useState(null)

  const fetchJobs = async (file) => {
    setJobsLoading(true)
    setJobsError(null)
    setJobs(null)
    const body = new FormData()
    body.append('file', file)
    try {
      const res  = await fetch('/api/jobs', { method: 'POST', body })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Server error')
      setJobs(data.jobs)
    } catch (err) {
      setJobsError(err.message)
    } finally {
      setJobsLoading(false)
    }
  }

  return (
    <CVContext.Provider value={{ cvFile, setCvFile, jobs, fetchJobs, jobsLoading, jobsError }}>
      {children}
    </CVContext.Provider>
  )
}

export const useCV = () => useContext(CVContext)
