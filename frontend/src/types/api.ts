/**
 * DevTwin Frontend — API Type Definitions
 * Strictly maps to backend FastAPI schemas from Step 6J (docs/12_API_SPECIFICATION.md).
 */

export interface DeveloperResponse {
  id: string;
  auth_user_id: string;
  created_at: string;
  updated_at: string;
}

export interface ProjectResponse {
  id: string;
  name: string;
  created_at: string;
}

export interface RepositoryResponse {
  id: string;
  project_id: string | null;
  github_repo_id: number;
  owner_login: string;
  name: string;
  full_name: string;
  url: string;
  default_branch: string;
  visibility: "public" | "private";
  synced_at: string | null;
  created_at: string;
}

export type AnalysisJobStatus = "QUEUED" | "PROCESSING" | "COMPLETED" | "FAILED";

export interface AnalysisJobCreateResponse {
  id: string;
  job_id: string;
  status: AnalysisJobStatus;
}

export interface AnalysisJobResponse {
  id: string;
  job_id: string;
  repository_id: string;
  status: AnalysisJobStatus;
  attempt_count: number;
  requested_at: string;
  completed_at: string | null;
}

export type AnalysisRunStatus =
  | "QUEUED"
  | "FETCHING"
  | "MINING"
  | "SKILL_GRAPH"
  | "CODE_RISK"
  | "CAPABILITY"
  | "COMPLETED"
  | "FAILED";

export interface AnalysisRunResponse {
  id: string;
  analysis_job_id: string;
  repository_id: string;
  status: AnalysisRunStatus;
  analyzer_version: string;
  schema_version: string;
  error_code: string | null;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface GitHubStatusResponse {
  is_connected: boolean;
  is_installed: boolean;
  is_disconnected: boolean;
  github_username: string | null;
}

export interface GitHubRepositoryOption {
  github_repo_id: number;
  name: string;
  full_name: string;
  visibility: "public" | "private" | string;
  private: boolean;
  default_branch: string;
}

export interface CapabilityTargetResponse {
  target_type: "skill" | "technology" | "concept";
  target_id: string;
  target_name: string;
  domain_or_category: string | null;
}

export interface DeveloperCapabilityResponse {
  id: string;
  developer_id: string;
  target: CapabilityTargetResponse;
  score: number;
  confidence: number;
  scoring_version: string;
  updated_at: string;
}

export interface DeveloperCapabilityListResponse {
  items: DeveloperCapabilityResponse[];
  total: number;
  limit: number;
  offset: number;
}

export interface CapabilityHistoryItemResponse {
  id: string;
  capability_id: string;
  analysis_run_id: string | null;
  target: CapabilityTargetResponse;
  score: number;
  confidence: number;
  scoring_version: string;
  recorded_at: string;
}

export interface CapabilityHistoryListResponse {
  items: CapabilityHistoryItemResponse[];
  total: number;
  limit: number;
  offset: number;
}

export interface EvidenceTaxonomyRef {
  id: string;
  name: string;
  type: "skill" | "technology" | "concept";
}

export interface EvidenceSourceProvenance {
  observation_id?: string | null;
  source_tool?: string | null;
  observation_type?: string | null;
  file_path?: string | null;
  line_start?: number | null;
  line_end?: number | null;
  rule_id?: string | null;
}

export interface EvidenceResponse {
  id: string;
  type: "MENTION" | "USAGE" | "APPLIED_ENGINEERING" | "DEMONSTRATED_OUTCOME";
  strength: number;
  directness: number;
  reliability: number;
  polarity: number;
  recency: string;
  created_at: string;
  skills: EvidenceTaxonomyRef[];
  technologies: EvidenceTaxonomyRef[];
  concepts: EvidenceTaxonomyRef[];
  provenance?: EvidenceSourceProvenance | null;
}

export interface EvidenceListResponse {
  items: EvidenceResponse[];
  total: number;
  limit: number;
  offset: number;
}

export type RiskSeverity = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export interface RiskFindingResponse {
  id: string;
  repository_id: string;
  analysis_run_id: string;
  category: "SECURITY" | "RELIABILITY" | "TESTING" | "MAINTAINABILITY" | "DEPENDENCY" | "ARCHITECTURE" | string;
  severity: RiskSeverity;
  confidence: number;
  risk_type: string;
  file_path: string | null;
  line_start: number | null;
  line_end: number | null;
  detected_at: string;
}

export interface RiskFindingListResponse {
  items: RiskFindingResponse[];
  total: number;
  limit: number;
  offset: number;
  analysis_run_id: string | null;
}

export interface SkillGraphLanguageResponse {
  language: string;
  bytes: number;
}

export interface SkillGraphDependencyResponse {
  ecosystem: string;
  package_name: string;
  version_constraint: string | null;
}

export interface SkillGraphNodeResponse {
  id: string;
  name: string;
  type: "skill" | "technology" | "concept";
  domain_or_category: string | null;
}

export interface SkillGraphEdgeResponse {
  source_id: string;
  target_id: string;
  source_name: string;
  target_name: string;
  relation_type: string;
}

export interface SkillGraphResponse {
  repository_id: string;
  analysis_run_id: string | null;
  languages: SkillGraphLanguageResponse[];
  dependencies: SkillGraphDependencyResponse[];
  nodes: SkillGraphNodeResponse[];
  edges: SkillGraphEdgeResponse[];
}
