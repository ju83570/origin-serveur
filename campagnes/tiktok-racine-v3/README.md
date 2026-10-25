# TikTok ORIGIN — « Ton nombre n'est qu'un début » (V3 RACINE)

Montage 32 s, 1080 × 1920, 30 fps, H.264 / AAC, généré à partir du pack
`ORIGIN_TIKTOK_V3_RACINE_PACK_CLAUDE_CODE.zip` (visuels, fonds sans texte, logo officiel, capture RACINE).

## Versions produites
- `ORIGIN_TikTok_32s_sous-titres.mp4` : habillage sonore + sous-titres incrustés (version principale).
- `ORIGIN_TikTok_32s_muette.mp4` : sans audio, sous-titres incrustés.
- `ORIGIN_TikTok_32s_sans-sous-titres.mp4` : habillage sonore, sans sous-titres (pour poser une voix off ou les sous-titres TikTok).
- `ORIGIN_TikTok_voix_off.srt` : texte de la voix off, minuté.

Les MP4 ne sont pas versionnés ici (dépôt du serveur) ; ils se régénèrent avec les scripts.

## Séquençage
| Scène | Temps | Animation |
|---|---|---|
| 01 | 0–3 s | Zoom vers le visage, titre en 2 temps (pop lumineux) |
| 02 | 3–8 s | Carte de calcul, chiffres révélés un à un avec surlignage + tintement, « = 43 », puis le 7 |
| 03 | 8–11 s | Le 7 surgit puis se transforme en « ? », CTA commentaire |
| 04 | 11–15 s | Les 9 cases s'allument successivement, le 7 se rallume ; mention « non scientifique » |
| 05 | 15–18 s | Bulles de discussion fictives, micro-pause lumineuse sur le CTA |
| 06 | 18–22 s | Coupure nette (noir + silence), la lumière gagne les branches puis les portraits, crescendo |
| 07 | 22–28 s | RACINE, puis la vignette s'agrandit en vraie interface : travelling dans l'arbre, appuis sur Marguerite puis Élise |
| 08 | 28–32 s | Logo officiel plein écran (fichier fourni, mise à l'échelle uniquement), signature et CTA |

Transitions 01→05 : poussées verticales avec flou de bougé. Pastilles de numéro de scène retirées.
Textes et sous-titres tenus hors de la bande basse TikTok et de la colonne droite.

## Régénérer
```
pip install numpy scipy opencv-python-headless pillow
# polices : Cormorant Garamond (SemiBold, Medium, Medium Italic) et Open Sans (Bold, SemiBold) — Google Fonts,
# renommées CG-SemiBold.ttf, CG-Medium.ttf, CG-MediumItalic.ttf, OS-Bold.ttf, OS-SemiBold.ttf
python3 render.py <pack_dézippé> <dossier_polices> <sortie>          # _video_clean.mp4, _video_subs.mp4, .srt
python3 render.py <pack> <polices> <sortie> --preview 1,4.5,9.5,24    # planche d'aperçu
python3 audio.py <sortie>/_audio.wav
```
Puis multiplexer avec ffmpeg (`-c:v copy -c:a aac -b:a 192k -movflags +faststart`).

## Légende TikTok
Tu connais ta date de naissance… mais ton chemin de vie, tu l'as déjà calculé ? ✨ Additionne tous ses chiffres et
réduis le total (sauf les nombres maîtres 11, 22, 33, selon la convention choisie). Écris TON nombre en commentaire 👇
puis partage cette vidéo à une personne que tu aimes pour comparer les vôtres. Et découvre RACINE, l'arbre
généalogique interactif ORIGIN : parce que ton nombre n'est qu'une porte d'entrée sur ton histoire.

#Origin #CheminDeVie #Numérologie #ArbreGénéalogique #Racine #HistoireFamiliale

*La numérologie est une pratique symbolique, sans validation scientifique pour décrire ou prédire la personnalité.*
