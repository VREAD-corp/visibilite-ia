#!/usr/bin/env python3
"""Static checks on _site/ (stdlib only). Exit 1 on any failure.

- every page: lang, one <title>, meta description, canonical, exactly one <h1>
- titles and descriptions unique across indexable pages
- every internal link / asset resolves to a built file (and #anchors exist)
- images have alt text; no third-party scripts, iframes or http:// links
- every page loads mesure.js then cro.js (site = repo name, France backend), vendored byte-identical
- sitemap.xml lists every indexable page; robots.txt points to it
"""
import json
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse, unquote

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "_site"
SITE = json.loads((ROOT / "site.json").read_text(encoding="utf-8"))
BASE = SITE.get("base", "/")
ORIGIN = SITE.get("origin", "https://visibilite-ia.jalonel.com")
HOST = ORIGIN.split("//")[1]
INDEXNOW_KEY = "5be19f56d46ca3d2553bee28ebfa8edd"
SLUG = SITE["repo"].split("/")[1]
TRACK_API = "https://script.google.com/macros/s/AKfycbzD1IRL8QALluKGZxgGiORFP6-DkC_qFJYR9aOxZiimxa06nbCqpzUI-9iLblp6V2VY/exec"


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.lang = None
        self.titles = []
        self.desc = None
        self.canonical = None
        self.h1 = 0
        self.links = []
        self.ids = set()
        self.imgs_no_alt = 0
        self.ext_scripts = []
        self.scripts = []
        self.iframes = 0
        self.noindex = False
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids.add(a["id"])
        if tag == "html":
            self.lang = a.get("lang")
        elif tag == "title":
            self._in_title = True
            self.titles.append("")
        elif tag == "meta" and a.get("name") == "description":
            self.desc = a.get("content")
        elif tag == "meta" and a.get("name") == "robots" and "noindex" in (a.get("content") or ""):
            self.noindex = True
        elif tag == "link" and a.get("rel") == "canonical":
            self.canonical = a.get("href")
        elif tag == "h1":
            self.h1 += 1
        elif tag == "img" and not a.get("alt") and a.get("alt") != "":
            self.imgs_no_alt += 1
        elif tag == "script" and a.get("src"):
            self.scripts.append(a)
            if urlparse(a["src"]).netloc:
                self.ext_scripts.append(a["src"])
        elif tag == "iframe":
            self.iframes += 1
        if tag == "a" and a.get("href"):
            self.links.append(a["href"])
        elif tag == "link" and a.get("rel") in ("stylesheet", "icon") and a.get("href"):
            self.links.append(a["href"])
        elif tag in ("img", "script", "source") and a.get("src"):
            self.links.append(a["src"])

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.titles[-1] += data


def resolve(link, page_rel):
    """Return (file Path, fragment) for an internal link, or None if external."""
    u = urlparse(link)
    if u.scheme in ("mailto", "tel"):
        return None
    if u.scheme and u.netloc:
        if link.startswith(ORIGIN + BASE):
            path = u.path
        else:
            return None
    else:
        path = u.path
    if not path:
        return (OUT / page_rel, u.fragment)
    if not path.startswith("/"):
        path = str(Path("/" + page_rel).parent / path)
    if not path.startswith(BASE):
        return ("BAD", path)
    rel = unquote(path[len(BASE):])
    target = OUT / rel
    if rel == "" or rel.endswith("/"):
        target = target / "index.html"
    return (target, u.fragment)


