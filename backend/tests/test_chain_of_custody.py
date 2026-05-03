from __future__ import annotations

import time

from app.core.chain_of_custody import ChainOfCustody, ImmutableAuditChain


class TestChainOfCustody:
    def test_initial_state(self):
        coc = ChainOfCustody(
            evidence_id="ev-001",
            evidence_hash="abc123",
            collected_at=time.time(),
            collected_by="analyst1",
        )
        assert coc.evidence_id == "ev-001"
        assert coc.integrity_verified
        assert len(coc.custody_chain) == 0

    def test_add_custody_entry(self):
        coc = ChainOfCustody(
            evidence_id="ev-001",
            evidence_hash="abc123",
            collected_at=time.time(),
            collected_by="analyst1",
        )
        coc.add_custody("analyst2", "transfer", "handoff to lab")
        assert len(coc.custody_chain) == 1
        assert coc.custody_chain[0].actor == "analyst2"
        assert coc.custody_chain[0].signature

    def test_verify_integrity_match(self):
        coc = ChainOfCustody(
            evidence_id="ev-001",
            evidence_hash="abc123",
            collected_at=time.time(),
            collected_by="analyst1",
        )
        assert coc.verify_integrity("abc123")
        assert coc.integrity_verified

    def test_verify_integrity_mismatch(self):
        coc = ChainOfCustody(
            evidence_id="ev-001",
            evidence_hash="abc123",
            collected_at=time.time(),
            collected_by="analyst1",
        )
        assert not coc.verify_integrity("xyz789")
        assert not coc.integrity_verified

    def test_export_chain(self):
        coc = ChainOfCustody(
            evidence_id="ev-001",
            evidence_hash="abc123",
            collected_at=time.time(),
            collected_by="analyst1",
        )
        coc.add_custody("analyst2", "analysis")
        exported = coc.export_chain()
        assert exported["evidence_id"] == "ev-001"
        assert exported["total_transfers"] == 1


class TestImmutableAuditChain:
    def test_add_entry(self):
        chain = ImmutableAuditChain()
        h = chain.add_entry("CREATE", "user1", "case-001")
        assert h
        assert chain.get_entry_count() == 1

    def test_verify_valid_chain(self):
        chain = ImmutableAuditChain()
        chain.add_entry("CREATE", "user1", "case-001")
        chain.add_entry("UPDATE", "user1", "case-001")
        chain.add_entry("READ", "user2", "case-001")
        assert chain.verify_chain()

    def test_chain_linking(self):
        chain = ImmutableAuditChain()
        h1 = chain.add_entry("CREATE", "user1", "case-001")
        h2 = chain.add_entry("UPDATE", "user1", "case-001")
        assert h1 != h2
        entries = chain.get_entries()
        assert entries[1]["previous_hash"] == h1

    def test_empty_chain_verify(self):
        chain = ImmutableAuditChain()
        assert chain.verify_chain()
