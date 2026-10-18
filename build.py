#!/usr/bin/env python3
"""Tiny static site builder (stdlib only).

Reads site.json + content/**/*.html fragments (front matter in a leading
HTML comment), wraps them in one layout and writes _site/ with sitemap.xml,
robots.txt, CNAME, the IndexNow key file and 404.html. Placeholders usable in fragments: {{base}}, {{asset}},
{{release}} (base URL of the free downloads, served from telechargements/), {{contact}} (public e-mail address).
"""
import hashlib
import html
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "_site"


def load_site():
    site = json.loads((ROOT / "site.json").read_text(encoding="utf-8"))
    # Served at the root of its own Jalonel subdomain since 2026-10-16.
    site.setdefault("base", "/")
    site["origin"] = site.get("origin", "https://visibilite-ia.jalonel.com")
    # Free PDFs: committed under telechargements/ and served by the site itself (no GitHub link on the site).
    site["release"] = site["base"] + "telechargements/"
    site.setdefault("contact", "contact@jalonel.com")
    return site


# Anonymous audience counter (mesure.js) and aggregate behaviour counters (cro.js): both vendored byte-identical from
# VREAD-corp/octave-checkout gas/web/jalonel/ (never edit the copies), sent to the France backend octave-pay-gas (`track`
# action, `site` = repo name, whitelisted there; mesure.js maps the visibilite-ia.jalonel.com host to that site id). The ?v= content hash makes crawlers' renderers drop an old copy.
TRACK_API = "https://script.google.com/macros/s/AKfycbzD1IRL8QALluKGZxgGiORFP6-DkC_qFJYR9aOxZiimxa06nbCqpzUI-9iLblp6V2VY/exec"
MESURE_V = hashlib.sha256((ROOT / "assets" / "mesure.js").read_bytes()).hexdigest()[:8]
CRO_V = hashlib.sha256((ROOT / "assets" / "cro.js").read_bytes()).hexdigest()[:8]
# Links whose clicks mesure.js counts (data-mesure): free PDFs (telechargements/) and the paid-version page.
A_RE = re.compile(r'<a\b([^>]*)>')


def tag_links(page):
    def one(m):
        attrs = m.group(1)
        if "data-mesure" in attrs or 'aria-current="page"' in attrs:
            return m.group(0)
        href = re.search(r'href="([^"]*)"', attrs)
        href = href.group(1) if href else ""
        if href.startswith("/telechargements/") and href.endswith(".pdf"):
            return f'<a{attrs} data-mesure="free_download">'
        if re.search(r"version-payante\.html(#|$)", href):
            return f'<a{attrs} data-mesure="cta_click">'
        return m.group(0)
    return A_RE.sub(one, page)


def tracking_tags(site):
    slug = site["repo"].split("/")[1]
    return (f'<script src="{site["base"]}assets/mesure.js?v={MESURE_V}" defer></script>\n'
            f'<script src="{site["base"]}assets/cro.js?v={CRO_V}" data-site="{slug}" data-api="{TRACK_API}" '
            f'data-hosts="{site["origin"].split("//")[1]}" data-cta="[data-mesure]" defer></script>')


# Publisher: the Jalonel brand (hub https://jalonel.com/), operated by READ FRANCE SAS.
ORG_REF = {"@type": "Organization", "@id": "https://jalonel.com/#org", "name": "Jalonel", "url": "https://jalonel.com/",
           "parentOrganization": {"@type": "Organization", "name": "READ FRANCE SAS", "identifier": "SIREN 988741773"}}

# IndexNow key, served at the site root (https://visibilite-ia.jalonel.com/<key>.txt).
INDEXNOW_KEY = "5be19f56d46ca3d2553bee28ebfa8edd"

# Internal links point at directory URLs, never at their index.html twin.
INDEX_RE = re.compile(r'href="(/(?:[^"#]*/)?)index\.html(#[^"]*)?"')


def dir_url(path):
    return path[:-10] if path.endswith("index.html") else path


FM_RE = re.compile(r"\A\s*<!--(.*?)-->\s*", re.S)


def parse(path):
    raw = path.read_text(encoding="utf-8")
    m = FM_RE.match(raw)
    if not m:
        sys.exit(f"missing front matter: {path}")
    meta = {}
    for line in m.group(1).strip().splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    for key in ("title", "description"):
        if not meta.get(key):
            sys.exit(f"missing {key}: {path}")
    return meta, raw[m.end():]


def fill(text, site):
    for key in ("base", "release", "contact"):
        text = text.replace("{{" + key + "}}", site[key])
    return text


def nav_html(site, lang, current):
    items = site["nav"].get(lang) or site["nav"][site["lang"]]
    out = []
    for label, href in items:
        url = site["base"] + href
        cur = ' aria-current="page"' if href == current else ""
        out.append(f'<li><a href="{url}"{cur}>{html.escape(label)}</a></li>')
    return "\n".join(out)


