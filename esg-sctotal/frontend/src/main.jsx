import React from 'react'
import ReactDOM from 'react-dom/client'
/* [이슈] App.jsx 경로 변경: src/ → src/homes/ (PASTED 구조 반영) */
import App from '@/homes/App'
/* [이슈] CSS 경로 변경: src/ → src/styles/ (PASTED 구조 반영) */
import '@styles/index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
