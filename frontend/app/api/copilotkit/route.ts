import { NextRequest } from 'next/server'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://backend:8000'

export async function POST(req: NextRequest) {
  try {
    const body = await req.json()
    
    // Handle CopilotKit messages
    if (body.messages && body.messages.length > 0) {
      const lastMessage = body.messages[body.messages.length - 1]
      
      if (lastMessage.role === 'user') {
        // Query the Text2SQL API
        const response = await fetch(`${API_URL}/api/query`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            question: lastMessage.content
          })
        })
        
        if (!response.ok) {
          throw new Error('Failed to query database')
        }
        
        const data = await response.json()
        
        // Format response for CopilotKit
        let responseText = ''
        
        if (data.error) {
          responseText = `❌ Error: ${data.error}`
        } else {
          responseText = `✅ Query executed successfully!\n\n`
          responseText += `**SQL Query:**\n\`\`\`sql\n${data.sql_query}\n\`\`\`\n\n`
          responseText += `**Results:** ${data.results.length} rows\n`
          responseText += `**Cached:** ${data.cached ? '✓ Yes' : '✗ No'}\n\n`
          
          if (data.results.length > 0) {
            responseText += `**Sample Data:**\n\`\`\`json\n${JSON.stringify(data.results.slice(0, 3), null, 2)}\n\`\`\``
          }
        }
        
        return new Response(
          JSON.stringify({
            messages: [
              ...body.messages,
              {
                role: 'assistant',
                content: responseText
              }
            ]
          }),
          {
            headers: {
              'Content-Type': 'application/json',
            },
          }
        )
      }
    }
    
    return new Response(
      JSON.stringify({ messages: body.messages }),
      {
        headers: {
          'Content-Type': 'application/json',
        },
      }
    )
  } catch (error) {
    console.error('CopilotKit API error:', error)
    return new Response(
      JSON.stringify({ error: 'Internal server error' }),
      {
        status: 500,
        headers: {
          'Content-Type': 'application/json',
        },
      }
    )
  }
}
