import { Routes, Route, Navigate } from 'react-router-dom'
import Navbar from './components/Navbar.jsx'
import Footer from './components/Footer.jsx'
import Landing from './pages/Landing.jsx'
import Login from './pages/Login.jsx'
import Onboarding from './pages/Onboarding.jsx'
import Resume from './pages/Resume.jsx'
import Jobs from './pages/Jobs.jsx'
import Roadmap from './pages/Roadmap.jsx'
import NotFound from './pages/NotFound.jsx'
import { useAuth } from './lib/AuthContext.jsx'

function ProtectedRoute({ children }) {
  const { token, loading } = useAuth()
  if (loading) return (
    <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center">
      <span className="h-6 w-6 rounded-full border-2 border-brand-400 border-t-transparent animate-spin" />
    </div>
  )
  if (!token) return <Navigate to="/login" replace />
  return children
}

export default function App() {
  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />
      <main className="flex-1">
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/login" element={<Login />} />
          <Route path="/onboarding" element={
            <ProtectedRoute><Onboarding /></ProtectedRoute>
          } />
          <Route path="/resume" element={
            <ProtectedRoute><Resume /></ProtectedRoute>
          } />
          <Route path="/jobs" element={
            <ProtectedRoute><Jobs /></ProtectedRoute>
          } />
          <Route path="/roadmap" element={
            <ProtectedRoute><Roadmap /></ProtectedRoute>
          } />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </main>
      <Footer />
    </div>
  )
}