def layout(site, meta, body, rel):
    lang = meta.get("lang", site["lang"])
    t = site["i18n"][lang]
    page_url = site["origin"] + site["base"] + (rel[:-10] if rel.endswith("index.html") else rel)
    title = meta["title"]
    full_title = title if meta.get("bare_title") == "yes" else f"{title} · {site['brand']}"
    alt = ""
    if meta.get("alternate"):
        alt_lang, alt_path = meta["alternate"].split(" ", 1)
        alt_url = site["origin"] + site["base"] + dir_url(alt_path)
        default_url = page_url if lang == site["lang"] else alt_url
        alt = (f'<link rel="alternate" hreflang="{lang}" href="{page_url}">\n'
               f'<link rel="alternate" hreflang="{alt_lang}" href="{alt_url}">\n'
               f'<link rel="alternate" hreflang="x-default" href="{default_url}">')
    jsonld = {
        "@context": "https://schema.org",
        "@type": meta.get("type", "WebPage"),
        "name": title,
        "headline": title,
        "description": meta["description"],
        "url": page_url,
        "inLanguage": lang,
        "isAccessibleForFree": True,
        "publisher": ORG_REF,
    }
    if meta.get("updated"):
        jsonld["dateModified"] = meta["updated"]
    robots = '\n<meta name="robots" content="noindex, follow">' if meta.get("noindex") == "yes" else ""
    lang_switch = ""
    if meta.get("alternate"):
        alt_lang, alt_path = meta["alternate"].split(" ", 1)
        lang_switch = (f'<a class="lang" href="{site["base"]}{alt_path}" hreflang="{alt_lang}" '
                       f'lang="{alt_lang}">{site["i18n"][alt_lang]["switch"]}</a>')
    footer_links = " · ".join(
        f'<a href="{href if href.startswith(("http", "mailto:", "{{")) else site["base"] + href}">{html.escape(label)}</a>'
        for label, href in t["footer_links"])
    banner = ""
    if site.get("banner", {}).get(lang):
        banner = f'<div class="banner" role="note">{site["banner"][lang]}</div>'
    return f"""<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(full_title)}</title>
<meta name="description" content="{html.escape(meta['description'])}">
<link rel="canonical" href="{page_url}">{robots}
{alt}
<meta property="og:type" content="website">
<meta property="og:site_name" content="{html.escape(site['brand'])}">
<meta property="og:title" content="{html.escape(title)}">
<meta property="og:description" content="{html.escape(meta['description'])}">
<meta property="og:url" content="{page_url}">
<meta property="og:locale" content="{t['locale']}">
<meta property="og:image" content="{site['origin']}{site['base']}assets/og.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="{site['accent']}">
<link rel="icon" href="{site['base']}assets/icon.svg" type="image/svg+xml">
<link rel="stylesheet" href="{site['base']}assets/style.css">
<script type="application/ld+json">{json.dumps(jsonld, ensure_ascii=False)}</script>
</head>
<body>
<a class="skip" href="#main">{t['skip']}</a>
<header class="site-header">
<div class="wrap header-inner">
<a class="brand" href="{site['base']}{t['home']}">{site['logo_text']}</a>
<nav aria-label="{t['nav_label']}"><ul>
{nav_html(site, lang, rel)}
</ul></nav>
{lang_switch}
</div>
</header>
{banner}
<main id="main" class="wrap">
{body}
</main>
<footer class="site-footer">
<div class="wrap">
<p>{t['footer_product']}</p>
<p>{footer_links}</p>
<p>{t['footer_tracking']}</p>
</div>
</footer>
{tracking_tags(site)}
</body>
</html>
"""


def main():
    site = load_site()
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    shutil.copytree(ROOT / "assets", OUT / "assets")
    shutil.copytree(ROOT / "telechargements", OUT / "telechargements")
    pages = []
    for src in sorted((ROOT / "content").rglob("*.html")):
        rel = src.relative_to(ROOT / "content").as_posix()
        meta, body = parse(src)
        page = layout(site, meta, fill(body, site), rel)
        dest = OUT / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(tag_links(INDEX_RE.sub(r'href="\1\2"', fill(page, site))), encoding="utf-8")
        if meta.get("noindex") != "yes":
            loc = site["origin"] + site["base"] + (rel[:-10] if rel.endswith("index.html") else rel)
            pages.append((loc, meta.get("updated", site["updated"])))
    sm = ['<?xml version="1.0" encoding="UTF-8"?>',
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for loc, mod in pages:
        sm.append(f"<url><loc>{loc}</loc><lastmod>{mod}</lastmod></url>")
    sm.append("</urlset>")
    (OUT / "sitemap.xml").write_text("\n".join(sm) + "\n", encoding="utf-8")
    (OUT / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\n\nSitemap: {site['origin']}{site['base']}sitemap.xml\n",
        encoding="utf-8")
    (OUT / ".nojekyll").write_text("", encoding="utf-8")
    (OUT / "CNAME").write_text(site["origin"].split("//")[1] + "\n", encoding="utf-8")
    (OUT / f"{INDEXNOW_KEY}.txt").write_text(INDEXNOW_KEY, encoding="utf-8")
    print(f"built {len(pages)} pages into {OUT}")


if __name__ == "__main__":
    main()
