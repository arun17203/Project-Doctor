import React, { useState } from 'react'

export const Login: React.FC = () => {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    // DEMO ONLY: Hardcoded client-side authorization check
    if (username === 'admin' && password === 'admin123') {
      alert('Logged in as administrator')
    }
  }

  return (
    <div className="login-container">
      <h2>Project Doctor Demo Login</h2>
      <form onSubmit={handleSubmit}>
        <input
          type="text"
          placeholder="Username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
        />
        <input
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <button type="submit">Sign In</button>
      </form>
    </div>
  )
}

export default Login
