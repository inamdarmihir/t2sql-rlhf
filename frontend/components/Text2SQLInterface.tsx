'use client'

import { useState } from 'react'
import { useCopilotAction, useCopilotReadable } from '@copilotkit/react-core'
import { Database, Loader2, CheckCircle, XCircle, Zap } from 'lucide-react'
import axios from 'axios'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface QueryResult {
  sql_query: string
  results: any[]
  cached: boolean
  error?: string
  message_count: number
}

export default function Text2SQLInterface() {
  const [question, setQuestion] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<QueryResult | null>(null)
  const [schema, setSchema] = useState<string>('')

  // Make database schema readable by Copilot
  useCopilotReadable({
    description: 'The current database schema',
    value: schema,
  })

  // Make query results readable by Copilot
  useCopilotReadable({
    description: 'The latest query results',
    value: result ? JSON.stringify(result) : '',
  })

  // Register Copilot action for querying
  useCopilotAction({
    name: 'queryDatabase',
    description: 'Query the database using natural language',
    parameters: [
      {
        name: 'question',
        type: 'string',
        description: 'The natural language question to convert to SQL',
        required: true,
      },
    ],
    handler: async ({ question }) => {
      await handleQuery(question)
      return `Query executed: ${question}`
    },
  })

  // Register Copilot action for getting schema
  useCopilotAction({
    name: 'getSchema',
    description: 'Get the database schema information',
    parameters: [],
    handler: async () => {
      await fetchSchema()
      return `Schema retrieved`
    },
  })

  const handleQuery = async (q: string = question) => {
    if (!q.trim()) return

    setLoading(true)
    setResult(null)

    try {
      const response = await axios.post<QueryResult>(`${API_URL}/api/query`, {
        question: q,
      })
      setResult(response.data)
    } catch (error: any) {
      setResult({
        sql_query: '',
        results: [],
        cached: false,
        error: error.response?.data?.detail || error.message,
        message_count: 0,
      })
    } finally {
      setLoading(false)
    }
  }

  const fetchSchema = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/schema`)
      setSchema(response.data.schema)
    } catch (error) {
      console.error('Failed to fetch schema:', error)
    }
  }

  const exampleQueries = [
    'Show me all customers from California',
    'What are the top 5 best-selling products?',
    'What is the total revenue by category?',
    'Which customers spent more than $500?',
  ]

  return (
    <div className="max-w-6xl mx-auto">
      {/* Query Input */}
      <div className="query-card">
        <div className="flex items-center gap-2 mb-4">
          <Database className="w-6 h-6 text-blue-600" />
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
            Ask Your Database
          </h2>
        </div>

        <div className="space-y-4">
          <div className="flex gap-2">
            <input
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleQuery()}
              placeholder="e.g., Show me all customers from California"
              className="flex-1 px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white"
              disabled={loading}
            />
            <button
              onClick={() => handleQuery()}
              disabled={loading || !question.trim()}
              className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {loading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Processing...
                </>
              ) : (
                <>
                  <Zap className="w-5 h-5" />
                  Query
                </>
              )}
            </button>
          </div>

          {/* Example Queries */}
          <div className="flex flex-wrap gap-2">
            <span className="text-sm text-gray-600 dark:text-gray-400">Try:</span>
            {exampleQueries.map((q, i) => (
              <button
                key={i}
                onClick={() => {
                  setQuestion(q)
                  handleQuery(q)
                }}
                className="text-sm px-3 py-1 bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 rounded-full hover:bg-blue-200 dark:hover:bg-blue-800 transition-colors"
                disabled={loading}
              >
                {q}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Results */}
      {result && (
        <div className="space-y-4">
          {/* Status */}
          <div className="query-card">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                {result.error ? (
                  <>
                    <XCircle className="w-5 h-5 text-red-500" />
                    <span className="text-red-600 dark:text-red-400 font-semibold">
                      Error
                    </span>
                  </>
                ) : (
                  <>
                    <CheckCircle className="w-5 h-5 text-green-500" />
                    <span className="text-green-600 dark:text-green-400 font-semibold">
                      Success
                    </span>
                  </>
                )}
              </div>
              {result.cached && (
                <div className="flex items-center gap-1 text-sm text-purple-600 dark:text-purple-400">
                  <Zap className="w-4 h-4" />
                  <span>Cached Result</span>
                </div>
              )}
            </div>
          </div>

          {/* SQL Query */}
          {result.sql_query && (
            <div className="query-card">
              <h3 className="text-lg font-semibold mb-3 text-gray-900 dark:text-white">
                Generated SQL
              </h3>
              <pre className="code-block">
                <code>{result.sql_query}</code>
              </pre>
            </div>
          )}

          {/* Error Message */}
          {result.error && (
            <div className="query-card bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800">
              <h3 className="text-lg font-semibold mb-2 text-red-700 dark:text-red-400">
                Error Details
              </h3>
              <p className="text-red-600 dark:text-red-300">{result.error}</p>
            </div>
          )}

          {/* Results Table */}
          {result.results && result.results.length > 0 && (
            <div className="query-card">
              <h3 className="text-lg font-semibold mb-3 text-gray-900 dark:text-white">
                Results ({result.results.length} rows)
              </h3>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                  <thead className="bg-gray-50 dark:bg-gray-800">
                    <tr>
                      {Object.keys(result.results[0]).map((key) => (
                        <th
                          key={key}
                          className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider"
                        >
                          {key}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-700">
                    {result.results.map((row, i) => (
                      <tr key={i}>
                        {Object.values(row).map((value: any, j) => (
                          <td
                            key={j}
                            className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-300"
                          >
                            {value !== null ? String(value) : 'NULL'}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* JSON View */}
          {result.results && result.results.length > 0 && (
            <details className="query-card">
              <summary className="cursor-pointer text-lg font-semibold text-gray-900 dark:text-white">
                JSON View
              </summary>
              <pre className="code-block mt-3">
                <code>{JSON.stringify(result.results, null, 2)}</code>
              </pre>
            </details>
          )}
        </div>
      )}

      {/* Schema Button */}
      <div className="mt-8 text-center">
        <button
          onClick={fetchSchema}
          className="btn-secondary"
        >
          View Database Schema
        </button>
      </div>

      {schema && (
        <div className="query-card mt-4">
          <h3 className="text-lg font-semibold mb-3 text-gray-900 dark:text-white">
            Database Schema
          </h3>
          <pre className="code-block whitespace-pre-wrap">
            <code>{schema}</code>
          </pre>
        </div>
      )}
    </div>
  )
}
