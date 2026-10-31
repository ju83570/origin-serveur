# Sécurité

Ce dépôt est **public**. Ne jamais y publier : données personnelles de clients ou de familles, photos, PDF de livrets, clés d'API, jetons, mots de passe, valeurs de variables d'environnement, adresses privées.

## Signaler un problème

Écrire à contact@origin-famille.fr en décrivant le problème, **sans** joindre de secret ni de donnée réelle. Pour une faille, ne pas ouvrir d'issue publique détaillée avant correction.

## Si un secret a été publié par erreur

1. Le considérer comme compromis : le **révoquer et le remplacer** chez le fournisseur (Stripe, Brevo, Anthropic, Render…). Supprimer le fichier du dépôt ne suffit pas, l'historique Git le conserve.
2. Prévenir le propriétaire d'ORIGIN.
3. Ensuite seulement, nettoyer l'historique si nécessaire.

## Garde-fous en place

- `.gitignore` : exclut fichiers de secrets, sorties de génération et données de clients.
- CI : analyse de l'**historique complet** à la recherche de secrets (gitleaks) et test local des motifs de clés connus.
- Tests : voir `docs/EXPLOITATION.md`.
