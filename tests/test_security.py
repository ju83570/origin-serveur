"""Régressions Y1/Y2/Y3 : fixtures en mémoire, aucun appel Stripe/IA/email."""
from copy import deepcopy
import json
import secrets
import unittest
from unittest.mock import patch

import app as engine
from premium_security import payment_matches
from test_origin import OfflineTest
from demo_support import response


CATALOG={'solo':{'price_id':'price_SoloFixture','amount':1000,'currency':'eur'},
         'couple':{'price_id':'price_CoupleFixture','amount':2000,'currency':'eur'}}


def paid():
    return {'id':'cs_test_fixture_12345','mode':'payment','status':'complete','livemode':False,
            'payment_status':'paid','amount_total':1000,'currency':'eur',
            'line_items':{'has_more':False,'data':[{'quantity':1,'amount_total':1000,
                'price':{'id':'price_SoloFixture','currency':'eur','unit_amount':1000}}]}}


class PaymentSecurityTests(OfflineTest):
    def test_exact_paid_product_is_accepted(self):
        self.assertTrue(payment_matches(paid(),'solo',CATALOG,'test'))

    def test_cross_offer_underpayment_free_subscription_and_mode_confusion_rejected(self):
        cases=[{'amount_total':999},{'amount_total':True},{'payment_status':'no_payment_required'},
               {'status':'open'},{'mode':'subscription'},{'currency':'usd'},{'livemode':True}]
        for change in cases:
            with self.subTest(change=change):self.assertFalse(payment_matches({**paid(),**change},'solo',CATALOG,'test'))
        self.assertFalse(payment_matches(paid(),'couple',CATALOG,'test'))
        self.assertFalse(payment_matches(paid(),'naissance',CATALOG,'test'))
        self.assertFalse(payment_matches(paid(),'solo',{},'test'))
        self.assertFalse(payment_matches(paid(),'solo',CATALOG,''))

    def test_line_items_and_price_are_required(self):
        for path,value in [('quantity',2),('quantity',True),('amount_total',1),('price',{'id':'price_other'})]:
            s=paid();s['line_items']['data'][0][path]=value
            self.assertFalse(payment_matches(s,'solo',CATALOG,'test'))
        for items in ({'has_more':True,'data':paid()['line_items']['data']},{'data':[]},{'has_more':False,'data':[]},{}):
            self.assertFalse(payment_matches({**paid(),'line_items':items},'solo',CATALOG,'test'))

    def test_stripe_adapter_expands_items_and_checks_id_and_catalog(self):
        with patch.object(engine,'STRIPE_KEY',object()), patch.dict('os.environ',{'STRIPE_MODE':'test','STRIPE_PRICE_CATALOG':json.dumps(CATALOG)}), patch.object(engine.requests,'get',return_value=response(paid())) as get:
            self.assertTrue(engine._stripe_verifier(paid()['id'],'solo')[0])
            self.assertEqual(get.call_args.kwargs['params'],{'expand[]':'line_items'})
            self.assertFalse(engine._stripe_verifier(paid()['id'],'couple')[0])
            self.assertFalse(engine._stripe_verifier('cs_test_fixture_other','solo')[0])
        with patch.object(engine,'STRIPE_KEY',object()),patch.dict('os.environ',{'STRIPE_PRICE_CATALOG':'invalid'}),patch.object(engine.requests,'get',return_value=response(paid())):
            self.assertFalse(engine._stripe_verifier(paid()['id'],'solo')[0])

    def test_missing_or_incorrect_webhook_auth_never_starts_work(self):
        with patch.object(engine.threading,'Thread') as thread,patch.object(engine.requests,'post') as post:
            client=engine.app.test_client()
            for secret in ('','weak'):
                with patch.object(engine,'WEBHOOK_SECRET',secret):
                    self.assertEqual(client.post('/webhook',json={}).status_code,503)
            with patch.object(engine,'WEBHOOK_SECRET',secrets.token_urlsafe(32)):
                self.assertEqual(client.post('/webhook',json={}).status_code,401)
                self.assertEqual(client.post('/webhook',json={},headers={'X-ORIGIN-SECRET':'wrong'}).status_code,401)
            thread.assert_not_called();post.assert_not_called()

    def test_gift_codes_have_no_secret_fallback(self):
        for secret in (b'',b'origin',b'short'):
            with patch.object(engine,'_CODES_SECRET',secret):
                with self.assertRaises(RuntimeError):engine.code_creer('solo')
                self.assertFalse(engine.code_verifier('ORG-S-AAAAAA-AAAAAAAA')[0])
        with patch.object(engine,'_CODES_SECRET',secrets.token_bytes(32)):
            code=engine.code_creer('solo')
            self.assertEqual(engine.code_verifier(code),(True,'solo',''))
        with patch.object(engine,'_CODES_SECRET',secrets.token_bytes(32)):
            self.assertFalse(engine.code_verifier(code)[0])


if __name__=='__main__':unittest.main()
