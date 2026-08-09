import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class EntityGovernanceTests(unittest.TestCase):
    def test_entity_validator(self):
        from tools.validate_entities import validate
        self.assertEqual(validate(ROOT), [])

    def test_id_contract(self):
        from aggie_analytics.entities import CanonicalEntityType, new_canonical_id, validate_canonical_id
        value=new_canonical_id(CanonicalEntityType.PLAYER)
        self.assertTrue(value.startswith("player_"))
        self.assertTrue(validate_canonical_id(value))
        self.assertFalse(validate_canonical_id("player_123"))
        self.assertFalse(validate_canonical_id("cfbd_12345"))

    def test_fuzzy_auto_accept_disabled(self):
        reg=json.loads((ROOT/"configs/entity_registry.json").read_text())
        self.assertFalse(reg["resolution"]["fuzzy_auto_accept_enabled"])
        self.assertEqual(reg["resolution"]["auto_accept_threshold"], "TBD_BY_LABELED_EVIDENCE")

    def test_postgresql_not_mandatory(self):
        reg=json.loads((ROOT/"configs/entity_registry.json").read_text())
        self.assertEqual(reg["storage_decision"]["decision"], "DEFER_POSTGRESQL")

if __name__=="__main__": unittest.main()
