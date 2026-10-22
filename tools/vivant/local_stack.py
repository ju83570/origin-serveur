"""PHP/MySQL isolés pour les tests, exposés uniquement sur la boucle locale.

Les secrets éphémères sont créés sous /tmp, jamais affichés ni versionnés.
Usage : python tools/vivant/local_stack.py start|stop
"""
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
STATE = Path('/tmp/origin-vivant-test/state.json')
NETWORK = 'origin-vivant-private-test'
FRONT = 'origin-vivant-loopback-test'
DB = 'origin-vivant-db-test'
PHP = 'origin-vivant-api-test'


def docker(*args, input=None):
    result = subprocess.run(['docker', *args], input=input, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError('Échec Docker : ' + result.stderr[:400])
    return result.stdout.strip()


def sql(statement):
    return docker('exec', '-i', DB, 'sh', '-c',
                  'MYSQL_PWD="$MARIADB_ROOT_PASSWORD" exec mariadb -uroot origin_test -N -B', input=statement)


def start():
    if STATE.exists():
        running=docker('inspect', '--format', '{{.State.Running}}', PHP, DB).splitlines()
        if running != ['true', 'true']:
            raise RuntimeError('Stack enregistrée mais arrêtée ; inspecter uniquement ces ressources de test avant de la recréer.')
        print('Stack de test existante ; API PHP locale sur le port 8090.')
        return
    STATE.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    password = secrets.token_hex(24)
    app_password = secrets.token_hex(24)
    import base64
    config = {
        'site_url': 'http://127.0.0.1:5080/vivant', 'mode': 'test', 'https_required': False,
        'db_dsn': 'mysql:host=db;port=3306;dbname=origin_test;charset=utf8mb4',
        'db_user': 'origin_test', 'db_password': app_password,
        'app_key': base64.b64encode(secrets.token_bytes(32)).decode(),
        'smtp_host': '', 'smtp_user': '', 'smtp_password': '', 'smtp_from': '',
        'stripe_secret': '', 'stripe_webhook_secret': secrets.token_hex(32),
        'stripe_prices': {'individual':'price_IndividualFixture','family':'price_FamilyFixture','mirror':'price_MirrorFixture'},
        'demo_features_enabled': True, 'product_features': {}, 'trusted_proxy_ips': [],
        'test_payments_enabled': False, 'payments_enabled': False,
        'legal_approved': False, 'live_payments_approved': False,
        'family_ready': False, 'mirror_paid_ready': False,
    }
    # Les chaînes générées sont sérialisées, pas interpolées dans un script shell.
    env_file = STATE.parent / 'database.env'
    env_file.write_text(f'MARIADB_ROOT_PASSWORD={password}\nMARIADB_DATABASE=origin_test\nMARIADB_USER=origin_test\nMARIADB_PASSWORD={app_password}\n')
    config_file = STATE.parent / 'origin-vivant-config.php'
    config_file.write_text('<?php return json_decode(' + "'" + json.dumps(config).replace('\\', '\\\\').replace("'", "\\'") + "', true);\n")
    for path in (env_file, config_file):
        path.chmod(0o600)
    created = []
    try:
        docker('network', 'create', '--internal', '--label', 'origin.scope=test', NETWORK)
        created.append('network')
        docker('network', 'create', '--label', 'origin.scope=test', FRONT)
        created.append('front')
        docker('run', '-d', '--rm', '--name', DB, '--label', 'origin.scope=test',
               '--network', NETWORK, '--network-alias', 'db', '--env-file', str(env_file),
               'mariadb:11.4@sha256:250e1609e93c0e6aecf64bfbab2d84d5e89d2481540fe77447ff6c855c3b1873')
        created.append(DB)
        for attempt in range(45):
            try:
                sql('SELECT 1;')
                break
            except RuntimeError:
                time.sleep(1)
        else:
            raise RuntimeError('MySQL ne démarre pas')
        sql((ROOT/'hostinger/vivant/api/schema.sql').read_text())
        docker('run', '-d', '--rm', '--name', PHP, '--label', 'origin.scope=test',
               '--network', FRONT, '-p', '127.0.0.1:8090:8080',
               '-v', f'{ROOT / "hostinger"}:/app:ro',
               '-v', f'{ROOT / "tools/vivant/router.php"}:/router.php:ro',
               '-v', f'{ROOT / "tests/php"}:/tests:ro',
               '-v', f'{config_file}:/config/origin-vivant-config.php:ro',
               '-e', 'ORIGIN_VIVANT_CONFIG=/config/origin-vivant-config.php',
               'origin-vivant-php-test', 'php', '-S', '0.0.0.0:8080', '-t', '/app', '/router.php')
        created.append(PHP)
        docker('network', 'connect', NETWORK, PHP)
        STATE.write_text(json.dumps({'php':PHP, 'db':DB, 'network':NETWORK, 'front':FRONT, 'webhook_secret':config['stripe_webhook_secret']}))
        STATE.chmod(0o600)
    except Exception:
        for resource in reversed(created):
            if resource == 'network':
                docker('network', 'rm', NETWORK)
            elif resource == 'front':
                docker('network', 'rm', FRONT)
            else:
                docker('stop', resource)
        raise
    print('PHP 8.3 / MySQL prêts sur réseau privé. API locale : port 8090. Stripe et SMTP non connectés.')


def stop():
    if not STATE.exists():
        print('Aucune stack enregistrée.')
        return
    for name in (PHP, DB):
        if docker('inspect', '-f', '{{index .Config.Labels "origin.scope"}}', name) != 'test':
            raise RuntimeError('Conteneur hors périmètre de test')
        docker('stop', '--time', '3', name)
        # --rm est asynchrone ; attendre la disparition avant de libérer les réseaux.
        for attempt in range(40):
            if subprocess.run(['docker','container','inspect',name],capture_output=True).returncode:
                break
            time.sleep(.1)
    docker('network', 'rm', NETWORK)
    docker('network', 'rm', FRONT)
    for name in ('state.json', 'database.env', 'origin-vivant-config.php'):
        (STATE.parent/name).unlink()
    print('Stack de test arrêtée ; données et secrets éphémères supprimés.')


if __name__ == '__main__':
    if len(sys.argv) != 2 or sys.argv[1] not in ('start', 'stop'):
        raise SystemExit('Usage : local_stack.py start|stop')
    globals()[sys.argv[1]]()
