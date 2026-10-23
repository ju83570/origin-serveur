# Aperçu web ORIGIN RÉVOLUTION

[Aperçu web léger](https://htmlpreview.github.io/?https://raw.githubusercontent.com/ju83570/origin-serveur/origin-preview-demo/ORIGIN_DEMO.html)

Le 23 octobre, la capture de l'utilisateur Android montre StackBlitz bloqué au
clonage du dépôt. L'import GitHub et le démarrage d'un environnement Node dans
le téléphone sont supprimés du parcours recommandé. La démo actuelle existe
maintenant aussi sous la forme d'un seul fichier `web-preview/ORIGIN_DEMO.html`.

Le bouton utilise le lecteur tiers HTML Preview pour afficher le fichier HTML
public. Le navigateur récupère un document d'environ 1,1 Mo depuis GitHub ; aucun
package, compilation ou WebContainer n'est nécessaire. Le document contient les
styles, scripts et images, ainsi que l'Arbre dans un document intégré de même
origine. Il reste possible de télécharger ce fichier pour le conserver.

## Vérifications et limites

- Six tests navigateur de l'aperçu statique : quatre expériences, persistance
  du Carnet, Arbre → Constellation → Miroir, absence d'API/paiement, reset isolé
  et largeurs 320/390/768/1440 px.
- Cinq tests du document autonome : quatre expériences et Arbre intégré sans
  autre ressource, persistance et reset depuis l'Arbre, aller-retour
  Arbre/Constellation/Miroir, dimensions mobiles et navigation malgré une base
  distante injectée par un lecteur HTML.
- Essai automatisé de compatibilité avec le chargeur officiel HTML Preview,
  révision `787b673198b8f13ac16384325cd380c5c68cf219`, récupéré via l'API GitHub.
  Le chargeur et les réponses HTML sont servis comme fixtures locales dans
  Chromium ; le parcours complet est exercé avec son véritable code.
- **Le service public `htmlpreview.github.io` n'est pas accessible depuis le
  proxy de cet environnement. Son accessibilité et l'affichage sur le téléphone
  de l'utilisateur restent à confirmer.** L'essai local du chargeur ne constitue
  pas un test de disponibilité du service. L'ouverture d'un fichier téléchargé
  dans un navigateur Android n'est pas testée ; `file://` est interdit par la
  politique du Chromium cloud. Le document autonome est testé via HTTP local,
  en interdisant toute requête de ressource supplémentaire.
- GitHub Pages reste désactivé. L'intégration renvoie HTTP 403
  `Resource not accessible by integration` à la création d'un site Pages.
  Aucun site Pages existant n'a été remplacé. Pour un hébergement statique
  indépendant de ce lecteur tiers, le propriétaire peut activer dans
  Settings → Pages : **Deploy from a branch**, branche `origin-preview-demo`,
  dossier `/ (root)`. Aucun domaine personnalisé à ajouter. Cette action n'a
  pas été effectuée et aucune URL Pages active n'est annoncée.

Les sorties sont dans `browser-tests.txt`, `portable-browser-tests.txt` et
`html-reader-compatibility.json`. Les tests et le manifeste permettent de
reconstruire et de contrôler exactement le bundle.

## Périmètre et protection des sources

`tools/vivant/build_web_preview.py` reprend les sources actuelles de
`hostinger/vivant/` et appelle `build_portable_preview.py` pour le document
autonome. Les scripts commerciaux, Python, PHP, bases et configurations privées
ne sont pas inclus. Le serveur Node optionnel n'expose que les fichiers publics
du bundle et refuse les écritures HTTP. Les sources du moteur et les pages
commerciales restent intactes.

- Cinq adultes, dates, liens et récits fictifs nommés « Démo ». Le Miroir et une
  page de Carnet sont préremplis.
- Aucun compte, paiement, sauvegarde distante, Claude/Brevo ou livraison.
- CSP `connect-src 'none'`, `form-action 'none'`, aucun suivi. Le lecteur HTML
  charge seulement le document public avant l'installation de cette politique.
  La navigation dans l'Arbre intégré utilise des messages dont la fenêtre source
  et les fragments de destination sont vérifiés.
- Stockage du bundle classique : `origin_web_preview_*`. Le fichier autonome
  utilise `origin_portable_preview_*`. Aucune réinitialisation n'efface les clés
  de l'application commerciale ou celles de l'autre aperçu. Ne saisir que des
  informations inventées ; le stockage local n'est pas chiffré.
- Le lecteur tiers et GitHub reçoivent les requêtes de chargement du document.
  Le texte saisi dans le Carnet ou l'Arbre n'est pas envoyé par la démo.
- Aucun CNAME, DNS, site Hostinger, fusion dans `main` ou déploiement de
  `origin-famille.fr`.

## Reproduction

```bash
PYTHONDONTWRITEBYTECODE=1 python3 tools/vivant/build_web_preview.py
XDG_CACHE_HOME=/workspace/.cache PYTHONDONTWRITEBYTECODE=1 \
  /workspace/.venvs/origin-serveur/bin/python tests/browser/test_web_preview.py
XDG_CACHE_HOME=/workspace/.cache PYTHONDONTWRITEBYTECODE=1 \
  /workspace/.venvs/origin-serveur/bin/python tests/browser/test_portable_preview.py
```

`manifest.json` donne les empreintes des sources et de tous les fichiers de
l'aperçu, y compris le HTML autonome. Les validations métier antérieures restent
dans `review/issue-3/` et `review/final-2026-10-23/` ; elles ne sont pas présentées
comme de nouveaux tests de ce changement de livraison de l'aperçu.
