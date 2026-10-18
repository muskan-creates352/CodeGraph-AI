import React, { useState, useEffect } from 'react';
import { 
  Sparkles, 
  Flame, 
  Route, 
  Skull, 
  ArrowRight, 
  Sliders, 
  Send,
  Zap,
  HelpCircle
} from 'lucide-react';

export default function InvestigationConsole({
  onRunInvestigation,
  isInvestigating,
  prefilledTarget,
}) {
  const [mode, setMode] = useState('impact'); // 'impact' | 'path' | 'dead_code'
  const [target, setTarget] = useState('calculate_discount');
  const [source, setSource] = useState('post_checkout_endpoint');
  const [destination, setDestination] = useState('format_log_entry');
  const [maxDepth, setMaxDepth] = useState(5);

  // When a user clicks a node in the graph, prefill the target
  useEffect(() => {
    if (prefilledTarget) {
      setMode('impact');
      setTarget(prefilledTarget);
    }
  }, [prefilledTarget]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (mode === 'impact') {
      onRunInvestigation({ mode: 'impact', target, max_depth: maxDepth });
    } else if (mode === 'path') {
      onRunInvestigation({ mode: 'path', source, destination });
    } else if (mode === 'dead_code') {
      onRunInvestigation({ mode: 'dead_code' });
    }
  };

  const applyPreset = (presetMode, params) => {
    setMode(presetMode);
    if (params.target) setTarget(params.target);
    if (params.source) setSource(params.source);
    if (params.destination) setDestination(params.destination);

    onRunInvestigation({
      mode: presetMode,
      ...params,
      max_depth: maxDepth,
    });
  };

  return (
    <div className="border-b border-slate-800 bg-slate-900/80 p-4 shrink-0">
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
          <Sparkles className="w-3.5 h-3.5 text-brand-500" />
          Codebase Investigation Agent
        </span>
        <span className="text-[11px] font-mono text-slate-400">
          Acts directly on FalkorDB GraphBLAS
        </span>
      </div>

      {/* Mode Tabs */}
      <div className="flex gap-1.5 p-1 rounded-lg bg-slate-950/80 border border-slate-800/80 mb-3">
        <button
          onClick={() => setMode('impact')}
          className={`flex-1 py-1.5 px-3 rounded-md text-xs font-medium flex items-center justify-center gap-1.5 transition-all ${
            mode === 'impact'
              ? 'bg-slate-800 text-white shadow-sm border border-slate-700/80 text-rose-300'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <Flame className="w-3.5 h-3.5 text-rose-400" />
          Blast Radius / Impact
        </button>

        <button
          onClick={() => setMode('path')}
          className={`flex-1 py-1.5 px-3 rounded-md text-xs font-medium flex items-center justify-center gap-1.5 transition-all ${
            mode === 'path'
              ? 'bg-slate-800 text-white shadow-sm border border-slate-700/80 text-emerald-300'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <Route className="w-3.5 h-3.5 text-emerald-400" />
          Call Path Tracing
        </button>

        <button
          onClick={() => setMode('dead_code')}
          className={`flex-1 py-1.5 px-3 rounded-md text-xs font-medium flex items-center justify-center gap-1.5 transition-all ${
            mode === 'dead_code'
              ? 'bg-slate-800 text-white shadow-sm border border-slate-700/80 text-amber-300'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <Skull className="w-3.5 h-3.5 text-amber-400" />
          Dead Code Detection
        </button>
      </div>

      {/* Presets Row */}
      <div className="flex items-center gap-1.5 mb-3 overflow-x-auto pb-1 text-xs">
        <span className="text-[11px] text-slate-400 uppercase font-semibold flex items-center gap-1 shrink-0">
          <Zap className="w-3 h-3 text-amber-400" /> Presets:
        </span>

        {mode === 'impact' && (
          <>
            <button
              onClick={() => applyPreset('impact', { target: 'calculate_discount' })}
              className="px-2 py-0.5 rounded bg-slate-800/80 hover:bg-slate-800 border border-slate-700/60 text-slate-300 text-[11px] font-mono shrink-0 transition-colors"
            >
              calculate_discount
            </button>
            <button
              onClick={() => applyPreset('impact', { target: 'charge_credit_card' })}
              className="px-2 py-0.5 rounded bg-slate-800/80 hover:bg-slate-800 border border-slate-700/60 text-slate-300 text-[11px] font-mono shrink-0 transition-colors"
            >
              charge_credit_card
            </button>
            <button
              onClick={() => applyPreset('impact', { target: 'OrderService' })}
              className="px-2 py-0.5 rounded bg-slate-800/80 hover:bg-slate-800 border border-slate-700/60 text-slate-300 text-[11px] font-mono shrink-0 transition-colors"
            >
              OrderService (Class)
            </button>
          </>
        )}

        {mode === 'path' && (
          <>
            <button
              onClick={() => applyPreset('path', { source: 'post_checkout_endpoint', destination: 'format_log_entry' })}
              className="px-2 py-0.5 rounded bg-slate-800/80 hover:bg-slate-800 border border-slate-700/60 text-slate-300 text-[11px] font-mono shrink-0 transition-colors"
            >
              post_checkout ➔ format_log
            </button>
            <button
              onClick={() => applyPreset('path', { source: 'checkout_order', destination: 'charge_credit_card' })}
              className="px-2 py-0.5 rounded bg-slate-800/80 hover:bg-slate-800 border border-slate-700/60 text-slate-300 text-[11px] font-mono shrink-0 transition-colors"
            >
              checkout_order ➔ charge_credit_card
            </button>
          </>
        )}

        {mode === 'dead_code' && (
          <button
            onClick={() => applyPreset('dead_code', {})}
            className="px-2 py-0.5 rounded bg-slate-800/80 hover:bg-slate-800 border border-slate-700/60 text-slate-300 text-[11px] font-mono shrink-0 transition-colors"
          >
            Scan for Orphan Helpers
          </button>
        )}
      </div>

      {/* Input Form */}
      <form onSubmit={handleSubmit} className="flex flex-wrap items-center gap-2.5">
        {mode === 'impact' && (
          <>
            <div className="flex-1 min-w-[200px]">
              <label className="block text-[10px] uppercase font-mono text-slate-400 mb-1">
                Target Function / Class to Change
              </label>
              <input
                type="text"
                value={target}
                onChange={(e) => setTarget(e.target.value)}
                placeholder="e.g. calculate_discount"
                className="w-full px-3 py-1.5 text-xs bg-slate-950 border border-slate-800 rounded font-mono text-slate-100 placeholder-slate-600 focus:outline-none focus:border-brand-500"
              />
            </div>
            <div className="w-24">
              <label className="block text-[10px] uppercase font-mono text-slate-400 mb-1">
                Max Hops ({maxDepth})
              </label>
              <input
                type="range"
                min="1"
                max="8"
                value={maxDepth}
                onChange={(e) => setMaxDepth(parseInt(e.target.value))}
                className="w-full accent-brand-500"
              />
            </div>
          </>
        )}

        {mode === 'path' && (
          <>
            <div className="flex-1 min-w-[150px]">
              <label className="block text-[10px] uppercase font-mono text-slate-400 mb-1">Source Function</label>
              <input
                type="text"
                value={source}
                onChange={(e) => setSource(e.target.value)}
                placeholder="e.g. post_checkout_endpoint"
                className="w-full px-3 py-1.5 text-xs bg-slate-950 border border-slate-800 rounded font-mono text-slate-100 focus:outline-none focus:border-brand-500"
              />
            </div>
            <ArrowRight className="w-4 h-4 text-slate-400 mt-4 shrink-0" />
            <div className="flex-1 min-w-[150px]">
              <label className="block text-[10px] uppercase font-mono text-slate-400 mb-1">Destination Function</label>
              <input
                type="text"
                value={destination}
                onChange={(e) => setDestination(e.target.value)}
                placeholder="e.g. format_log_entry"
                className="w-full px-3 py-1.5 text-xs bg-slate-950 border border-slate-800 rounded font-mono text-slate-100 focus:outline-none focus:border-brand-500"
              />
            </div>
          </>
        )}

        {mode === 'dead_code' && (
          <div className="flex-1 text-xs text-slate-400 italic">
            Agent will analyze incoming CALLS edges across FalkorDB and report unreferenced candidates.
          </div>
        )}

        <button
          type="submit"
          disabled={isInvestigating}
          className="self-end px-4 py-1.5 rounded bg-brand-600 hover:bg-brand-500 text-slate-950 font-semibold text-xs flex items-center gap-1.5 shadow-md shadow-brand-500/20 active:scale-95 transition-all disabled:opacity-50"
        >
          <Send className={`w-3.5 h-3.5 ${isInvestigating ? 'animate-spin' : ''}`} />
          {isInvestigating ? 'Querying FalkorDB...' : 'Investigate'}
        </button>
      </form>
    </div>
  );
}
