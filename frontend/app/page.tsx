'use client'

import { CopilotKit } from '@copilotkit/react-core'
import { CopilotSidebar } from '@copilotkit/react-ui'
import '@copilotkit/react-ui/styles.css'
import Text2SQLInterface from '@/components/Text2SQLInterface'

export default function Home() {
  return (
    <CopilotKit runtimeUrl="/api/copilotkit">
      <CopilotSidebar
        defaultOpen={true}
        labels={{
          title: "Text2SQL Assistant",
          initial: "Ask me anything about your database!",
        }}
      >
        <main className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800">
          <div className="container mx-auto px-4 py-8">
            <header className="text-center mb-12">
              <h1 className="text-5xl font-bold text-gray-900 dark:text-white mb-4">
                Text2SQL
              </h1>
              <p className="text-xl text-gray-600 dark:text-gray-300">
                AI-Powered Natural Language to SQL Converter
              </p>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">
                Powered by LangGraph Multi-Agent System with Qdrant Caching
              </p>
            </header>

            <Text2SQLInterface />
          </div>
        </main>
      </CopilotSidebar>
    </CopilotKit>
  )
}
