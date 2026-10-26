#!/usr/bin/env python3
"""Montage TikTok ORIGIN Famille « La photo » — 10 scènes, 1080x1920, 40 s.

Usage : python3 montage.py            -> genere ORIGIN_FAMILLE_LA_PHOTO_1080x1920.mp4 (muet)
        python3 montage.py voix.mp3   -> ajoute la voix off enregistree

Chaque visuel est anime (zoom lent + leger panoramique) pour eviter l'effet
diaporama statique ; zoom limite a 4 % pour ne jamais rogner les textes,
le logo ni le bandeau du bas.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
VIS = os.path.join(HERE, "VISUELS_9_16_1080x1920")
OUT = os.path.join(HERE, "ORIGIN_FAMILLE_LA_PHOTO_1080x1920.mp4")
FPS = 30
XF = 0.4  # duree des fondus enchaines

# (fichier, duree a l'ecran en s, mouvement) — calendrier du brief
SCENES = [
    ("01_la_photo_intrigante.png", 3, "in"),
    ("02_une_confidence.png", 4, "out"),
    ("03_le_portrait_a_une_histoire.png", 3, "in"),
    ("04_les_souvenirs_vivants.png", 3, "pan"),
    ("05_le_livret_famille.png", 4, "in"),
    ("06_un_extrait_de_pages.png", 5, "in"),
    ("07_en_parler_ensemble.png", 4, "out"),
    ("08_transmettre_a_ses_enfants.png", 3, "in"),
    ("09_racine_arbre_interactif_demo.png", 4, "in"),
    ("10_decouvrir_un_extrait.png", 7, "out"),
]
ZMAX = 1.04


def motion(kind, frames):
    p = f"(on/{frames - 1})"
    if kind == "in":
        z = f"1+{ZMAX - 1}*{p}"
        x, y = "(iw-iw/zoom)/2", "(ih-ih/zoom)/2"
    elif kind == "out":
        z = f"{ZMAX}-{ZMAX - 1}*{p}"
        x, y = "(iw-iw/zoom)/2", "(ih-ih/zoom)/2"
    else:  # pan horizontal doux a zoom fixe
        z = f"{ZMAX}"
        x, y = f"(iw-iw/zoom)*{p}", "(ih-ih/zoom)/2"
    return z, x, y


def main():
    voice = sys.argv[1] if len(sys.argv) > 1 else None
    inputs, filters = [], []
    for i, (f, d, kind) in enumerate(SCENES):
        clip = d + (XF if i < len(SCENES) - 1 else 0)
        frames = round(clip * FPS)
        inputs += ["-loop", "1", "-framerate", str(FPS), "-t", f"{clip}", "-i", os.path.join(VIS, f)]
        z, x, y = motion(kind, frames)
        # sur-echantillonnage x2 avant zoompan pour un mouvement sans saccade
        filters.append(
            f"[{i}:v]scale=2160:3840:flags=lanczos,"
            f"zoompan=z='{z}':x='{x}':y='{y}':d=1:s=1080x1920:fps={FPS},"
            f"trim=duration={clip},setpts=PTS-STARTPTS,format=yuv420p[v{i}]"
        )
    prev, t = "v0", 0.0
    for i in range(1, len(SCENES)):
        t += SCENES[i - 1][1]
        out = f"x{i}"
        filters.append(f"[{prev}][v{i}]xfade=transition=fade:duration={XF}:offset={t:.3f}[{out}]")
        prev = out
    total = sum(d for _, d, _ in SCENES)
    filters.append(f"[{prev}]fade=t=out:st={total - 0.5}:d=0.5,setsar=1[vout]")

    cmd = ["ffmpeg", "-y", *inputs]
    if voice:
        cmd += ["-i", voice]
    cmd += ["-filter_complex", ";".join(filters), "-map", "[vout]"]
    if voice:
        cmd += ["-map", f"{len(SCENES)}:a", "-c:a", "aac", "-b:a", "192k", "-af", f"apad,atrim=0:{total}"]
    cmd += ["-c:v", "libx264", "-preset", "slow", "-crf", "20", "-profile:v", "high",
            "-pix_fmt", "yuv420p", "-r", str(FPS), "-t", str(total), "-movflags", "+faststart", OUT]
    subprocess.run(cmd, check=True)
    print("OK ->", OUT)


if __name__ == "__main__":
    main()
