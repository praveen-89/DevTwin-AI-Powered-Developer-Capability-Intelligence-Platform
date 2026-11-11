"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { apiClient, ApiError } from "@/lib/api-client";
import type {
  SkillGraphResponse,
  RepositoryResponse,
  SkillGraphNodeResponse,
  SkillGraphEdgeResponse,
} from "@/types/api";
import { Shell, PageContainer, PageHeading } from "@/components/layout/shell";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { CardSkeleton } from "@/components/ui/skeleton";
import { EmptyState, InlineError } from "@/components/ui/empty-state";
import { formatBytes } from "@/lib/utils";
import { SkillGraphCanvas } from "@/components/skillgraph/skillgraph-canvas";
import { SkillGraphDetail } from "@/components/skillgraph/skillgraph-detail";
import {
  Layers,
  Box,
  Search,
  LayoutGrid,
  List,
} from "lucide-react";

type NodeFilter = "ALL" | "skill" | "technology" | "concept";
type ViewMode = "canvas" | "list";

export default function SkillGraphPage() {
  const { token } = useAuth();
  const [repos, setRepos] = useState<RepositoryResponse[]>([]);
  const [selectedRepoId, setSelectedRepoId] = useState<string | null>(null);
  const [graph, setGraph] = useState<SkillGraphResponse | null>(null);
  const [loadingRepos, setLoadingRepos] = useState(true);
  const [loadingGraph, setLoadingGraph] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Interactive exploration state
  const [selectedNode, setSelectedNode] = useState<SkillGraphNodeResponse | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<SkillGraphEdgeResponse | null>(null);
  const [filterType, setFilterType] = useState<NodeFilter>("ALL");
  const [searchQuery, setSearchQuery] = useState("");
  const [viewMode, setViewMode] = useState<ViewMode>("canvas");

  useEffect(() => {
    if (!token) {
      setLoadingRepos(false);
      return;
    }
    apiClient
      .getRepositories()
      .then((data) => {
        setRepos(data);
        if (data.length > 0) setSelectedRepoId(data[0].id);
      })
      .catch(() => setError("Could not load repositories."))
      .finally(() => setLoadingRepos(false));
  }, [token]);

  useEffect(() => {
    if (!selectedRepoId) return;
    setLoadingGraph(true);
    setError(null);
    setSelectedNode(null);
    setSelectedEdge(null);
    apiClient
      .getRepositorySkillGraph(selectedRepoId)
      .then(setGraph)
      .catch((err) =>
        setError(err instanceof ApiError ? err.detail : "Failed to load SkillGraph.")
      )
      .finally(() => setLoadingGraph(false));
  }, [selectedRepoId]);

  const totalLangBytes = graph?.languages.reduce((sum, l) => sum + l.bytes, 0) ?? 0;

  const handleSelectNodeById = (nodeId: string) => {
    if (!graph) return;
    const n = graph.nodes.find((item) => item.id === nodeId);
    if (n) {
      setSelectedNode(n);
      setSelectedEdge(null);
    }
  };

  return (
    <Shell pageTitle="SkillGraph">
      <PageContainer>
        <PageHeading
          title="Interactive SkillGraph"
          description="Explore the directed taxonomy of skills, technologies, and concepts extracted from repository analysis."
          actions={
            graph && (
              <div className="flex items-center gap-2">
                <Badge variant="muted">{graph.nodes.length} nodes</Badge>
                <Badge variant="muted">{graph.edges.length} edges</Badge>
              </div>
            )
          }
        />

        {!token && (
          <EmptyState variant="no-github" description="Sign in to view SkillGraph data." />
        )}
        {loadingRepos && <CardSkeleton lines={3} />}

        {repos.length > 0 && (
          <>
            {/* Repository Selector Tabs */}
            <div className="flex flex-wrap gap-1.5" role="tablist" aria-label="Select repository">
              {repos.map((repo) => (
                <button
                  key={repo.id}
                  role="tab"
                  aria-selected={selectedRepoId === repo.id}
                  onClick={() => setSelectedRepoId(repo.id)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-mono transition-all ${
                    selectedRepoId === repo.id
                      ? "bg-cyan-500/15 text-cyan-300 border border-cyan-500/30"
                      : "text-slate-400 border border-slate-700/50 hover:text-slate-200 hover:border-slate-600"
                  }`}
                >
                  {repo.full_name}
                </button>
              ))}
            </div>

            {error && <InlineError message={error} />}

            {loadingGraph && (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
                <div className="md:col-span-2">
                  <CardSkeleton lines={8} />
                </div>
                <div>
                  <CardSkeleton lines={5} />
                </div>
              </div>
            )}

            {!loadingGraph && !graph && !error && (
              <EmptyState
                variant="no-data"
                description="No SkillGraph data found. Run an analysis on this repository to generate nodes and relationships."
              />
            )}

            {!loadingGraph && graph && (
              <div className="space-y-6">
                {/* Graph Controls Toolbar: Filter tabs, Search input, View Switcher */}
                <div className="flex flex-wrap items-center justify-between gap-3 bg-slate-900/60 p-2.5 rounded-xl border border-slate-800/60">
                  {/* Category filters */}
                  <div className="flex items-center gap-1">
                    {(["ALL", "skill", "technology", "concept"] as NodeFilter[]).map((t) => (
                      <button
                        key={t}
                        onClick={() => setFilterType(t)}
                        className={`px-3 py-1.5 rounded-md text-xs font-medium capitalize transition-all ${
                          filterType === t
                            ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/40"
                            : "text-slate-400 hover:text-slate-200"
                        }`}
                      >
                        {t === "ALL" ? "All Categories" : t}
                      </button>
                    ))}
                  </div>

                  {/* Search and view toggle */}
                  <div className="flex items-center gap-2">
                    <div className="relative">
                      <Search
                        className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-500"
                        aria-hidden="true"
                      />
                      <input
                        type="text"
                        placeholder="Search nodes..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="w-40 sm:w-48 pl-8 pr-3 py-1 text-xs rounded-lg bg-slate-800/70 border border-slate-700/60 text-slate-200 placeholder:text-slate-500 focus:outline-none focus:ring-1 focus:ring-cyan-500/60 font-mono"
                        aria-label="Filter nodes by name"
                      />
                    </div>

                    {/* Accessible list vs canvas toggle */}
                    <div className="flex items-center bg-slate-800/80 rounded-lg p-0.5 border border-slate-700/60">
                      <button
                        onClick={() => setViewMode("canvas")}
                        aria-label="Interactive Canvas View"
                        title="Canvas View"
                        className={`p-1.5 rounded-md transition-all ${
                          viewMode === "canvas"
                            ? "bg-cyan-500/20 text-cyan-300"
                            : "text-slate-400 hover:text-slate-200"
                        }`}
                      >
                        <LayoutGrid className="h-3.5 w-3.5" />
                      </button>
                      <button
                        onClick={() => setViewMode("list")}
                        aria-label="Accessible Table View"
                        title="Accessible Table View"
                        className={`p-1.5 rounded-md transition-all ${
                          viewMode === "list"
                            ? "bg-cyan-500/20 text-cyan-300"
                            : "text-slate-400 hover:text-slate-200"
                        }`}
                      >
                        <List className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </div>
                </div>

                {/* Main Interactive Graph & Inspector Section */}
                {graph.nodes.length === 0 ? (
                  <Card>
                    <CardBody>
                      <EmptyState
                        variant="no-data"
                        description="No skill or technology nodes were extracted from this repository. Ensure the repository contains supported source files or package manifests."
                      />
                    </CardBody>
                  </Card>
                ) : (
                  <div className="grid grid-cols-1 lg:grid-cols-3 gap-5 items-start">
                    {/* Graph Canvas or Accessible Table (2 cols on lg) */}
                    <div className="lg:col-span-2 space-y-4">
                      {viewMode === "canvas" ? (
                        <SkillGraphCanvas
                          nodes={graph.nodes}
                          edges={graph.edges}
                          selectedNode={selectedNode}
                          selectedEdge={selectedEdge}
                          onSelectNode={setSelectedNode}
                          onSelectEdge={setSelectedEdge}
                          filterType={filterType}
                          searchQuery={searchQuery}
                        />
                      ) : (
                        /* Accessible Table View for screen-reader & keyboard users */
                        <Card>
                          <CardHeader>
                            <CardTitle as="h3">Taxonomy Nodes & Relationships</CardTitle>
                          </CardHeader>
                          <div className="overflow-x-auto max-h-[500px]">
                            <table className="w-full text-xs" aria-label="Taxonomy nodes table">
                              <thead>
                                <tr className="border-b border-slate-800/60 bg-slate-900/60 text-slate-400">
                                  <th className="text-left px-4 py-2 font-medium">Name</th>
                                  <th className="text-left px-4 py-2 font-medium">Type</th>
                                  <th className="text-left px-4 py-2 font-medium">Domain / Category</th>
                                  <th className="text-left px-4 py-2 font-medium">Action</th>
                                </tr>
                              </thead>
                              <tbody>
                                {graph.nodes
                                  .filter((n) => {
                                    if (filterType !== "ALL" && n.type !== filterType) return false;
                                    if (
                                      searchQuery.trim() &&
                                      !n.name.toLowerCase().includes(searchQuery.toLowerCase().trim())
                                    ) {
                                      return false;
                                    }
                                    return true;
                                  })
                                  .map((node) => (
                                    <tr
                                      key={node.id}
                                      className={`border-b border-slate-800/30 hover:bg-slate-800/20 transition-colors ${
                                        selectedNode?.id === node.id ? "bg-cyan-500/10" : ""
                                      }`}
                                    >
                                      <td className="px-4 py-2 font-mono text-slate-200">
                                        {node.name}
                                      </td>
                                      <td className="px-4 py-2">
                                        <Badge
                                          variant={
                                            node.type === "skill"
                                              ? "accent"
                                              : node.type === "technology"
                                              ? "success"
                                              : "info"
                                          }
                                        >
                                          {node.type}
                                        </Badge>
                                      </td>
                                      <td className="px-4 py-2 text-slate-400">
                                        {node.domain_or_category || "—"}
                                      </td>
                                      <td className="px-4 py-2">
                                        <button
                                          onClick={() => {
                                            setSelectedNode(node);
                                            setSelectedEdge(null);
                                          }}
                                          className="text-xs text-cyan-400 hover:text-cyan-300 underline underline-offset-2"
                                        >
                                          Inspect
                                        </button>
                                      </td>
                                    </tr>
                                  ))}
                              </tbody>
                            </table>
                          </div>
                        </Card>
                      )}
                    </div>

                    {/* Detail Inspector Panel (1 col on lg) */}
                    <div className="lg:col-span-1">
                      <SkillGraphDetail
                        selectedNode={selectedNode}
                        selectedEdge={selectedEdge}
                        allEdges={graph.edges}
                        onClear={() => {
                          setSelectedNode(null);
                          setSelectedEdge(null);
                        }}
                        onSelectNodeById={handleSelectNodeById}
                      />
                    </div>
                  </div>
                )}

                {/* Secondary Composition Cards: Languages & Dependencies */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-5 pt-4">
                  {/* Languages */}
                  <Card>
                    <CardHeader>
                      <CardTitle as="h3" className="flex items-center gap-2">
                        <Layers className="h-4 w-4 text-slate-400" aria-hidden="true" />
                        Language Composition
                      </CardTitle>
                      <Badge variant="muted">{graph.languages.length} languages</Badge>
                    </CardHeader>
                    {graph.languages.length === 0 ? (
                      <EmptyState variant="no-data" description="No language data detected." />
                    ) : (
                      <CardBody className="space-y-3">
                        {graph.languages
                          .sort((a, b) => b.bytes - a.bytes)
                          .map((lang) => {
                            const pct =
                              totalLangBytes > 0 ? (lang.bytes / totalLangBytes) * 100 : 0;
                            return (
                              <div key={lang.language} className="space-y-1">
                                <div className="flex justify-between text-xs">
                                  <span className="text-slate-200 font-mono">{lang.language}</span>
                                  <span className="text-slate-400 tabular-nums font-mono">
                                    {formatBytes(lang.bytes)} ({pct.toFixed(1)}%)
                                  </span>
                                </div>
                                <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
                                  <div
                                    className="h-full rounded-full bg-cyan-500/60"
                                    style={{ width: `${pct}%` }}
                                    aria-hidden="true"
                                  />
                                </div>
                              </div>
                            );
                          })}
                      </CardBody>
                    )}
                  </Card>

                  {/* Dependencies */}
                  <Card>
                    <CardHeader>
                      <CardTitle as="h3" className="flex items-center gap-2">
                        <Box className="h-4 w-4 text-slate-400" aria-hidden="true" />
                        Dependencies Ecosystem
                      </CardTitle>
                      <Badge variant="muted">{graph.dependencies.length}</Badge>
                    </CardHeader>
                    {graph.dependencies.length === 0 ? (
                      <EmptyState variant="no-data" description="No dependencies detected." />
                    ) : (
                      <CardBody className="max-h-64 overflow-y-auto space-y-1">
                        {graph.dependencies.map((dep, i) => (
                          <div
                            key={i}
                            className="flex items-center gap-2 py-1 border-b border-slate-800/30 last:border-0"
                          >
                            <Badge variant="muted" className="text-xs flex-shrink-0">
                              {dep.ecosystem}
                            </Badge>
                            <span className="text-xs font-mono text-slate-300 truncate">
                              {dep.package_name}
                            </span>
                            {dep.version_constraint && (
                              <span className="text-xs text-slate-500 font-mono flex-shrink-0">
                                {dep.version_constraint}
                              </span>
                            )}
                          </div>
                        ))}
                      </CardBody>
                    )}
                  </Card>
                </div>
              </div>
            )}
          </>
        )}
      </PageContainer>
    </Shell>
  );
}
