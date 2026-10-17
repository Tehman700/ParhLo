import type { Edition } from "@/lib/api";
import { buildPrintHtml } from "@/lib/printHtml";

export const runtime = "nodejs";
export const maxDuration = 60;

const CHROMIUM_PACK = "https://github.com/Sparticuz/chromium/releases/download/v153.0.0/chromium-v153.0.0-pack.x64.tar";

/** GET /pdf/2026-10-17 → the edition as a print-ready A4 PDF (headless Chromium).
 *  Auth is forwarded from the caller (session cookie or X-Demo-User) to the backend. */
export async function GET(req: Request, ctx: RouteContext<"/pdf/[date]">) {
  const { date } = await ctx.params;
  const origin = new URL(req.url).origin;
  const backend = process.env.NEXT_PUBLIC_API_URL || origin;
  const fwd: Record<string, string> = {};
  for (const h of ["cookie", "authorization", "x-demo-user"]) {
    const v = req.headers.get(h);
    if (v) fwd[h] = v;
  }

  const res = await fetch(`${backend}/api/editions/${encodeURIComponent(date)}`, { headers: fwd, cache: "no-store" });
  if (!res.ok) return new Response(await res.text(), { status: res.status });
  const edition = (await res.json()) as Edition;

  const browser = await launchBrowser();
  try {
    const page = await browser.newPage();
    await page.setContent(buildPrintHtml(edition), { waitUntil: "load", timeout: 30_000 });
    await page.evaluate(() => document.fonts.ready); // newspaper fonts must be in before printing
    const pdf = await page.pdf({ format: "A4", printBackground: true, preferCSSPageSize: true });
    return new Response(Buffer.from(pdf), {
      headers: {
        "Content-Type": "application/pdf",
        "Content-Disposition": `attachment; filename="ParhLo-${date}.pdf"`,
        "Cache-Control": "private, max-age=300",
      },
    });
  } finally {
    await browser.close();
  }
}

async function launchBrowser() {
  const puppeteer = await import("puppeteer-core");
  if (process.env.VERCEL) {
    // chromium-min downloads the browser pack into /tmp on cold start (nothing to bundle or trace).
    const chromium = (await import("@sparticuz/chromium-min")).default;
    return puppeteer.launch({ args: chromium.args, executablePath: await chromium.executablePath(CHROMIUM_PACK), headless: true });
  }
  const local = process.env.CHROME_PATH
    ?? (process.platform === "win32" ? "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
      : process.platform === "darwin" ? "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" : "/usr/bin/google-chrome");
  return puppeteer.launch({ executablePath: local, headless: true });
}
