import { useState } from 'react'

function App() {
  const [question, setQuestion] = useState('')
  const [language, setLanguage] = useState('English')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    
    if (!question.trim()) return

    setLoading(true)
    setError(null)
    setResult(null)

    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'

    try {
      const response = await fetch(`${apiUrl}/ask`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ question, language }),
      })

      if (!response.ok) {
        throw new Error(`Server error: ${response.statusText}`)
      }

      const data = await response.json()
      setResult(data)
    } catch (err) {
      setError(err.message || 'Something went wrong while fetching the answer.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="container">
      <h1>Homework Helper</h1>
      
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="question">What is your question?</label>
          <textarea
            id="question"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="E.g., Solve for x: 2x + 4 = 10"
            disabled={loading}
            required
          />
        </div>

        <div className="form-group">
          <label htmlFor="language">Language</label>
          <select 
            id="language" 
            value={language} 
            onChange={(e) => setLanguage(e.target.value)}
            disabled={loading}
          >
            <option value="English">English</option>
            <option value="Hindi">Hindi</option>
            <option value="Tamil">Tamil</option>
            <option value="Telugu">Telugu</option>
          </select>
        </div>

        <button type="submit" disabled={loading || !question.trim()}>
          {loading ? 'Solving...' : 'Solve'}
        </button>
      </form>

      {error && (
        <div className="error-message">
          {error}
        </div>
      )}

      {result && !loading && (
        <div className="results-panel">
          <div className="subject-badge">
            {result.subject}
          </div>

          <div className="result-section">
            <h3>Explanation</h3>
            <p>{result.explanation}</p>
          </div>

          <div className="result-section quiz-box">
            <h3>Follow-up Quiz</h3>
            <p>{result.quiz_question}</p>
          </div>
        </div>
      )}
    </div>
  )
}

export default App