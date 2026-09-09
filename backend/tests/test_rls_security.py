import re
from pathlib import Path

def test_rls_policies_do_not_leak_null_projects():
    """
    Static analysis test to verify that RLS policies do not contain
    the insecure 'OR project_id IS NULL' bypass for repositories.
    """
    # Locate the migrations directory
    backend_dir = Path(__file__).parent.parent
    migrations_dir = backend_dir.parent / "database" / "migrations"
    
    assert migrations_dir.exists(), "Migrations directory not found"
    
    # Check all SQL migrations
    sql_files = list(migrations_dir.glob("*.sql"))
    assert len(sql_files) > 0, "No SQL migrations found"
    
    # We will aggregate the final policy logic by reading sequentially
    repositories_policy_text = ""
    evidence_policy_text = ""
    
    for sql_file in sorted(sql_files):
        content = sql_file.read_text(encoding="utf-8")
        
        # We are looking for the creation of 'repositories_select_own'
        repo_matches = re.findall(
            r'CREATE\s+POLICY\s+"repositories_select_own".*?USING\s*\((.*?)\);',
            content,
            re.IGNORECASE | re.DOTALL
        )
        if repo_matches:
            repositories_policy_text = repo_matches[-1] # take the latest override
            
        # Also check evidence
        evidence_matches = re.findall(
            r'CREATE\s+POLICY\s+"evidence_select_own".*?USING\s*\((.*?)\);',
            content,
            re.IGNORECASE | re.DOTALL
        )
        if evidence_matches:
            evidence_policy_text = evidence_matches[-1]
            
    # Verify the final state of the repository policy does NOT contain the NULL bypass
    assert "project_id IS NULL" not in repositories_policy_text.upper(), \
        "SECURITY VULNERABILITY: repositories RLS policy contains 'project_id IS NULL' bypass."
        
    # Verify evidence doesn't have the observation bypass
    assert "observation_id IS NULL" not in evidence_policy_text.upper(), \
        "SECURITY VULNERABILITY: evidence RLS policy contains 'observation_id IS NULL' bypass."
