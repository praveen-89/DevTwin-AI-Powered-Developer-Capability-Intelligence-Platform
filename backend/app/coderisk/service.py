"""
DevTwin CodeRisk — Persistence Service

Persists CodeRisk findings and underlying factual observations to the database
within session transaction boundaries.
"""

import logging
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.coderisk.analyzer import analyze_repository_risks
from app.coderisk.models import CodeRiskResult
from app.mining.models import MiningResult
from app.models.analysis_run import AnalysisRun
from app.models.observation import Observation
from app.models.risk_finding import RiskFinding

logger = logging.getLogger(__name__)


async def persist_coderisk(
    session: AsyncSession,
    run: AnalysisRun,
    repository_id: uuid.UUID,
    root_dir: Optional[Path],
    mining_result: MiningResult,
) -> CodeRiskResult:
    """
    Executes static risk analysis and atomically persists observations and risk_findings.
    """
    logger.info("Executing CodeRisk static analysis for run %s (repo %s)...", run.id, repository_id)

    findings = analyze_repository_risks(root_dir=root_dir, mining_result=mining_result)

    # 1. Idempotent cleanup for this analysis run
    # Remove existing risk findings and parent RISK_OBSERVED observations for this run
    await session.execute(
        delete(RiskFinding).where(RiskFinding.analysis_run_id == run.id)
    )
    await session.execute(
        delete(Observation).where(
            Observation.analysis_run_id == run.id,
            Observation.type == "RISK_OBSERVED",
        )
    )

    # 2. Persist Observations and RiskFinding records
    for f in findings:
        obs_id = uuid.uuid4()
        session.add(
            Observation(
                id=obs_id,
                analysis_run_id=run.id,
                type="RISK_OBSERVED",
                source_tool="coderisk-v1",
                source_reference={
                    "rule_id": f.rule_id,
                    "title": f.title,
                    "explanation": f.explanation,
                    "file_path": f.file_path,
                    "line_start": f.line_start,
                    "line_end": f.line_end,
                    "evidence_snippet": f.evidence_snippet,
                },
                confidence=f.confidence,
            )
        )

        session.add(
            RiskFinding(
                id=uuid.uuid4(),
                repository_id=repository_id,
                analysis_run_id=run.id,
                observation_id=obs_id,
                commit_id=None,
                category=f.category,
                severity=f.severity,
                confidence=f.confidence,
                risk_type=f.rule_id,
                file_path=f.file_path,
                line_start=f.line_start,
                line_end=f.line_end,
            )
        )

    await session.flush()

    by_cat = Counter(f.category for f in findings)
    by_sev = Counter(f.severity for f in findings)
    now_iso = datetime.now(timezone.utc).isoformat()

    result = CodeRiskResult(
        schema_version="1.0.0",
        analyzer_version="1.0.0",
        total_findings=len(findings),
        findings_by_category=dict(by_cat),
        findings_by_severity=dict(by_sev),
        findings=findings,
        completed_at=now_iso,
    )

    logger.info(
        "CodeRisk analysis completed for run %s: %d findings (%s).",
        run.id,
        result.total_findings,
        dict(by_sev),
    )
    return result
