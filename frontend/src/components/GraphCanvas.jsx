import React, { useRef, useEffect, useState, useMemo, useCallback } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import { ZoomIn, ZoomOut, Maximize2, Loader2, Network } from 'lucide-react';

const NODE_COLORS = {
  File: '#3b82f6',      // Blue
  Class: '#a855f7',     // Purple
  Function: '#f59e0b',  // Amber
  Default: '#94a3b8',   // Slate
};

export default function GraphCanvas({
  data,
  isLoading,
  selectedNode,
  onNodeClick,
  highlightedNodeNames = [],
  highlightedType = 'impact', // 'impact' | 'path'
  theme = 'dark',
}) {
  const fgRef = useRef();
  const containerRef = useRef();
  const [dimensions, setDimensions] = useState({ width: 600, height: 600 });

  const isLight = theme === 'light';

  // Dynamic link colors based on theme
  const linkColors = useMemo(() => ({
    CALLS: '#f59e0b',
    IMPORTS: '#06b6d4',
    INHERITS_FROM: '#c084fc',
    CONTAINS: isLight ? '#cbd5e1' : '#334155',
    Default: isLight ? '#94a3b8' : '#475569',
  }), [isLight]);

  // Update canvas dimensions dynamically
  useEffect(() => {
    function updateDimensions() {
      if (containerRef.current) {
        setDimensions({
          width: containerRef.current.clientWidth || 600,
          height: containerRef.current.clientHeight || 600,
        });
      }
    }
    updateDimensions();
    window.addEventListener('resize', updateDimensions);
    return () => window.removeEventListener('resize', updateDimensions);
  }, []);

  // Format data for react-force-graph
  const graphData = useMemo(() => {
    if (!data?.nodes || data.nodes.length === 0) {
      return { nodes: [], links: [] };
    }

    const nodeIds = new Set(data.nodes.map((n) => n.id));
    const validLinks = (data.links || []).filter(
      (l) => nodeIds.has(l.source) && nodeIds.has(l.target)
    );

    return {
      nodes: data.nodes.map((n) => ({ ...n })),
      links: validLinks.map((l) => ({ ...l })),
    };
  }, [data]);

  // Set of names highlighted by the investigation agent
  const highlightedSet = useMemo(() => {
    return new Set(highlightedNodeNames.map((name) => name?.toLowerCase()));
  }, [highlightedNodeNames]);

  // Tune d3 simulation forces so graph fits naturally and spreads out cleanly
  useEffect(() => {
    if (fgRef.current && graphData.nodes.length > 0) {
      fgRef.current.d3Force('charge')?.strength(-160);
      fgRef.current.d3Force('link')?.distance(65);
    }
  }, [graphData]);

  // Zoom to fit on initial data load
  useEffect(() => {
    if (graphData.nodes.length > 0 && fgRef.current) {
      const timer = setTimeout(() => {
        fgRef.current?.zoomToFit(400, 50);
      }, 350);
      return () => clearTimeout(timer);
    }
  }, [graphData]);

  // Custom node drawing on HTML5 canvas for clean developer aesthetics
  const drawNode = useCallback(
    (node, ctx, globalScale) => {
      const isSelected = selectedNode?.id === node.id;
      const isHighlighted = highlightedSet.has(node.name?.toLowerCase());

      const baseRadius = node.type === 'File' ? 7 : node.type === 'Class' ? 6 : 5;
      const radius = isSelected || isHighlighted ? baseRadius * 1.5 : baseRadius;

      // Outer glow for highlighted/selected nodes
      if (isSelected || isHighlighted) {
        ctx.beginPath();
        ctx.arc(node.x, node.y, radius + 4, 0, 2 * Math.PI, false);
        ctx.fillStyle = isHighlighted
          ? highlightedType === 'impact' ? 'rgba(239, 68, 68, 0.35)' : 'rgba(34, 197, 94, 0.35)'
          : 'rgba(59, 130, 246, 0.4)';
        ctx.fill();
      }

      // Main Node Circle
      ctx.beginPath();
      ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI, false);
      ctx.fillStyle = isHighlighted
        ? highlightedType === 'impact' ? '#ef4444' : '#22c55e'
        : isSelected
        ? '#3b82f6'
        : NODE_COLORS[node.type] || NODE_COLORS.Default;
      ctx.fill();

      // Border outline
      ctx.lineWidth = isSelected || isHighlighted ? 2 : 1;
      ctx.strokeStyle = isSelected || isHighlighted ? '#ffffff' : (isLight ? '#cbd5e1' : '#0f172a');
      ctx.stroke();

      // Node Label (Visible when zoomed in or when selected/highlighted)
      if (globalScale > 0.75 || isSelected || isHighlighted) {
        const label = node.name;
        const fontSize = Math.max(10 / globalScale, 3);
        ctx.font = `${isSelected || isHighlighted ? 'bold ' : ''}${fontSize}px JetBrains Mono, monospace`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'top';

        // Background pill behind text for contrast
        const textWidth = ctx.measureText(label).width;
        ctx.fillStyle = isLight ? 'rgba(255, 255, 255, 0.95)' : 'rgba(15, 23, 42, 0.88)';
        ctx.fillRect(
          node.x - textWidth / 2 - 3,
          node.y + radius + 2,
          textWidth + 6,
          fontSize + 2
        );

        if (isLight) {
          ctx.strokeStyle = '#e2e8f0';
          ctx.lineWidth = 0.5;
          ctx.strokeRect(
            node.x - textWidth / 2 - 3,
            node.y + radius + 2,
            textWidth + 6,
            fontSize + 2
          );
        }

        ctx.fillStyle = isHighlighted
          ? (isLight ? '#b45309' : '#fef08a')
          : isSelected
          ? (isLight ? '#1d4ed8' : '#60a5fa')
          : (isLight ? '#0f172a' : '#cbd5e1');
        ctx.fillText(label, node.x, node.y + radius + 3);
      }
    },
    [selectedNode, highlightedSet, highlightedType, isLight]
  );

  return (
    <div
      ref={containerRef}
      className={`relative w-full h-full overflow-hidden select-none transition-colors duration-200 ${
        isLight ? 'bg-slate-50' : 'bg-slate-950'
      }`}
    >
      {/* Zoom / Canvas Controls */}
      <div className={`absolute top-4 right-4 z-10 flex flex-col gap-1 rounded-lg p-1 shadow-lg backdrop-blur-sm border transition-colors ${
        isLight ? 'bg-white/90 border-slate-200 text-slate-700' : 'bg-slate-900/90 border-slate-800 text-slate-300'
      }`}>
        <button
          onClick={() => fgRef.current?.zoom(fgRef.current.zoom() * 1.3, 300)}
          className={`p-1.5 rounded transition-colors ${isLight ? 'hover:bg-slate-100 hover:text-slate-900' : 'hover:bg-slate-800 hover:text-white'}`}
          title="Zoom In"
        >
          <ZoomIn className="w-4 h-4" />
        </button>
        <button
          onClick={() => fgRef.current?.zoom(fgRef.current.zoom() / 1.3, 300)}
          className={`p-1.5 rounded transition-colors ${isLight ? 'hover:bg-slate-100 hover:text-slate-900' : 'hover:bg-slate-800 hover:text-white'}`}
          title="Zoom Out"
        >
          <ZoomOut className="w-4 h-4" />
        </button>
        <button
          onClick={() => fgRef.current?.zoomToFit(400, 50)}
          className={`p-1.5 rounded transition-colors ${isLight ? 'hover:bg-slate-100 hover:text-slate-900' : 'hover:bg-slate-800 hover:text-white'}`}
          title="Fit to Screen"
        >
          <Maximize2 className="w-4 h-4" />
        </button>
      </div>

      {/* Loading Overlay */}
      {isLoading && (
        <div className={`absolute inset-0 backdrop-blur-sm z-20 flex flex-col items-center justify-center gap-3 ${
          isLight ? 'bg-white/80' : 'bg-slate-950/80'
        }`}>
          <Loader2 className="w-8 h-8 text-brand-500 animate-spin" />
          <span className="text-xs font-mono font-medium text-slate-600 dark:text-slate-300">
            Querying FalkorDB GraphBLAS Engine...
          </span>
        </div>
      )}

      {/* Empty State */}
      {!isLoading && graphData.nodes.length === 0 && (
        <div className="absolute inset-0 z-10 flex flex-col items-center justify-center p-6 text-center">
          <div className={`w-12 h-12 rounded-xl flex items-center justify-center mb-3 shadow-inner border ${
            isLight ? 'bg-white border-slate-200 text-slate-500' : 'bg-slate-900 border-slate-800 text-slate-400'
          }`}>
            <Network className="w-6 h-6" />
          </div>
          <h3 className={`text-sm font-semibold ${isLight ? 'text-slate-800' : 'text-slate-200'}`}>
            No Codebase Graph Loaded
          </h3>
          <p className="text-xs text-slate-500 max-w-sm mt-1">
            Click <strong>"Load Demo Repository"</strong> in the left sidebar to ingest and visualize the e-commerce codebase in FalkorDB.
          </p>
        </div>
      )}

      {/* Force-Directed Canvas */}
      {graphData.nodes.length > 0 && (
        <ForceGraph2D
          ref={fgRef}
          width={dimensions.width}
          height={dimensions.height}
          graphData={graphData}
          nodeCanvasObject={drawNode}
          nodePointerAreaPaint={(node, color, ctx) => {
            ctx.beginPath();
            ctx.arc(node.x, node.y, 9, 0, 2 * Math.PI, false);
            ctx.fillStyle = color;
            ctx.fill();
          }}
          linkColor={(link) => linkColors[link.type] || linkColors.Default}
          linkWidth={(link) => (link.type === 'CALLS' ? 1.5 : 1)}
          linkDirectionalArrowLength={4.5}
          linkDirectionalArrowRelPos={0.92}
          linkCurvature={0.12}
          onNodeClick={(node) => onNodeClick?.(node)}
          cooldownTicks={120}
          d3AlphaDecay={0.02}
          d3VelocityDecay={0.3}
          minZoom={0.2}
          maxZoom={8}
        />
      )}
    </div>
  );
}
