// Live check: visits every URL of the live sitemap at 390px width,
// records console errors, horizontal overflow and the HTTP status of every link.
// Usage: node scripts/check_live.mjs https://visibilite-ia.jalonel.com/
import { chromium } from "playwright";

const base = process.argv[2];
if (!base) throw new Error("usage: check_live.mjs <base-url>");
const launch = process.env.CHROME_PATH ? { executablePath: process.env.CHROME_PATH } : {};
const browser = await chromium.launch(launch);
const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, userAgent: "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0 Safari/537.36 site-check" });
const sitemap = await (await fetch(base + "sitemap.xml")).text();
const urls = [...sitemap.matchAll(/<loc>([^<]+)<\/loc>/g)].map((m) => m[1]);
const links = new Map();
const report = { base, checkedAt: new Date().toISOString(), pages: [], badLinks: [] };

for (const url of urls) {
  const page = await ctx.newPage();
  const errors = [];
  page.on("console", (m) => m.type() === "error" && errors.push(m.text()));
  page.on("pageerror", (e) => errors.push(String(e)));
  const res = await page.goto(url, { waitUntil: "load" });
  const info = await page.evaluate(() => ({
    title: document.title,
    h1: document.querySelectorAll("h1").length,
    overflow: document.documentElement.scrollWidth > window.innerWidth,
    links: [...document.querySelectorAll("a[href]")].map((a) => a.href),
  }));
  for (const l of info.links) {
    const clean = l.split("#")[0];
    if (clean.startsWith("http")) links.set(clean, (links.get(clean) || new Set()).add(url));
  }
  report.pages.push({ url, status: res.status(), title: info.title, h1: info.h1, overflow: info.overflow, consoleErrors: errors });
  await page.close();
}

async function status(u) {
  // GitHub release asset URLs are checked without downloading (HEAD, no redirect follow)
  // so verification does not inflate the download-count KPI.
  const asset = /\/releases\/(latest\/)?download\//.test(u);
  const opts = { redirect: asset ? "manual" : "follow", headers: { "user-agent": "Mozilla/5.0 site-check" } };
  try {
    let r = await fetch(u, { ...opts, method: "HEAD" });
    if (!asset && (r.status === 405 || r.status === 403 || r.status === 404 || r.status >= 500)) r = await fetch(u, { ...opts, method: "GET" });
    return r.status;
  } catch (e) {
    return "ERR " + e.message;
  }
}
for (const [u, from] of links) {
  const s = await status(u);
  const ok = typeof s === "number" && (s < 400 || (s === 302 && /releases/.test(u)));
  if (!ok) report.badLinks.push({ url: u, status: s, from: [...from].slice(0, 3) });
}
report.linksChecked = links.size;
report.summary = {
  pages: report.pages.length,
  non200: report.pages.filter((p) => p.status !== 200).length,
  withConsoleErrors: report.pages.filter((p) => p.consoleErrors.length).length,
  withOverflow390: report.pages.filter((p) => p.overflow).length,
  badLinks: report.badLinks.length,
};
console.log(JSON.stringify(report, null, 2));
await browser.close();
