import React, { useState } from 'react';
import { 
  CheckCircle2, 
  AlertCircle, 
  Clock, 
  Terminal, 
  Copy, 
  Check, 
  Layers, 
  ChevronDown, 
  ChevronUp,
  ShieldAlert,
  ArrowRight
} from 'lucide-react';

export default function EvidencePanel({ result, isInvestigating }) {
  const [showCypher, setShowCypher] = useState(false);
  const [copiedIndex, setCopiedIndex] = useState(null);

  if (isInvestigating) {
    return (
      <div className="flex-1 p-6 flex flex-col items-center justify-center text-center text-slate-400">
        <div className="w-8 h-8 border-2 border-brand-500 border-t-transparent rounded-full animate-spin mb-3"></div>
        <p className="text-xs font-mono text-slate-300">Traversing GraphBLAS matrices in FalkorDB...</p>
        <p className="text-[11px] text-slate-400 mt-1">Tracing actual dependencies & call edges</p>
      </div>
    );
  }

  if (!result) {
    return (
      <div className="flex-1 p-6 flex flex-col items-center justify-center text-center text-slate-400">
        <Layers className="w-10 h-10 text-slate-700 mb-2" />
        <p className="text-xs font-medium text-slate-300">No Investigation Run Yet</p>
        <p className="text-[11px] text-slate-400 max-w-xs mt-1">
          Select an investigation mode above (Blast Radius, Call Path, or Dead Code) and click <strong>"Investigate"</strong> to see verified graph evidence.
        </p>
      </div>
    );
  }

  const handleCopyCypher = (text, index) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(index);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  const isSuccess = result.status === 'success';

  return (
    <div className="flex-1 overflow-y-auto p-5 space-y-4 text-xs font-sans">
      {/* Telemetry Header Strip */}
      <div className="flex items-center justify-between bg-slate-950 p-2.5 rounded-lg border border-slate-800">
        <div className="flex items-center gap-2">
          {isSuccess ? (
            <span className="flex items-center gap-1 text-emerald-400 font-semibold uppercase text-[11px]">
              <CheckCircle2 className="w-3.5 h-3.5" /> Verified Graph Result
            </span>
          ) : (
            <span className="flex items-center gap-1 text-amber-400 font-semibold uppercase text-[11px]">
              <AlertCircle className="w-3.5 h-3.5" /> {result.status.replace('_', ' ')}
            </span>
          )}
          <span className="text-slate-400">|</span>
          <span className="text-slate-300 font-mono text-[11px]">{result.target}</span>
        </div>

        <div className="flex items-center gap-3 font-mono text-[11px] text-slate-400">
          <span className="flex items-center gap-1 text-brand-400">
            <Clock className="w-3 h-3" /> {result.telemetry?.execution_time_ms ?? 0} ms
          </span>
          <span>Nodes: {result.telemetry?.nodes_examined ?? 0}</span>
          <span>Rels: {result.telemetry?.relationships_examined ?? 0}</span>
        </div>
      </div>

      {/* Human-Readable Summary */}
      <div className="p-3.5 rounded-lg bg-slate-900/90 border border-slate-800/80 leading-relaxed text-slate-200 whitespace-pre-line">
        {result.summary}
      </div>

      {/* Impact Details Badge Grid (If Impact Mode) */}
      {result.investigation_type === 'impact_analysis' && result.details && (
        <div className="grid grid-cols-3 gap-2">
          <div className="p-2.5 rounded bg-slate-950/60 border border-slate-800 text-center">
            <span className="text-[10px] uppercase font-mono text-slate-400 block">Direct Impacts</span>
            <span className="text-base font-bold font-mono text-rose-400">
              {result.details.direct_impact_count ?? 0}
            </span>
          </div>
          <div className="p-2.5 rounded bg-slate-950/60 border border-slate-800 text-center">
            <span className="text-[10px] uppercase font-mono text-slate-400 block">Indirect Impacts</span>
            <span className="text-base font-bold font-mono text-amber-400">
              {result.details.indirect_impact_count ?? 0}
            </span>
          </div>
          <div className="p-2.5 rounded bg-slate-950/60 border border-slate-800 text-center">
            <span className="text-[10px] uppercase font-mono text-slate-400 block">Impact Score</span>
            <span className="text-base font-bold font-mono text-emerald-400">
              {result.details.impact_score ?? 0}
            </span>
          </div>
        </div>
      )}

      {/* Verified Evidence Path Table */}
      {result.evidence_paths && result.evidence_paths.length > 0 && (
        <div className="space-y-2">
          <span className="text-[11px] uppercase font-mono font-semibold tracking-wider text-slate-400 block">
            Step-by-Step Graph Evidence
          </span>
          <div className="overflow-x-auto rounded-lg border border-slate-800 bg-slate-950">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-slate-900 border-b border-slate-800 text-slate-400 text-[10px] uppercase">
                <tr>
                  <th className="px-3 py-2">#</th>
                  <th className="px-3 py-2">Caller / Source</th>
                  <th className="px-3 py-2">Relation</th>
                  <th className="px-3 py-2">Target</th>
                  <th className="px-3 py-2">Location</th>
                  <th className="px-3 py-2">Impact / Depth</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-slate-300">
                {result.evidence_paths.map((p, idx) => (
                  <tr key={idx} className="hover:bg-slate-900/40">
                    <td className="px-3 py-2 text-slate-400">{p.step || idx + 1}</td>
                    <td className="px-3 py-2 font-semibold text-white">{p.from_node || p.function}</td>
                    <td className="px-3 py-2 text-emerald-400">{p.relationship || p.type || 'CALLS'}</td>
                    <td className="px-3 py-2 text-slate-300">{p.to_node || '—'}</td>
                    <td className="px-3 py-2 text-slate-400 text-[11px] truncate max-w-[150px]">
                      {p.file || p.from_file || '—'} {p.line ? `(L${p.line})` : ''}
                    </td>
                    <td className="px-3 py-2 text-amber-400 text-[11px]">
                      {p.impact || p.reason || (p.confidence ? `Confidence: ${p.confidence}` : 'Direct')}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Raw Cypher Query Inspector Drawer */}
      {result.cypher_queries && result.cypher_queries.length > 0 && (
        <div className="pt-2 border-t border-slate-800/80">
          <button
            onClick={() => setShowCypher(!showCypher)}
            className="flex items-center justify-between w-full p-2 rounded bg-slate-950 border border-slate-800/80 text-xs font-mono text-slate-300 hover:text-white transition-colors"
          >
            <span className="flex items-center gap-1.5 text-emerald-400">
              <Terminal className="w-3.5 h-3.5" />
              Cypher Query Inspector ({result.cypher_queries.length} queries executed)
            </span>
            {showCypher ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>

          {showCypher && (
            <div className="mt-2 space-y-2">
              {result.cypher_queries.map((q, idx) => (
                <div key={idx} className="relative rounded bg-slate-950 border border-slate-800 p-3 font-mono text-[11px]">
                  <div className="flex items-center justify-between mb-1 pb-1 border-b border-slate-800/60 text-slate-400">
                    <span>Query {idx + 1}</span>
                    <button
                      onClick={() => handleCopyCypher(q, idx)}
                      className="flex items-center gap-1 text-[10px] text-slate-400 hover:text-slate-200"
                    >
                      {copiedIndex === idx ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                      {copiedIndex === idx ? 'Copied' : 'Copy'}
                    </button>
                  </div>
                  <pre className="text-emerald-300 overflow-x-auto whitespace-pre-wrap">{q}</pre>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Limitations & Verification Notice */}
      {result.limitations && result.limitations.length > 0 && (
        <div className="p-3 rounded-lg bg-amber-950/20 border border-amber-900/40 text-[11px] text-amber-300/90 space-y-1">
          <div className="flex items-center gap-1.5 font-semibold uppercase tracking-wider text-amber-400 text-[10px]">
            <ShieldAlert className="w-3 h-3" />
            Static Verification Limitations
          </div>
          <ul className="list-disc list-inside space-y-0.5 text-slate-400">
            {result.limitations.map((lim, idx) => (
              <li key={idx}>{lim}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
