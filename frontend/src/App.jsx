import React, { useState, useEffect, useCallback } from 'react';
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import GraphCanvas from './components/GraphCanvas';
import InvestigationConsole from './components/InvestigationConsole';
import EvidencePanel from './components/EvidencePanel';
import { 
  checkDbHealth, 
  getGraphData, 
  analyzeRepository, 
  runInvestigation 
} from './api/client';
import { AlertTriangle, CheckCircle } from 'lucide-react';

export default function App() {
  const [theme, setTheme] = useState('dark');
  const [dbHealth, setDbHealth] = useState(null);
  const [isRefreshingHealth, setIsRefreshingHealth] = useState(false);

  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const [isLoadingGraph, setIsLoadingGraph] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  const [selectedNode, setSelectedNode] = useState(null);
  const [investigationResult, setInvestigationResult] = useState(null);
  const [isInvestigating, setIsInvestigating] = useState(false);
  const [prefilledTarget, setPrefilledTarget] = useState(null);

  const [notification, setNotification] = useState(null);

  const toggleTheme = () => {
    setTheme((prev) => (prev === 'dark' ? 'light' : 'dark'));
  };

  const showNotification = (message, type = 'info') => {
    setNotification({ message, type });
    setTimeout(() => setNotification(null), 4000);
  };

  // 1. Fetch DB Health
  const loadDbHealth = useCallback(async () => {
    setIsRefreshingHealth(true);
    try {
      const data = await checkDbHealth();
      setDbHealth(data);
    } catch (err) {
      setDbHealth({ status: 'error', error_message: err.message });
    } finally {
      setIsRefreshingHealth(false);
    }
  }, []);

  // 2. Fetch Graph Data
  const loadGraph = useCallback(async () => {
    setIsLoadingGraph(true);
    try {
      const data = await getGraphData('codegraph', 200);
      setGraphData(data);
    } catch (err) {
      showNotification(`Failed to load graph: ${err.message}`, 'error');
    } finally {
      setIsLoadingGraph(false);
    }
  }, []);

  // Initial mount load
  useEffect(() => {
    loadDbHealth();
    loadGraph();
  }, [loadDbHealth, loadGraph]);

  // 3. Ingest Demo Repository
  const handleAnalyzeDemo = async () => {
    setIsAnalyzing(true);
    try {
      const res = await analyzeRepository({ is_demo: true, clean_existing: true });
      showNotification(
        `Demo ingested into FalkorDB in ${res.execution_time_ms}ms (${res.total_nodes_in_db} nodes, ${res.total_relationships_in_db} rels)`,
        'success'
      );
      await loadGraph();
      await loadDbHealth();
    } catch (err) {
      showNotification(`Ingestion failed: ${err.message}`, 'error');
    } finally {
      setIsAnalyzing(false);
    }
  };

  // 4. Ingest Custom Repository
  const handleAnalyzeCustom = async (path) => {
    setIsAnalyzing(true);
    try {
      const res = await analyzeRepository({ repo_path: path, clean_existing: true });
      showNotification(
        `Repository ingested in ${res.execution_time_ms}ms (${res.total_nodes_in_db} nodes)`,
        'success'
      );
      await loadGraph();
      await loadDbHealth();
    } catch (err) {
      showNotification(`Analysis failed: ${err.message}`, 'error');
    } finally {
      setIsAnalyzing(false);
    }
  };

  // 5. Run Investigation
  const handleRunInvestigation = async (params) => {
    setIsInvestigating(true);
    try {
      const res = await runInvestigation({
        ...params,
        graph_name: 'codegraph',
      });
      setInvestigationResult(res);
      showNotification(`Investigation finished in ${res.telemetry?.execution_time_ms ?? 0}ms`, 'success');
    } catch (err) {
      showNotification(`Investigation failed: ${err.message}`, 'error');
    } finally {
      setIsInvestigating(false);
    }
  };

  // Extract highlighted node names from investigation result for graph canvas
  const highlightedNodeNames = React.useMemo(() => {
    if (!investigationResult || investigationResult.status !== 'success') return [];

    const names = [];
    if (investigationResult.target) {
      names.push(investigationResult.target);
    }

    if (investigationResult.details?.direct_impacts) {
      investigationResult.details.direct_impacts.forEach((e) => names.push(e.name));
    }
    if (investigationResult.details?.indirect_impacts) {
      investigationResult.details.indirect_impacts.forEach((e) => names.push(e.name));
    }
    if (investigationResult.details?.path_nodes) {
      investigationResult.details.path_nodes.forEach((n) => names.push(n.name));
    }

    return names;
  }, [investigationResult]);

  const highlightedType = investigationResult?.investigation_type === 'impact_analysis' ? 'impact' : 'path';

  return (
    <div className={`flex flex-col h-screen w-screen overflow-hidden font-sans transition-colors duration-200 ${
      theme === 'light' ? 'theme-light bg-slate-50 text-slate-900' : 'bg-slate-950 text-slate-100'
    }`}>
      {/* Top Header */}
      <Header
        dbHealth={dbHealth}
        onRefreshHealth={loadDbHealth}
        isRefreshing={isRefreshingHealth}
        theme={theme}
        onToggleTheme={toggleTheme}
      />

      {/* Notification Toast */}
      {notification && (
        <div className={`fixed top-20 right-6 z-50 flex items-center gap-2 px-4 py-2.5 rounded-lg border text-xs shadow-2xl backdrop-blur-md animate-in fade-in slide-in-from-top-2 duration-200 ${
          notification.type === 'error'
            ? 'bg-rose-950/90 border-rose-800 text-rose-200 shadow-rose-950/50'
            : 'bg-emerald-950/90 border-emerald-800 text-emerald-200 shadow-emerald-950/50'
        }`}>
          {notification.type === 'error' ? (
            <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
          ) : (
            <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0" />
          )}
          <span className="font-medium">{notification.message}</span>
        </div>
      )}

      {/* Main Split Layout */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left Sidebar */}
        <Sidebar
          graphStats={graphData}
          onAnalyzeDemo={handleAnalyzeDemo}
          onAnalyzeCustom={handleAnalyzeCustom}
          isAnalyzing={isAnalyzing}
          selectedNode={selectedNode}
          onSelectEntityForImpact={(name) => setPrefilledTarget(name)}
        />

        {/* Center / Right Split: Interactive Graph & Investigation Console */}
        <main className="flex-1 flex flex-col min-w-0 h-full overflow-hidden">
          {/* Top Half: Graph Visualization Canvas */}
          <div className="flex-[3] min-h-[350px] relative border-b border-slate-800">
            <GraphCanvas
              data={graphData}
              isLoading={isLoadingGraph}
              selectedNode={selectedNode}
              onNodeClick={(node) => setSelectedNode(node)}
              highlightedNodeNames={highlightedNodeNames}
              highlightedType={highlightedType}
              theme={theme}
            />
          </div>

          {/* Bottom Half: Investigation Agent Console & Evidence Inspector */}
          <div className="flex-[2] min-h-[280px] flex flex-col bg-slate-900/40 overflow-hidden">
            <InvestigationConsole
              onRunInvestigation={handleRunInvestigation}
              isInvestigating={isInvestigating}
              prefilledTarget={prefilledTarget}
            />

            <EvidencePanel
              result={investigationResult}
              isInvestigating={isInvestigating}
            />
          </div>
        </main>
      </div>
    </div>
  );
}
