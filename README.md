# Repère IA — visibilité dans les assistants IA (GEO)

Site : https://visibilite-ia.jalonel.com/

2026-10-16: moved to https://visibilite-ia.jalonel.com/ (brand Jalonel, a brand of READ FRANCE SAS). Ancienne adresse
https://outils.vread.fr/visibilite-ia/ : redirection 301 de GitHub Pages vers la même page sur le nouveau domaine.

Check-list GEO et kit d'auto-test gratuits (10 prompts) pour que les PME vérifient comment ChatGPT, Perplexity,
Gemini, Claude ou Copilot décrivent leur entreprise. Une marque Jalonel (Jalonel est une marque de READ FRANCE SAS). Non affilié aux éditeurs cités.

Téléchargements gratuits (GitHub Releases) :
- `checklist-geo-pme.pdf`
- `kit-auto-test-visibilite-ia.pdf`

Version payante (rapport à 149 € HT) : **pas encore en vente**, aucune commande possible.

## Mesure d'audience (depuis le 2026-10-13)

`assets/mesure.js` (compteur d'audience anonyme, `v:2`, robots / navigateurs automatisés / `octave_notrack=1` comptés à
part) et `assets/cro.js` (compteurs agrégés de comportement) sont copiés **à l'identique** depuis
`VREAD-corp/octave-checkout` (`gas/web/`, ne jamais modifier les copies). Chargés sur chaque page par `build.py`
(`data-site="visibilite-ia"`, avec empreinte `?v=`), ils envoient l'action `track` au backend France `octave-pay-gas`, qui
accepte ce site (`mesure.js` déduit l'identifiant `visibilite-ia` de l'hôte `visibilite-ia.jalonel.com` ; `cro.js` :
`data-hosts="visibilite-ia.jalonel.com outils.vread.fr"`). Clics comptés : PDF gratuits (`free_download`) et page « version payante » (`cta_click`). Aucun cookie,
aucun identifiant, rien sous Do Not Track / GPC ; nos tests ajoutent `?octave_notrack=1`. Détails :
`content/confidentialite.html`. Après une mise à jour du snippet maître : recopier les deux fichiers puis
`node tests/cro.check.mjs assets/cro.js`.

## Structure

- `content/` — pages (fragments HTML avec en-tête de métadonnées)
- `pdf/` — sources HTML des PDF publiés en Release
- `build.py` — générateur statique sans dépendance (`python3 build.py` → `_site/`)
- `tests/test_site.py` — vérifications (titres, descriptions, liens internes, sitemap, pas de script tiers)
- `scripts/make_pdf.mjs` — rendu des PDF et de l'image Open Graph (Playwright)
- `scripts/check_live.mjs` — contrôle du site en ligne (rendu 390 px, erreurs console, liens)

Le site est servi à la racine `/` de `https://visibilite-ia.jalonel.com/` (origine dans `site.json`) ; `build.py` écrit aussi `CNAME` et la clé
IndexNow `5be19f56d46ca3d2553bee28ebfa8edd.txt` à la racine de `_site/`.

```sh
python3 build.py && python3 tests/test_site.py
npm i && node scripts/make_pdf.mjs   # PDF dans dist/
```

Le déploiement GitHub Pages se fait par `.github/workflows/pages.yml` (build + tests + déploiement).

Contenus : CC BY 4.0. Code : MIT. Voir `LICENSE`.
Signaler une erreur : onglet Issues (aucune donnée personnelle, les tickets sont publics).
