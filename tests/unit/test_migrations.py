"""
Unit Tests for Database Migrations & Version Tracking
"""

import os
from alembic.config import Config
from alembic.script import ScriptDirectory


def test_alembic_configuration_and_revisions():
    """Verifies Alembic environment configuration and checks migration scripts."""
    alembic_cfg_path = os.path.join(os.getcwd(), "alembic.ini")
    assert os.path.exists(alembic_cfg_path), "alembic.ini must exist in project root"
    
    config = Config(alembic_cfg_path)
    script_dir = ScriptDirectory.from_config(config)
    
    # Check that revisions exist and baseline heads are discoverable
    heads = script_dir.get_heads()
    assert len(heads) == 1, "There should be exactly one active migration head"
    
    # Check that revisions are tracked in linear order
    revisions = list(script_dir.walk_revisions())
    assert len(revisions) >= 3, "Expected baseline, assessment, and regulatory intel revisions"
    doc_strings = [r.doc for r in revisions if r.doc]
    assert any("master_data_and_tenancy_baseline" in doc or "Initial" in doc for doc in doc_strings)
    assert any("assessment" in doc for doc in doc_strings)
    assert any("regulatory" in doc for doc in doc_strings)
