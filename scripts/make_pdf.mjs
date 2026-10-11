// Renders pdf/*.html to dist/*.pdf and assets/og.html to assets/og.png
// with headless Chromium (Playwright). Usage: node scripts/make_pdf.mjs
// Optional env CHROME_PATH to use an already-installed Chromium binary.
import { chromium } from "playwright";
import { readdirSync, mkdirSync, existsSync } from "node:fs";
import { resolve, basename } from "node:path";
import { pathToFileURL } from "node:url";

const root = resolve(import.meta.dirname, "..");
const launch = process.env.CHROME_PATH ? { executablePath: process.env.CHROME_PATH } : {};
const browser = await chromium.launch(launch);
const page = await browser.newPage();
mkdirSync(resolve(root, "dist"), { recursive: true });

for (const f of readdirSync(resolve(root, "pdf")).filter((n) => n.endsWith(".html"))) {
  await page.goto(pathToFileURL(resolve(root, "pdf", f)).href, { waitUntil: "load" });
  const out = resolve(root, "dist", basename(f, ".html") + ".pdf");
  await page.pdf({
    path: out,
    format: "A4",
    printBackground: true,
    margin: { top: "16mm", bottom: "18mm", left: "15mm", right: "15mm" },
    displayHeaderFooter: true,
    headerTemplate: "<span></span>",
    footerTemplate:
      '<div style="font-size:8px;width:100%;text-align:center;color:#555">' +
      '<span class="title"></span> · <span class="pageNumber"></span>/<span class="totalPages"></span></div>',
  });
  console.log("pdf", out);
}

const og = resolve(root, "scripts", "og.html");
if (existsSync(og)) {
  await page.setViewportSize({ width: 1200, height: 630 });
  await page.goto(pathToFileURL(og).href);
  await page.screenshot({ path: resolve(root, "assets", "og.png") });
  console.log("og", resolve(root, "assets", "og.png"));
}
await browser.close();
