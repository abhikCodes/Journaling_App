/**
 * Attempts to extract an access token from various sources
 * in an auth callback situation
 */
export function extractToken() {
  // Try to get token from URL
  const params = new URLSearchParams(window.location.search)
  const accessToken = params.get('access_token')
  if (accessToken) return accessToken
  
  // Try to extract from document body
  try {
    const bodyText = document.body.innerText
    
    // Look for JSON format
    if (bodyText?.includes('access_token')) {
      // Try to parse as JSON
      try {
        const jsonResponse = JSON.parse(bodyText)
        if (jsonResponse?.access_token) {
          return jsonResponse.access_token
        }
      } catch (error) {
        console.error('Failed to parse body as JSON', error)
      }
      
      // Try regex extraction as fallback
      const tokenMatch = bodyText.match(/"access_token":"([^"]+)"/)
      if (tokenMatch && tokenMatch[1]) {
        return tokenMatch[1]
      }
    }
  } catch (error) {
    console.error('Error extracting token from body', error)
  }
  
  return null
} 