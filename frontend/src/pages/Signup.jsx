import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function Signup() {
  const { signup } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ username: '', email: '', password: '' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handle = (e) => setForm({ ...form, [e.target.name]: e.target.value })

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await signup(form.username, form.email, form.password)
      navigate('/')
    } catch (err) {
      setError(err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-[80vh] flex items-center justify-center px-4">
      <div className="w-full max-w-md card p-8">
        <h1 className="text-2xl font-bold mb-1">Sign up</h1>
        <p className="text-white/40 text-sm mb-6">
          Free forever — an account just saves your favourite teams.
        </p>

        {error && <div className="bg-red-900/30 border border-red-700 text-red-300 text-sm px-4 py-2 rounded-lg mb-4">{error}</div>}

        <form onSubmit={submit} className="space-y-4">
          {['username', 'email'].map((field) => (
            <div key={field}>
              <label className="block text-sm text-white/60 mb-1 capitalize">{field}</label>
              <input
                name={field} value={form[field]} onChange={handle} required
                type={field === 'email' ? 'email' : 'text'}
                className="w-full bg-pitch-900 border border-white/10 rounded-lg px-4 py-2.5 text-white focus:border-green-500 outline-none transition-colors"
              />
            </div>
          ))}
          <div>
            <label className="block text-sm text-white/60 mb-1">Password</label>
            <input
              name="password" type="password" value={form.password} onChange={handle}
              required minLength={6}
              className="w-full bg-pitch-900 border border-white/10 rounded-lg px-4 py-2.5 text-white focus:border-green-500 outline-none transition-colors"
            />
          </div>
          <button type="submit" disabled={loading} className="btn-primary w-full py-2.5 text-center disabled:opacity-60">
            {loading ? 'Creating account…' : 'Sign up'}
          </button>
        </form>

        <p className="text-center text-white/40 text-sm mt-6">
          Already have an account? <Link to="/login" className="text-green-400 hover:underline">Sign in</Link>
        </p>
        <p className="text-center text-white/30 text-sm mt-2">
          <Link to="/" className="hover:text-yellow-300">Keep watching without an account →</Link>
        </p>
      </div>
    </div>
  )
}
