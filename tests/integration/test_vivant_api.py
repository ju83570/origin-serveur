"""Contrôles PHP/MySQL réels sur la stack Docker locale dédiée.

Les comptes, mots de passe et événements de paiement sont des fixtures de TEST.
L'envoi SMTP et l'API Stripe ne sont pas sollicités.
"""
import hashlib
import hmac
import json
from pathlib import Path
import secrets
import sys
import time
import unittest

import requests

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from tools.vivant.local_stack import docker, sql, STATE, PHP

BASE='http://127.0.0.1:5080/vivant/api/'


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.webhook_secret=json.loads(STATE.read_text())['webhook_secret']
        if docker('inspect','-f','{{index .Config.Labels "origin.scope"}}',PHP) != 'test':
            raise RuntimeError('Ces tests nécessitent la stack locale dédiée')
        sql('DELETE FROM rate_limits;')

    def setUp(self):
        self.email=f'test-{secrets.token_hex(6)}@example.invalid'
        self.password=secrets.token_urlsafe(24)
        hashed=docker('exec','-i',PHP,'php','-r','echo password_hash(stream_get_contents(STDIN), PASSWORD_DEFAULT);',input=self.password)
        sql(f"INSERT INTO users(email,password_hash,verified_at,privacy_version,privacy_accepted_at,created_at) VALUES('{self.email}','{hashed}',UTC_TIMESTAMP(),'test',UTC_TIMESTAMP(),UTC_TIMESTAMP());")
        self.uid=int(sql(f"SELECT id FROM users WHERE email='{self.email}';"))
        self.session=requests.Session()
        self.addCleanup(self.session.close)
        result=self.session.get(BASE,params={'op':'status'},timeout=10)
        self.assertEqual(result.status_code,200,result.text)
        self.assertIn('secure',result.headers.get('Set-Cookie','').lower())
        self.assertIn('httponly',result.headers.get('Set-Cookie','').lower())
        # Seulement dans le client de test HTTP loopback ; le serveur conserve Secure.
        for cookie in self.session.cookies: cookie.secure=False
        self.csrf=result.json()['csrf']
        login=self.call('login',{'email':self.email,'password':self.password})
        self.assertEqual(login.status_code,200,login.text)
        for cookie in self.session.cookies: cookie.secure=False
        self.csrf=login.json()['csrf']

    def call(self,op,data,csrf=True):
        return self.session.post(BASE,params={'op':op},json=data,headers={'X-CSRF-Token':self.csrf} if csrf else {},timeout=10)

    def event(self,event_id,uid=None,customer=None):
        return {'id':event_id,'type':'checkout.session.completed','livemode':False,'data':{'object':{
            'id':'cs_test_fixture_'+secrets.token_hex(6),'client_reference_id':str(uid or self.uid),
            'customer':customer,'mode':'payment','payment_status':'paid','metadata':{'plan':'mirror'}}}}

    def webhook(self,event,age=0,valid=True):
        raw=json.dumps(event,separators=(',',':')).encode();timestamp=str(int(time.time())+age)
        signature=hmac.new(self.webhook_secret.encode(),timestamp.encode()+b'.'+raw,hashlib.sha256).hexdigest() if valid else '0'*64
        return requests.post(BASE,params={'op':'webhook'},data=raw,headers={'Stripe-Signature':f't={timestamp},v1={signature}','Content-Type':'application/json'},timeout=10)

    def test_sessions_csrf_and_disabled_checkout(self):
        self.assertEqual(self.call('save',{'state':{}},csrf=False).status_code,403)
        self.assertEqual(self.call('checkout',{'plan':'individual'}).status_code,503)
        status=self.session.get(BASE,params={'op':'status'},timeout=10)
        self.assertEqual(status.json()['user']['email'],self.email)
        self.assertFalse(status.json()['payments_enabled'])
        self.assertTrue(status.json()['stripe_test_mode'])
        self.assertNotIn('password_hash',status.text)

    def test_encrypted_backup_roundtrip_and_isolation(self):
        payload={'format':'origin-vivant-cloud-2','carnet':{'draft':{},'mirrors':[],'memories':[{'text':'note privée test'}],'checkins':[]},'tree':{'demo':False,'people':[{'id':'a','name':'Lina'}]}}
        self.assertEqual(self.call('save',{'state':payload}).status_code,200)
        sealed=sql(f'SELECT sealed_payload FROM user_state WHERE user_id={self.uid};')
        self.assertNotIn('note privée test',sealed)
        self.assertEqual(self.call('load',{}).json()['state'],payload)
        stranger=requests.Session()
        try:
            status=stranger.get(BASE,params={'op':'status'},timeout=10)
            for cookie in stranger.cookies: cookie.secure=False
            self.assertEqual(stranger.post(BASE,params={'op':'load'},json={},headers={'X-CSRF-Token':status.json()['csrf']},timeout=10).status_code,401)
        finally: stranger.close()
        self.assertEqual(self.call('save',{'state':{'text':'x'*751000}}).status_code,413)
        sql(f"UPDATE user_state SET sealed_payload='invalid' WHERE user_id={self.uid};")
        result=self.call('load',{})
        self.assertEqual(result.status_code,503)
        self.assertEqual(result.json()['code'],'backup_unreadable')

    def test_password_reset_consumes_token_and_revokes_old_session(self):
        token=secrets.token_hex(32)
        digest=hashlib.sha256(token.encode()).hexdigest()
        sql(f"INSERT INTO password_resets(user_id,token_hash,expires_at) VALUES({self.uid},'{digest}',DATE_ADD(UTC_TIMESTAMP(),INTERVAL 45 MINUTE));")
        data={'token':token,'password':secrets.token_urlsafe(24)}
        self.assertEqual(self.call('password_reset',data).status_code,200)
        self.assertIsNone(self.session.get(BASE,params={'op':'status'},timeout=10).json()['user'])
        self.assertEqual(self.call('password_reset',data).status_code,410)

    def test_signed_webhook_is_idempotent_and_rejects_live_and_expired_events(self):
        event=self.event('evt_fixture_'+secrets.token_hex(6))
        self.assertEqual(self.webhook(event,valid=False).status_code,400)
        self.assertEqual(self.webhook(event,age=-600).status_code,400)
        self.assertEqual(self.webhook({**event,'livemode':True}).status_code,400)
        self.assertEqual(self.webhook(event).status_code,200)
        self.assertTrue(self.webhook(event).json()['duplicate'])
        self.assertEqual(int(sql(f"SELECT COUNT(*) FROM purchases WHERE user_id={self.uid};")),1)

    def test_failed_event_rolls_back_then_can_be_retried(self):
        customer='cus_fixture_'+secrets.token_hex(6)
        # Un autre compte possède déjà ce client : la contrainte doit bloquer l'opération.
        sql(f"INSERT INTO users(email,password_hash,stripe_customer_id,privacy_version,privacy_accepted_at,created_at) VALUES('owner-{secrets.token_hex(5)}@example.invalid','unused','{customer}','test',UTC_TIMESTAMP(),UTC_TIMESTAMP());")
        event=self.event('evt_fixture_'+secrets.token_hex(6),customer=customer)
        self.assertEqual(self.webhook(event).status_code,503)
        self.assertEqual(int(sql(f"SELECT COUNT(*) FROM stripe_events WHERE event_id='{event['id']}';")),0)
        sql(f"UPDATE users SET stripe_customer_id=NULL WHERE stripe_customer_id='{customer}';")
        self.assertEqual(self.webhook(event).status_code,200)
        self.assertEqual(int(sql(f"SELECT COUNT(*) FROM stripe_events WHERE event_id='{event['id']}';")),1)


if __name__=='__main__':
    unittest.main(verbosity=2)
