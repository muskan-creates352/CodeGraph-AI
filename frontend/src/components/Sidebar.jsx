import React, { useState } from 'react';
import { 
  FolderGit2, 
  Play, 
  BarChart3, 
  FileCode, 
  Boxes, 
  Network, 
  Sparkles, 
  Info,
  CheckCircle2,
  AlertTriangle,
  FolderOpen
} from 'lucide-react';

export default function Sidebar({
  graphStats,
  onAnalyzeDemo,
  onAnalyzeCustom,
  isAnalyzing,
  selectedNode,
  onSelectEntityForImpact
}) {
  const [customPath, setCustomPath] = useState('');
  const [showCustomInput, setShowCustomInput] = useState(false);

  const handleCustomSubmit = (e) => {
    e.preventDefault();
    if (customPath.trim()) {
      onAnalyzeCustom(customPath.trim());
    }
  };

  return (
    <aside className="w-80 border-r border-slate-800 bg-slate-900/60 flex flex-col h-full overflow-y-auto shrink-0 select-none">
      {/* Repository Ingestion Section */}
      <div className="p-4 border-b border-slate-800">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
            <FolderGit2 className="w-3.5 h-3.5 text-brand-500" />
            Repository Target
          </span>
          <span className="text-[11px] font-mono text-emerald-400 bg-emerald-950/60 px-1.5 py-0.5 rounded border border-emerald-900/60">
            AST Zero-Exec
          </span>
        </div>

        {/* 1-Click Demo Repository Loader */}
        <button
          onClick={onAnalyzeDemo}
          disabled={isAnalyzing}
          className="w-full py-2.5 px-3.5 rounded-lg bg-gradient-to-r from-brand-600 to-emerald-600 hover:from-brand-500 hover:to-emerald-500 text-slate-950 font-semibold text-xs flex items-center justify-center gap-2 shadow-md shadow-brand-500/10 transition-all active:scale-[0.98] disabled:opacity-50 disabled:pointer-events-none"
        >
          <Play className={`w-3.5 h-3.5 fill-current ${isAnalyzing ? 'animate-spin' : ''}`} />
          {isAnalyzing ? 'Ingesting into FalkorDB...' : 'Load Demo Repository'}
        </button>

        <p className="text-[11px] text-slate-400 mt-2 text-center">
          Pre-bundled E-Commerce code with orders, payments, discounts & dead code.
        </p>

        {/* Custom Path Toggle */}
        <div className="mt-3 pt-3 border-t border-slate-800/80">
          <button
            onClick={() => setShowCustomInput(!showCustomInput)}
            className="text-xs text-slate-400 hover:text-slate-200 flex items-center gap-1 transition-colors"
          >
            <FolderOpen className="w-3.5 h-3.5" />
            <span>{showCustomInput ? 'Hide custom path' : 'Analyze custom local path...'}</span>
          </button>

          {showCustomInput && (
            <form onSubmit={handleCustomSubmit} className="mt-2 space-y-2">
              <input
                type="text"
                placeholder="C:\path\to\python\project"
                value={customPath}
                onChange={(e) => setCustomPath(e.target.value)}
                className="w-full px-2.5 py-1.5 text-xs bg-slate-950 border border-slate-800 rounded text-slate-200 placeholder-slate-600 focus:outline-none focus:border-brand-500 font-mono"
              />
              <button
                type="submit"
                disabled={isAnalyzing || !customPath.trim()}
                className="w-full py-1.5 px-2 bg-slate-800 hover:bg-slate-700 text-xs text-slate-200 rounded border border-slate-700 transition-colors disabled:opacity-50 font-medium"
              >
                Analyze & Index Graph
              </button>
            </form>
          )}
        </div>
      </div>

      {/* Codebase Graph Statistics */}
      <div className="p-4 border-b border-slate-800">
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5 mb-3">
          <BarChart3 className="w-3.5 h-3.5 text-brand-500" />
          Graph Topology Metrics
        </span>

        <div className="grid grid-cols-2 gap-2 text-xs">
          <div className="p-2.5 rounded-lg bg-slate-950/60 border border-slate-800/80">
            <span className="text-slate-400 block text-[11px]">Total Nodes</span>
            <span className="text-lg font-bold font-mono text-white">{graphStats?.total_nodes_in_db ?? 0}</span>
          </div>
          <div className="p-2.5 rounded-lg bg-slate-950/60 border border-slate-800/80">
            <span className="text-slate-400 block text-[11px]">Relationships</span>
            <span className="text-lg font-bold font-mono text-emerald-400">{graphStats?.total_edges_in_db ?? 0}</span>
          </div>
          <div className="p-2 rounded bg-slate-950/40 border border-slate-800/60 flex items-center justify-between">
            <span className="text-slate-400 text-[11px]">Files</span>
            <span className="font-mono font-semibold text-blue-400">
              {graphStats?.nodes?.filter(n => n.type === 'File').length ?? 0}
            </span>
          </div>
          <div className="p-2 rounded bg-slate-950/40 border border-slate-800/60 flex items-center justify-between">
            <span className="text-slate-400 text-[11px]">Classes</span>
            <span className="font-mono font-semibold text-purple-400">
              {graphStats?.nodes?.filter(n => n.type === 'Class').length ?? 0}
            </span>
          </div>
          <div className="p-2 rounded bg-slate-950/40 border border-slate-800/60 col-span-2 flex items-center justify-between">
            <span className="text-slate-400 text-[11px]">Functions & Methods</span>
            <span className="font-mono font-semibold text-amber-400">
              {graphStats?.nodes?.filter(n => n.type === 'Function').length ?? 0}
            </span>
          </div>
        </div>
      </div>

      {/* Selected Node Inspector Card */}
      {selectedNode ? (
        <div className="p-4 border-b border-slate-800 bg-slate-950/40">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
              <Info className="w-3.5 h-3.5 text-blue-400" />
              Node Inspector
            </span>
            <span className={`text-[10px] font-semibold uppercase px-1.5 py-0.5 rounded border ${
              selectedNode.type === 'File'
                ? 'bg-blue-950/60 border-blue-800 text-blue-400'
                : selectedNode.type === 'Class'
                ? 'bg-purple-950/60 border-purple-800 text-purple-400'
                : 'bg-amber-950/60 border-amber-800 text-amber-400'
            }`}>
              {selectedNode.type}
            </span>
          </div>

          <div className="space-y-1.5 font-mono text-xs">
            <div>
              <span className="text-slate-400 text-[10px] uppercase block">Entity Name</span>
              <p className="font-bold text-white truncate">{selectedNode.name}</p>
            </div>
            {selectedNode.file && (
              <div>
                <span className="text-slate-400 text-[10px] uppercase block">File Path</span>
                <p className="text-slate-300 text-[11px] truncate">{selectedNode.file}</p>
              </div>
            )}
            {selectedNode.scope && selectedNode.scope !== 'global' && (
              <div>
                <span className="text-slate-400 text-[10px] uppercase block">Class Scope</span>
                <p className="text-purple-300 text-[11px]">{selectedNode.scope}</p>
              </div>
            )}
          </div>

          {(selectedNode.type === 'Function' || selectedNode.type === 'Class') && (
            <button
              onClick={() => onSelectEntityForImpact(selectedNode.name)}
              className="mt-3 w-full py-1.5 px-2 bg-slate-800 hover:bg-slate-700 text-xs text-brand-400 hover:text-brand-300 font-semibold rounded border border-slate-700 flex items-center justify-center gap-1.5 transition-colors"
            >
              <Sparkles className="w-3.5 h-3.5" />
              Run Blast Radius on this {selectedNode.type}
            </button>
          )}
        </div>
      ) : null}

      {/* Graph Visual Legend */}
      <div className="p-4 mt-auto">
        <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 block mb-2">
          Legend
        </span>
        <div className="space-y-1.5 text-xs text-slate-400">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-blue-500 shadow-sm shadow-blue-500/50"></span>
            <span>File Node</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-purple-500 shadow-sm shadow-purple-500/50"></span>
            <span>Class Node</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-500 shadow-sm shadow-amber-500/50"></span>
            <span>Function / Method</span>
          </div>
          <div className="flex items-center gap-2 pt-1 border-t border-slate-800 text-[11px]">
            <span className="w-3 h-0.5 bg-amber-500"></span>
            <span>CALLS relationship</span>
          </div>
          <div className="flex items-center gap-2 text-[11px]">
            <span className="w-3 h-0.5 bg-cyan-500"></span>
            <span>IMPORTS relationship</span>
          </div>
          <div className="flex items-center gap-2 text-[11px]">
            <span className="w-3 h-0.5 bg-purple-500"></span>
            <span>INHERITS_FROM relationship</span>
          </div>
        </div>
      </div>
    </aside>
  );
}
