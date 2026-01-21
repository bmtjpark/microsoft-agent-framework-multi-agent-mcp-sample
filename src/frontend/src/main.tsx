import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

console.log('Mounting React App...');

const rootElement = document.getElementById('root');
if (!rootElement) {
  console.error('Root element not found');
} else {
  try {
    createRoot(rootElement).render(
      <StrictMode>
        <App />
      </StrictMode>,
    )
  } catch (e) {
    console.error(e);
    rootElement.innerHTML = `<div style="color: red; padding: 20px;">
      <h1>React Mount Error</h1>
      <pre>${e instanceof Error ? e.message : JSON.stringify(e)}</pre>
      <pre>${e instanceof Error ? e.stack : ''}</pre>
    </div>`;
  }
}
