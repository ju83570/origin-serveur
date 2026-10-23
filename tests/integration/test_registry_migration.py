"""Migration additive sur une base temporaire ; jamais de base client."""
from pathlib import Path
import sys
import secrets
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from tools.vivant.local_stack import sql,docker,DB


class RegistryMigrationTests(unittest.TestCase):
    def test_migration_preserves_legacy_rows_without_inventing_entitlements(self):
        self.assertEqual(docker('inspect','-f','{{index .Config.Labels "origin.scope"}}',DB),'test')
        old=(ROOT/'tests/fixtures/schema-before-final.sql').read_text()
        name='origin_migration_test_'+secrets.token_hex(5)
        sql('CREATE DATABASE '+name+' CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;')
        try:
            sql('USE '+name+';\n'+old)
            sql('USE '+name+"; INSERT INTO users(id,email,password_hash,privacy_version,privacy_accepted_at,created_at) VALUES(1,'fixture@example.invalid','unused','test',UTC_TIMESTAMP(),UTC_TIMESTAMP()); INSERT INTO user_state(user_id,sealed_payload,revision,updated_at) VALUES(1,'opaque-legacy-fixture',7,UTC_TIMESTAMP()); INSERT INTO purchases(user_id,product,stripe_session_id,status,created_at) VALUES(1,'mirror','cs_test_legacy_fixture','paid',UTC_TIMESTAMP());")
            before=sql('USE '+name+'; SELECT SHA2(sealed_payload,256),revision FROM user_state WHERE user_id=1;')
            sql('USE '+name+';\n'+(ROOT/'pack-docs/migrations/004_registry_inbox.sql').read_text())
            self.assertEqual(sql('USE '+name+'; SELECT SHA2(sealed_payload,256),revision FROM user_state WHERE user_id=1;'),before)
            self.assertEqual(sql('USE '+name+'; SELECT COUNT(*) FROM purchases;'),'1')
            self.assertEqual(sql('USE '+name+'; SELECT COUNT(*) FROM entitlements;'),'0')
            # Le script peut être relancé ; il ne remplace pas une version sauvegardée.
            sql('USE '+name+';\n'+(ROOT/'pack-docs/migrations/004_registry_inbox.sql').read_text())
            self.assertEqual(sql('USE '+name+'; SELECT revision FROM user_state WHERE user_id=1;'),'7')
        finally:
            sql('DROP DATABASE '+name+';')
