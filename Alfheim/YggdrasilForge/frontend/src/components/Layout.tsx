import { NavLink } from 'react-router-dom'
import type { ReactNode } from 'react'

const navItems = [
  { path: '/', label: 'Forge', icon: '⚒️' },
  { path: '/library', label: 'Library', icon: '📚' },
  { path: '/viewport', label: 'Viewport', icon: '🖥️' },
  { path: '/history', label: 'History', icon: '📜' },
]

export function Layout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen flex">
      {/* Sidebar */}
      <aside className="w-56 bg-rune-900/60 border-r border-rune-700/40 flex flex-col">
        {/* Logo */}
        <div className="p-4 border-b border-rune-700/40">
          <h1 className="text-lg font-bold text-ember flex items-center gap-2">
            <span className="text-2xl">⚒️</span>
            YggdrasilForge
          </h1>
          <p className="text-xs text-rune-400 mt-1">Viking 3D Asset Studio</p>
        </div>

        {/* Nav */}
        <nav className="flex-1 p-2 space-y-1">
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === '/'}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-all ${
                  isActive
                    ? 'bg-ember/20 text-ember-light border border-ember/30'
                    : 'text-rune-300 hover:bg-rune-800 hover:text-rune-100'
                }`
              }
            >
              <span className="text-base">{item.icon}</span>
              {item.label}
            </NavLink>
          ))}
        </nav>

        {/* Blender Status */}
        <div className="p-3 border-t border-rune-700/40">
          <BlenderStatus />
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        {children}
      </main>
    </div>
  )
}

function BlenderStatus() {
  // TODO: connect to real health endpoint
  return (
    <div className="flex items-center gap-2 text-xs text-rune-400">
      <div className="w-2 h-2 rounded-full bg-rune-600" />
      <span>Blender: Checking...</span>
    </div>
  )
}
