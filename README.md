# Repère IA — visibilité dans les assistants IA (GEO)

Site : https://outils.vread.fr/visibilite-ia/

Check-list GEO et kit d'auto-test gratuits (10 prompts) pour que les PME vérifient comment ChatGPT, Perplexity,
Gemini, Claude ou Copilot décrivent leur entreprise. Un produit de READ FRANCE SAS. Non affilié aux éditeurs cités.

Téléchargements gratuits (GitHub Releases) :
- `checklist-geo-pme.pdf`
- `kit-auto-test-visibilite-ia.pdf`

Version payante (rapport à 149 € HT) : **pas encore en vente**, aucune commande possible.

## Structure

- `content/` — pages (fragments HTML avec en-tête de métadonnées)
- `pdf/` — sources HTML des PDF publiés en Release
- `build.py` — générateur statique sans dépendance (`python3 build.py` → `_site/`)
- `tests/test_site.py` — vérifications (titres, descriptions, liens internes, sitemap, pas de script tiers)
- `scripts/make_pdf.mjs` — rendu des PDF et de l'image Open Graph (Playwright)
- `scripts/check_live.mjs` — contrôle du site en ligne (rendu 390 px, erreurs console, liens)

```sh
python3 build.py && python3 tests/test_site.py
npm i && node scripts/make_pdf.mjs   # PDF dans dist/
```

Le déploiement GitHub Pages se fait par `.github/workflows/pages.yml` (build + tests + déploiement).

Contenus : CC BY 4.0. Code : MIT. Voir `LICENSE`.
Signaler une erreur : onglet Issues (aucune donnée personnelle, les tickets sont publics).
