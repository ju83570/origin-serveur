# Préparer une préproduction Hostinger sans toucher au site public

Ne pas exécuter les notices originales du ZIP sur le domaine public. Le travail
actuel est local et non déployé. Une installation Hostinger nécessitera une
validation distincte et un emplacement de test autorisé.

Confirmer d'abord le type d'hébergement : le Website Builder n'exécute pas cette
API PHP. Prévoir un sous-domaine PHP/HTML de préproduction, PHP >= 8.3, PDO_MYSQL,
sodium, mbstring, curl et openssl, HTTPS et une base MySQL/InnoDB dédiée.
Le moteur Python reste hébergé séparément ; Docker et la façade locale ne sont
pas requis sur Hostinger.

Le modèle `config-exemple/origin-vivant-config.php.EXEMPLE` reste une copie du
pack initial. Lors de la création du vrai fichier privé, utiliser l'URL de
préproduction autorisée, jamais celle du site public. Placer la configuration
au-dessus du DOCUMENT_ROOT et conserver sa clé de chiffrement dans un coffre.
Ne pas envoyer de valeurs dans le chat ni les committer.

Paramètres supplémentaires de cette branche :

```php
'mode' => 'test',
'test_payments_enabled' => false,
'payments_enabled' => false,
'live_payments_approved' => false,
'family_ready' => false,
'mirror_paid_ready' => false,
'https_required' => true,
'trusted_proxy_ips' => [],
```

Pour un checkout Stripe de test, renseigner une vraie clé **test**, les vrais
prix **test** et le secret webhook **test** par la configuration sécurisée, puis
activer explicitement `test_payments_enabled` pour une offre testable. Ne pas
basculer le site en production pour tester. Les anciens drapeaux de paiement ne
suffisent plus à activer du live ; `live_payments_approved` reste false.
Les événements `livemode=true` sont rejetés en mode test.

N'ajouter des proxys de confiance que si leurs adresses exactes sont connues.
Ne pas désactiver HTTPS pour l'hébergement de test distant. La valeur false du
helper Docker est réservée aux connexions loopback de la machine de développement.

Pour une base NEUVE, importer le `hostinger/vivant/api/schema.sql` de cette
branche. Si une base de TEST utilise déjà le schéma du ZIP initial, la migration
`migrations/002_session_version.sql` ajoute le compteur nécessaire à la révocation
des sessions. Ne pas l'exécuter une deuxième fois ni sur une base existante
inconnue ; aucune migration distante n'a été exécutée dans cette mission.

Pour une base déjà passée aux correctifs du 22 octobre (migration 003), la
migration additive `migrations/004_registry_inbox.sql` installe le registre
normalisé. Elle ne convertit pas automatiquement les anciens achats en droits.
Faire d'abord une sauvegarde et un essai de restauration sur une copie dédiée,
puis rapprocher les commandes historiques avec Stripe. Le nouveau code et ce
schéma doivent être recettés ensemble. Voir
[la procédure détaillée](../review/final-2026-10-23/EXPLOITATION_TEST.md), notamment
pour le worker CLI obligatoire et la conservation des anciennes clés.

Vérifier ensuite inscription, email de confirmation, connexion, récupération,
restauration carnet/arbre, suppression, paiement test, portail et cycle complet
d'abonnement. Les tests locaux ne prouvent pas le fonctionnement du SMTP,
d'Apache/.htaccess, du TLS ou de MySQL du compte Hostinger.

Les sources de l'Arbre et du Miroir restent sur une même origine pour leurs
échanges locaux. Les données du navigateur sont locales et non chiffrées ; la
sauvegarde distante est volontaire et chiffrée au repos. Ce n'est pas du
chiffrement de bout en bout. Finaliser les textes de confidentialité et CGV selon
les pratiques réelles avant toute ouverture commerciale.