def main():
    errors = []
    pages = {}
    for f in sorted(OUT.rglob("*.html")):
        p = Page()
        p.feed(f.read_text(encoding="utf-8"))
        pages[f.relative_to(OUT).as_posix()] = p
    titles, descs = {}, {}
    for rel, p in pages.items():
        where = rel
        if not p.lang:
            errors.append(f"{where}: missing lang")
        if len(p.titles) != 1 or not p.titles[0].strip():
            errors.append(f"{where}: needs exactly one non-empty <title>")
        if not p.desc or len(p.desc) < 50:
            errors.append(f"{where}: meta description missing or < 50 chars")
        if p.desc and len(p.desc) > 170:
            errors.append(f"{where}: meta description > 170 chars ({len(p.desc)})")
        if not p.canonical:
            errors.append(f"{where}: missing canonical")
        if p.h1 != 1:
            errors.append(f"{where}: {p.h1} <h1> (want 1)")
        if p.imgs_no_alt:
            errors.append(f"{where}: {p.imgs_no_alt} <img> without alt")
        if p.iframes:
            errors.append(f"{where}: iframe found")
        for s in p.ext_scripts:
            errors.append(f"{where}: external script {s}")
        srcs = [urlparse(s["src"]).path for s in p.scripts]
        if srcs != [BASE + "assets/mesure.js", BASE + "assets/cro.js"]:
            errors.append(f"{where}: want mesure.js then cro.js, got {srcs}")
        else:
            cro = p.scripts[1]
            if (cro.get("data-site"), cro.get("data-api"), cro.get("data-hosts")) != (SLUG, TRACK_API, HOST):
                errors.append(f"{where}: cro.js data-site/data-api/data-hosts")
            if not all("defer" in s for s in p.scripts) or any(s.get("type") == "module" for s in p.scripts):
                errors.append(f"{where}: snippets must be classic deferred scripts")
        if not p.noindex:
            titles.setdefault(p.titles[0] if p.titles else "", []).append(rel)
            descs.setdefault(p.desc, []).append(rel)
        for link in p.links:
            if link.startswith("http://"):
                errors.append(f"{where}: insecure link {link}")
                continue
            r = resolve(link, rel)
            if r is None:
                continue
            target, frag = r
            if target == "BAD":
                errors.append(f"{where}: link outside base {link}")
                continue
            if not target.exists():
                errors.append(f"{where}: broken internal link {link}")
                continue
            if frag and target.suffix == ".html":
                tp = pages.get(target.relative_to(OUT).as_posix())
                if tp and frag not in tp.ids:
                    errors.append(f"{where}: missing anchor #{frag} in {link}")
    for t, rels in titles.items():
        if len(rels) > 1:
            errors.append(f"duplicate title '{t}': {rels}")
    for d, rels in descs.items():
        if len(rels) > 1:
            errors.append(f"duplicate description: {rels}")
    sitemap = (OUT / "sitemap.xml").read_text(encoding="utf-8")
    for rel, p in pages.items():
        if p.noindex:
            continue
        loc = ORIGIN + BASE + (rel[:-10] if rel.endswith("index.html") else rel)
        if f"<loc>{loc}</loc>" not in sitemap:
            errors.append(f"sitemap missing {loc}")
    if "Sitemap: " + ORIGIN + BASE + "sitemap.xml" not in (OUT / "robots.txt").read_text():
        errors.append("robots.txt has no sitemap line")
    if (OUT / "CNAME").read_text().strip() != HOST:
        errors.append("CNAME does not hold " + HOST)
    if (OUT / (INDEXNOW_KEY + ".txt")).read_text() != INDEXNOW_KEY:
        errors.append("IndexNow key file missing at the site root")
    # Jalonel brand only: no Vread mention, GitHub repository / issues / releases link or « code source » in anything served.
    for f in sorted(OUT.rglob("*")):
        if f.is_file() and f.suffix in (".html", ".js", ".css", ".json", ".xml", ".txt", ".svg"):
            text = f.read_text(encoding="utf-8").lower()
            for bad in ("vread", "octave@", "/issues", "code source", "/releases/"):
                if bad in text:
                    errors.append(f"{f.relative_to(OUT)}: mentions {bad}")
    # Free PDFs served by the site itself, linked with the free_download counter.
    for name in ("checklist-geo-pme.pdf", "kit-auto-test-visibilite-ia.pdf"):
        pdf = OUT / "telechargements" / name
        if not pdf.exists() or not pdf.read_bytes().startswith(b"%PDF-"):
            errors.append(f"telechargements/{name} missing or not a PDF")
        if f'href="{BASE}telechargements/{name}" data-mesure="free_download"' not in (OUT / "index.html").read_text(encoding="utf-8"):
            errors.append(f"index.html: no tracked link to telechargements/{name}")
    if 'href="mailto:contact@jalonel.com"' not in (OUT / "index.html").read_text(encoding="utf-8"):
        errors.append("index.html: footer has no mailto:contact@jalonel.com")
    for name in ("mesure.js", "cro.js"):
        js = (ROOT / "assets" / name).read_text(encoding="utf-8")
        if name == "mesure.js" and (TRACK_API not in js or "octave_notrack" not in js or "v:2" not in js):
            errors.append("assets/mesure.js is not the octave-checkout snippet (v:2, octave_notrack)")
    for e in errors:
        print("FAIL", e)
    print(f"{len(pages)} pages checked, {len(errors)} errors")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
