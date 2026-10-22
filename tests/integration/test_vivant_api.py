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
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from uuid import uuid4

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
        sql('DELETE FROM rate_limits; DELETE FROM rate_limit_counters;')

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
        self.assertEqual(self.call('save',{'state':payload,'base_revision':0}).status_code,200)
        sealed=sql(f'SELECT sealed_payload FROM user_state WHERE user_id={self.uid};')
        self.assertNotIn('note privée test',sealed)
        self.assertEqual(self.call('load',{}).json()['state'],payload)
        stranger=requests.Session()
        try:
            status=stranger.get(BASE,params={'op':'status'},timeout=10)
            for cookie in stranger.cookies: cookie.secure=False
            self.assertEqual(stranger.post(BASE,params={'op':'load'},json={},headers={'X-CSRF-Token':status.json()['csrf']},timeout=10).status_code,401)
        finally: stranger.close()
        self.assertEqual(self.call('save',{'state':{'text':'x'*751000},'base_revision':1}).status_code,413)
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
        # Un événement signé sans commande canonique n'accorde AUCUN droit.
        self.assertEqual(int(sql(f"SELECT COUNT(*) FROM purchases WHERE user_id={self.uid};")),0)

    def test_failed_event_rolls_back_then_can_be_retried(self):
        order,session,items=self.order()
        event=self.fixture_event('checkout.session.completed',session)
        # Vrai endpoint signé, Stripe déconnecté : aucun faux succès.
        self.assertEqual(self.webhook(event).status_code,503)
        self.assertEqual(sql(f"SELECT status FROM stripe_events WHERE event_id='{event['id']}';"),'received')
        responses=self.checkout_responses(session,items)
        wrong=deepcopy(responses);wrong[f"checkout/sessions/{session['id']}/line_items"]['data'][0]['price']['id']='price_WrongFixture'
        self.assertFalse(self.service('event',event=event,responses=wrong)['ok'])
        self.assertEqual(sql(f"SELECT status FROM stripe_events WHERE event_id='{event['id']}';"),'received')
        self.assertEqual(sql(f"SELECT status FROM orders WHERE order_id='{order}';"),'pending')
        self.assertEqual(self.service('event',event=event,responses=responses)['status'],'processed')
        self.assertTrue(self.service('event',event=event,responses=responses)['duplicate'])

    def test_webhook_before_checkout_response_can_bind_the_canonical_order(self):
        oid,session,items=self.order()
        sql(f"UPDATE orders SET stripe_session_id=NULL WHERE order_id='{oid}';")
        result=self.service('event',event=self.fixture_event('checkout.session.completed',session),responses=self.checkout_responses(session,items))
        self.assertEqual(result['status'],'processed')
        self.assertEqual(sql(f"SELECT stripe_session_id FROM orders WHERE order_id='{oid}';"),session['id'])
        self.assertTrue(self.service('rights')['mirror_paid'])
        other={**session,'id':'cs_test_fixture_other'}
        self.assertFalse(self.service('event',event=self.fixture_event('checkout.session.completed',other),responses={})['ok'])

    def backup(self,text='note privée test',tree=True):
        return {'format':'origin-vivant-cloud-2','carnet':{'draft':{},'mirrors':[],'memories':[{'text':text}],'checkins':[]},'tree':{'demo':False,'people':[{'id':'a','name':'Lina'}]} if tree else None}

    def service(self,kind,**values):
        data={'kind':kind,'uid':self.uid,**values}
        return json.loads(docker('exec','-i',PHP,'php','/tests/service.php',input=json.dumps(data)))

    def fixture_event(self,kind,obj):
        return {'id':'evt_fixture_'+secrets.token_hex(8),'type':kind,'livemode':False,'data':{'object':obj}}

    def order(self,product='mirror',status='pending'):
        oid=str(uuid4());sid='cs_test_fixture_'+secrets.token_hex(8);customer='cus_fixture_'+secrets.token_hex(8)
        sql(f"UPDATE users SET stripe_customer_id='{customer}' WHERE id={self.uid};")
        price={'mirror':'price_MirrorFixture','individual':'price_IndividualFixture','family':'price_FamilyFixture'}[product]
        # Centimes de fixture UNIQUEMENT, ne définissent aucun tarif commercial.
        sql(f"INSERT INTO orders(order_id,user_id,product,environment,price_id,amount,currency,status,stripe_customer_id,stripe_session_id,created_at,expires_at) VALUES('{oid}',{self.uid},'{product}','test','{price}',1000,'eur','{status}','{customer}','{sid}',UTC_TIMESTAMP(),DATE_ADD(UTC_TIMESTAMP(),INTERVAL 1 DAY));")
        session={'id':sid,'livemode':False,'client_reference_id':oid,'customer':customer,'metadata':{'origin_order_id':oid,'plan':product},'mode':'payment' if product=='mirror' else 'subscription','payment_status':'paid','status':'complete','amount_total':1000,'currency':'eur','payment_intent':'pi_fixture_'+secrets.token_hex(8)}
        items={'has_more':False,'data':[{'quantity':1,'amount_total':1000,'price':{'id':price,'currency':'eur','unit_amount':1000}}]}
        return oid,session,items

    def checkout_responses(self,session,items):
        return {'checkout/sessions/'+session['id']:session,'checkout/sessions/'+session['id']+'/line_items':items}

    def test_revision_conflicts_and_recovery_versions(self):
        first=self.backup('première')
        self.assertEqual(self.call('save',{'state':first}).status_code,409)
        self.assertEqual(self.call('save',{'state':first,'base_revision':0}).json()['revision'],1)
        self.assertEqual(self.call('save',{'state':self.backup('seconde'),'base_revision':1}).json()['revision'],2)
        stale=self.call('save',{'state':self.backup('ancienne copie'),'base_revision':1})
        self.assertEqual(stale.status_code,409)
        self.assertEqual(self.call('load',{}).json()['state']['carnet']['memories'][0]['text'],'seconde')
        self.assertEqual(self.call('load',{'revision':1}).json()['state'],first)
        self.assertEqual(len(self.call('versions',{}).json()['versions']),1)
        self.assertEqual(self.call('save',{'state':{'format':'future'},'base_revision':2}).status_code,422)
        self.assertEqual(self.call('load',{}).json()['revision'],2)

    def test_competing_saves_have_one_winner(self):
        # Clients indépendants : l'ancienne révision ne peut pas gagner deux fois.
        headers={'X-CSRF-Token':self.csrf,'Cookie':'; '.join(f'{c.name}={c.value}' for c in self.session.cookies)}
        def save(text):return requests.post(BASE,params={'op':'save'},json={'state':self.backup(text),'base_revision':0},headers=headers,timeout=10).status_code
        with ThreadPoolExecutor(max_workers=2) as pool:codes=list(pool.map(save,['appareil A','appareil B']))
        self.assertEqual(sorted(codes),[200,409])

    def test_unreadable_backup_cannot_be_overwritten(self):
        self.assertEqual(self.call('save',{'state':self.backup(),'base_revision':0}).status_code,200)
        sql(f"UPDATE user_state SET sealed_payload='ov1:missing:invalid' WHERE user_id={self.uid};")
        self.assertEqual(self.call('save',{'state':self.backup('écrasement'),'base_revision':1}).status_code,503)
        self.assertEqual(sql(f'SELECT sealed_payload FROM user_state WHERE user_id={self.uid};'),'ov1:missing:invalid')

    def test_export_and_recovery_remain_available_without_entitlement(self):
        state=self.backup();self.assertEqual(self.call('save',{'state':state,'base_revision':0}).status_code,200)
        # Lanceur CLI désactive explicitement les droits de démonstration.
        self.assertEqual(self.service('rights')['features'],[])
        self.assertEqual(self.service('load')['state'],state)
        denied=self.service('save',state=self.backup('autre'),base_revision=1)
        self.assertEqual(denied['code'],'product_required')
        self.assertEqual(self.call('export',{}).json()['state'],state)

    def test_async_checkout_refund_and_late_completion(self):
        oid,session,items=self.order();pending={**session,'payment_status':'unpaid'}
        event=self.fixture_event('checkout.session.completed',pending)
        self.assertEqual(self.service('event',event=event,responses=self.checkout_responses(pending,items))['status'],'processed')
        self.assertFalse(self.service('rights')['mirror_paid'])
        event=self.fixture_event('checkout.session.async_payment_succeeded',session)
        self.assertEqual(self.service('event',event=event,responses=self.checkout_responses(session,items))['status'],'processed')
        rights=self.service('rights');self.assertTrue(rights['mirror_paid']);self.assertEqual(rights['features'],['mirror_deep'])
        refund=self.fixture_event('charge.refunded',{'payment_intent':session['payment_intent'],'amount_refunded':1})
        self.assertEqual(self.service('event',event=refund,responses={})['status'],'processed')
        self.assertFalse(self.service('rights')['mirror_paid'])
        late=self.fixture_event('checkout.session.completed',session)
        self.assertEqual(self.service('event',event=late,responses={})['status'],'processed')
        self.assertEqual(sql(f"SELECT status FROM orders WHERE order_id='{oid}';"),'refunded')

    def test_paid_checkout_offer_amount_owner_and_environment_mismatches(self):
        for field,value in [('amount_total',1),('currency','usd'),('customer','cus_other'),('client_reference_id','other'),('livemode',True)]:
            with self.subTest(field=field):
                oid,session,items=self.order();session[field]=value
                result=self.service('event',event=self.fixture_event('checkout.session.completed',session),responses=self.checkout_responses(session,items))
                self.assertFalse(result['ok'])
                self.assertEqual(sql(f"SELECT status FROM orders WHERE order_id='{oid}';"),'pending')

    def test_subscription_plan_from_price_and_out_of_order_cancellation(self):
        oid,session,items=self.order('individual')
        sid='sub_fixture_'+secrets.token_hex(8);session['subscription']=sid
        sub={'id':sid,'customer':session['customer'],'livemode':False,'metadata':{'plan':'family','origin_order_id':oid},'status':'active',
             'items':{'has_more':False,'data':[{'quantity':1,'price':{'id':'price_IndividualFixture'},'current_period_end':int(time.time())+3600}]}}
        responses={**self.checkout_responses(session,items),'subscriptions/'+sid:sub}
        self.assertEqual(self.service('event',event=self.fixture_event('checkout.session.completed',session),responses=responses)['status'],'processed')
        rights=self.service('rights');self.assertEqual(rights['plans'],['individual']);self.assertEqual(rights['features'],['cloud_carnet'])
        # Ne pas écraser l'arbre hérité lors d'une rétrogradation vers le carnet.
        saved=self.backup();self.assertEqual(self.call('save',{'state':saved,'base_revision':0}).status_code,200)
        denied=self.service('save',state=self.backup('modification'),base_revision=1)
        # arbre identique : conservé ; changement de l'arbre : refusé
        self.assertTrue(denied['ok'])
        changed=self.backup();changed['tree']['people'][0]['name']='Autre'
        self.assertEqual(self.service('save',state=changed,base_revision=2)['code'],'tree_product_required')
        no_tree=self.backup(tree=False)
        self.assertTrue(self.service('save',state=no_tree,base_revision=2)['ok'])
        self.assertEqual(self.service('load')['state']['tree'],saved['tree'])
        past={**sub,'status':'past_due'}
        self.service('event',event=self.fixture_event('invoice.payment_failed',{'subscription':sid}),responses={'subscriptions/'+sid:past})
        self.assertEqual(self.service('rights')['features'],[])
        self.assertIsNotNone(self.service('load')['state'])
        self.service('event',event=self.fixture_event('customer.subscription.deleted',{**sub,'status':'canceled'}),responses={})
        self.service('event',event=self.fixture_event('customer.subscription.updated',sub),responses={'subscriptions/'+sid:sub})
        self.assertEqual(sql(f"SELECT status FROM subscriptions WHERE stripe_subscription_id='{sid}';"),'canceled')

    def test_account_deletion_requires_password_and_removes_backup_history(self):
        for n in range(2):self.assertEqual(self.call('save',{'state':self.backup(str(n)),'base_revision':n}).status_code,200)
        self.assertEqual(self.call('delete',{'confirm':'SUPPRIMER','password':'wrong'}).status_code,403)
        self.assertEqual(self.call('delete',{'confirm':'SUPPRIMER','password':self.password}).status_code,200)
        for table in ['users','user_state','user_state_history']:
            column='id' if table=='users' else 'user_id'
            self.assertEqual(int(sql(f'SELECT COUNT(*) FROM {table} WHERE {column}={self.uid};')),0)

    def test_non_entitling_subscription_still_blocks_account_deletion(self):
        sql(f"INSERT INTO subscriptions(user_id,stripe_subscription_id,plan,status,updated_at) VALUES({self.uid},'sub_fixture_{secrets.token_hex(6)}','individual','paused',UTC_TIMESTAMP());")
        self.assertEqual(self.call('delete',{'confirm':'SUPPRIMER','password':self.password}).json()['code'],'billing_active')

    def test_login_limits_account_without_blocking_all_proxy_users(self):
        for _ in range(11):
            self.assertEqual(self.call('login',{'email':self.email,'password':'wrong'}).status_code,401)
        self.assertEqual(self.call('login',{'email':self.email,'password':'wrong'}).status_code,429)
        other='absent-'+secrets.token_hex(6)+'@example.invalid'
        self.assertEqual(self.call('login',{'email':other,'password':'wrong'}).status_code,401)

    def checkout_fixture(self):
        customer='cus_fixture_'+secrets.token_hex(8);sid='cs_test_fixture_'+secrets.token_hex(8)
        sql(f"UPDATE users SET stripe_customer_id='{customer}' WHERE id={self.uid};")
        return {'prices/price_MirrorFixture':{'id':'price_MirrorFixture','livemode':False,'active':True,'currency':'eur','unit_amount':1000,'type':'one_time'},
                'checkout/sessions':{'id':sid,'status':'open','url':'https://checkout.stripe.com/c/pay/fixture'},
                'checkout/sessions/'+sid:{'id':sid,'status':'open','url':'https://checkout.stripe.com/c/pay/fixture'}}

    def test_checkout_has_a_common_order_id_and_reuses_pending_payment(self):
        responses=self.checkout_fixture()
        first=self.service('checkout',responses=responses)
        self.assertTrue(first['ok'])
        post=next(c for c in first['fixture_calls'] if c['method']=='POST')
        self.assertEqual(post['params']['client_reference_id'],first['order_id'])
        self.assertEqual(post['params']['metadata']['origin_order_id'],first['order_id'])
        self.assertEqual(post['idempotency'],'origin-checkout-'+first['order_id'])
        second=self.service('checkout',responses=responses)
        self.assertEqual(second['order_id'],first['order_id'])
        self.assertFalse(any(c['method']=='POST' for c in second['fixture_calls']))
        self.assertEqual(int(sql(f'SELECT COUNT(*) FROM orders WHERE user_id={self.uid};')),1)

    def test_checkout_retry_after_ambiguous_timeout_keeps_idempotency_key(self):
        responses=self.checkout_fixture()
        self.assertFalse(self.service('checkout',responses=responses,timeout=True)['ok'])
        oid=sql(f'SELECT order_id FROM orders WHERE user_id={self.uid};')
        self.assertNotEqual(oid,'')
        second=self.service('checkout',responses=responses)
        self.assertEqual(second['order_id'],oid)
        post=next(c for c in second['fixture_calls'] if c['method']=='POST')
        self.assertEqual(post['idempotency'],'origin-checkout-'+oid)


if __name__=='__main__':
    unittest.main(verbosity=2)
