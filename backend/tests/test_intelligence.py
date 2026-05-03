from __future__ import annotations

import pytest

from app.intelligence.graph_intel import GraphIntelligence, Node, Edge
from app.intelligence.fusion import MultiINTFusionEngine
from app.intelligence.cybint import CYBINTModule, IoCType, ThreatLevel, IndicatorOfCompromise


class TestGraphIntelligence:
    def test_add_entity(self):
        gi = GraphIntelligence()
        gi.add_entity("user1", "John Doe", "person")
        assert "user1" in gi._nodes
        assert gi._nodes["user1"].label == "John Doe"

    def test_add_relationship(self):
        gi = GraphIntelligence()
        gi.add_entity("a", "A", "node")
        gi.add_entity("b", "B", "node")
        gi.add_relationship("a", "b", "KNOWS")
        assert len(gi._edges) == 1
        assert gi._edges[0].source == "a"
        assert gi._edges[0].target == "b"

    def test_find_paths(self):
        gi = GraphIntelligence()
        gi.add_entity("a", "A", "node")
        gi.add_entity("b", "B", "node")
        gi.add_entity("c", "C", "node")
        gi.add_relationship("a", "b", "LINK")
        gi.add_relationship("b", "c", "LINK")
        paths = gi.find_paths("a", "c")
        assert len(paths) > 0
        assert paths[0] == ["a", "b", "c"]

    def test_connected_nodes(self):
        gi = GraphIntelligence()
        gi.add_entity("a", "A", "node")
        gi.add_entity("b", "B", "node")
        gi.add_entity("c", "C", "node")
        gi.add_relationship("a", "b", "LINK")
        gi.add_relationship("a", "c", "LINK")
        result = gi.find_connected_nodes("a")
        assert len(result.nodes) == 3
        assert len(result.edges) == 2

    def test_influence_score(self):
        gi = GraphIntelligence()
        gi.add_entity("center", "Center", "node")
        for i in range(5):
            gi.add_entity(f"n{i}", f"Node {i}", "node")
            gi.add_relationship("center", f"n{i}", "LINK")
        assert gi.get_influence_score("center") == 5

    def test_export_cypher(self):
        gi = GraphIntelligence()
        gi.add_entity("a", "A", "person")
        gi.add_entity("b", "B", "person")
        gi.add_relationship("a", "b", "KNOWS")
        statements = gi.export_neo4j_cypher()
        assert len(statements) == 3

    def test_to_json_roundtrip(self):
        gi = GraphIntelligence()
        gi.add_entity("a", "A", "node", {"key": "value"})
        gi.add_relationship("a", "b", "LINK")
        json_str = gi.to_json()
        gi2 = GraphIntelligence.from_dict(gi.to_dict())
        assert len(gi2._nodes) == 1
        assert len(gi2._edges) == 1


class TestCYBINTModule:
    def test_extract_ip_iocs(self):
        cybint = CYBINTModule()
        text = "Server 192.168.1.1 contacted malicious host 10.0.0.5"
        iocs = cybint.extract_iocs(text)
        ip_iocs = [i for i in iocs if i.ioc_type == IoCType.IP]
        assert len(ip_iocs) == 2

    def test_extract_email_iocs(self):
        cybint = CYBINTModule()
        text = "Contact admin@example.com or user@test.org"
        iocs = cybint.extract_iocs(text)
        email_iocs = [i for i in iocs if i.ioc_type == IoCType.EMAIL]
        assert len(email_iocs) == 2

    def test_extract_hash_iocs(self):
        cybint = CYBINTModule()
        text = "File hash: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        iocs = cybint.extract_iocs(text)
        sha256_iocs = [i for i in iocs if i.ioc_type == IoCType.HASH_SHA256]
        assert len(sha256_iocs) == 1

    def test_mitre_mapping(self):
        cybint = CYBINTModule()
        ioc = IndicatorOfCompromise(value="test@email.com", ioc_type=IoCType.EMAIL)
        techniques = cybint.map_to_mitre(ioc)
        assert "T1566" in techniques


class TestMultiINTFusionEngine:
    @pytest.mark.asyncio
    async def test_fuse_empty(self):
        engine = MultiINTFusionEngine()
        result = await engine.fuse(target="test_target")
        assert result.fusion_id
        assert result.input_sources == []
        assert result.confidence >= 0.3

    @pytest.mark.asyncio
    async def test_fuse_with_osint(self):
        engine = MultiINTFusionEngine()
        result = await engine.fuse(
            target="example.com",
            osint_results=[{"id": "1", "data": "test"}],
        )
        assert "OSINT" in result.input_sources
        assert len(result.graph_data["nodes"]) > 0

    @pytest.mark.asyncio
    async def test_fuse_threat_assessment(self):
        engine = MultiINTFusionEngine()
        from app.intelligence.darkweb import DarkWebResult
        result = await engine.fuse(
            target="target1",
            darkweb_results=[DarkWebResult(
                source="test", url="http://test.com", title="test",
                content_snippet="test", risk_score=8.5,
            )],
        )
        assert "DARKWEB" in result.input_sources
        assert len(result.correlated_entities) > 0
        assert len(result.recommendations) > 0
