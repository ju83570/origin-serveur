# ORIGIN Famille — TikTok cinématique « Tu sais d'où tu viens ? »

`ORIGIN_FAMILLE_CINEMATIQUE_1080x1920.mp4` : 1080×1920, 30 i/s, H.264 + AAC, 43,6 s, effets sonores seuls.

## Déroulé
| # | Temps | Visuel | Caméra | Transition sortante |
|---|---|---|---|---|
| 01 | 0,0 s | Tu sais d'où tu viens ? | mise au point + zoom avant | flash doré |
| 02 | 3,6 s | Puis un jour… cette photo | zoom arrière | zoom traversant |
| 03 | 7,8 s | Alors mes parents… | zoom avant | whip pan horizontal |
| 04 | 12,0 s | Avec RACINE | zoom arrière | light leak |
| 05 | 16,6 s | J'ai découvert leurs vies | zoom avant | zoom traversant |
| 06 | 21,0 s | Chaque souvenir ajouté | zoom arrière | whip pan vertical |
| 07 | 25,2 s | Lire ce qu'ils ont vécu | zoom avant | light leak |
| 08 | 29,8 s | Et maintenant… | zoom arrière | whip pan horizontal |
| 09 | 34,0 s | Aujourd'hui, nos enfants | zoom avant | flash doré + impact |
| 10 | 38,2 s | CTA « Découvrir ORIGIN » | recul puis plan fixe, halo pulsant + reflet sur le bouton et le logo | fondu au noir |

Effets permanents : poussière dorée et bokeh flottants, light leaks chauds, grain argentique, vignettage, reflet lumineux qui passe sur chaque titre.

## Son
Effets sonores seuls (pas de musique) pour ajouter un son TikTok par-dessus : whoosh à chaque transition, petits impacts, battement de cœur des scènes 7 à 9, montée + impact sur le CTA. Niveau volontairement discret (≈ -20 LUFS) pour rester sous la musique.
Dans TikTok, choisissez la musique dans la Commercial Music Library (obligatoire pour un compte professionnel), puis réglez « Son original » vers 50–70 %.
La version avec musique originale reste disponible : `python3 montage_cinematique.py --avec-musique`.

## Régénérer
```
python3 montage_cinematique.py            # rendu final (~10 min)
python3 montage_cinematique.py --preview  # aperçu rapide 540x960
```
Durées, mouvements et transitions : liste `SCENES` en tête de `montage_cinematique.py`.

## À vérifier avant publication
- Le bouton « Découvrir ORIGIN » et les pictos sont dans le bas de l'image (≈ 65–80 % de la hauteur) : vérifiez dans l'aperçu TikTok qu'ils ne sont pas masqués par la légende.
- RACINE (scènes 04, 09, 10) : confirmez que l'arbre interactif est bien disponible à la vente.
- Mise en scène fictive (« Marcel, né en 1898 en Dordogne », etc.) : ne pas la présenter comme un témoignage client réel.
