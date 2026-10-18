import React from 'react';
import { Database, Activity, RefreshCw, Cpu, Sun, Moon } from 'lucide-react';

export default function Header({ dbHealth, onRefreshHealth, isRefreshing, theme, onToggleTheme }) {
  const isConnected = dbHealth?.status === 'connected';

  return (
    <header className="h-16 border-b border-slate-800 bg-slate-900/90 backdrop-blur-md px-6 flex items-center justify-between z-20 shrink-0">
      {/* Brand & Track Badge */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-brand-500 to-emerald-700 flex items-center justify-center shadow-lg shadow-brand-500/20">
            <Cpu className="w-5 h-5 text-black font-bold" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-bold tracking-tight text-white">CodeGraph <span className="text-brand-500">AI</span></h1>
              <span className="text-[10px] uppercase font-semibold px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">v0.1.0</span>
            </div>
            <p className="text-xs text-slate-400">Context & Investigation Agent for Connected Codebases</p>
          </div>
        </div>

        <div className="hidden md:flex items-center gap-2 pl-4 border-l border-slate-800">
          <span className="text-xs font-medium px-2.5 py-1 rounded-full bg-emerald-950/70 text-emerald-400 border border-emerald-800/80 flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
            Track: Agents That Act on Connected Data
          </span>
        </div>
      </div>

      {/* Database Connection Status & Controls */}
      <div className="flex items-center gap-3">
        <div className={`flex items-center gap-2 px-3 py-1.5 rounded-md border text-xs font-mono transition-all ${
          isConnected
            ? 'bg-emerald-950/40 border-emerald-800/70 text-emerald-300 shadow-sm shadow-emerald-900/20'
            : 'bg-rose-950/40 border-rose-800/70 text-rose-300'
        }`}>
          <Database className={`w-3.5 h-3.5 ${isConnected ? 'text-emerald-400' : 'text-rose-400'}`} />
          <span>FalkorDB:</span>
          <span className="font-semibold">{isConnected ? 'ONLINE' : 'OFFLINE'}</span>
          <span className="text-slate-400">({dbHealth?.host || 'localhost'}:{dbHealth?.port || 6379})</span>
          {dbHealth?.active_graph && (
            <span className="bg-slate-800 px-1.5 py-0.5 rounded text-[11px] text-slate-300">
              graph: {dbHealth.active_graph}
            </span>
          )}
        </div>

        <button
          onClick={onRefreshHealth}
          disabled={isRefreshing}
          title="Refresh Database Health"
          className="p-1.5 rounded-md border border-slate-800 bg-slate-800/60 text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin text-brand-500' : ''}`} />
        </button>

        {/* Dark / Light Theme Toggle */}
        <button
          onClick={onToggleTheme}
          title={`Switch to ${theme === 'dark' ? 'Light' : 'Dark'} Mode`}
          className="p-1.5 rounded-md border border-slate-800 bg-slate-800/60 text-slate-300 hover:text-amber-400 hover:bg-slate-800 transition-colors"
        >
          {theme === 'dark' ? (
            <Sun className="w-4 h-4 text-amber-400" />
          ) : (
            <Moon className="w-4 h-4 text-indigo-500" />
          )}
        </button>
      </div>
    </header>
  );
}
