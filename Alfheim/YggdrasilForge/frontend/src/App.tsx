import { Routes, Route } from 'react-router-dom'
import { Layout } from './components/Layout'
import { ForgePage } from './pages/ForgePage'
import { LibraryPage } from './pages/LibraryPage'
import { HistoryPage } from './pages/HistoryPage'
import { ViewportPage } from './pages/ViewportPage'

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<ForgePage />} />
        <Route path="/library" element={<LibraryPage />} />
        <Route path="/history" element={<HistoryPage />} />
        <Route path="/viewport" element={<ViewportPage />} />
      </Routes>
    </Layout>
  )
}
