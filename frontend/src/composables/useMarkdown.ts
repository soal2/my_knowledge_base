/**
 * Markdown Renderer Composable
 * 
 * Features:
 * - Parse markdown to HTML
 * - Syntax highlighting for code blocks
 * - KaTeX for math formulas
 */

import { marked } from 'marked'
import hljs from 'highlight.js'
import katex from 'katex'

// Configure marked
marked.setOptions({
  gfm: true,
  breaks: true
})

// Custom renderer for code blocks
const renderer = new marked.Renderer()

renderer.code = (code: string, language: string | undefined): string => {
  const validLanguage = language && hljs.getLanguage(language) ? language : 'plaintext'
  const highlighted = hljs.highlight(code, { language: validLanguage }).value
  return `<pre><code class="hljs language-${validLanguage}">${highlighted}</code></pre>`
}

// Parse inline math ($...$) and block math ($$...$$)
const renderMath = (text: string): string => {
  // Block math: $$...$$
  text = text.replace(/\$\$([\s\S]+?)\$\$/g, (_match, math) => {
    try {
      return katex.renderToString(math.trim(), {
        displayMode: true,
        throwOnError: false
      })
    } catch {
      return `<span class="text-red-500">[Math Error]</span>`
    }
  })
  
  // Inline math: $...$
  text = text.replace(/\$([^\$\n]+?)\$/g, (_match, math) => {
    try {
      return katex.renderToString(math.trim(), {
        displayMode: false,
        throwOnError: false
      })
    } catch {
      return `<span class="text-red-500">[Math Error]</span>`
    }
  })
  
  return text
}

export function useMarkdown() {
  const render = (content: string): string => {
    if (!content) return ''
    
    // First render math
    let processed = renderMath(content)
    
    // Then render markdown
    processed = marked.parse(processed, { renderer }) as string
    
    return processed
  }
  
  return { render }
}
