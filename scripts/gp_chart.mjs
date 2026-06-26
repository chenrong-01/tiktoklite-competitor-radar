#!/usr/bin/env node
/*
 * gp_chart.mjs — fetch a REAL Google Play Top-Free chart for one country x category.
 *
 * Replaces the old "scrape the category recommendation web page" approach, which
 * only returned an approximation and missed real hits (e.g. Setlog). This uses
 * the facundoolano/google-play-scraper `list` API (TOP_FREE collection) which
 * returns the actual ranked chart.
 *
 * Usage:
 *   node gp_chart.mjs --country th --category SOCIAL --num 30
 * Output (stdout): JSON array of {rank, appId, title, developer, url}
 */

import gplay from 'google-play-scraper';

const api = gplay.default || gplay;

function arg(name, fallback) {
  const idx = process.argv.indexOf(`--${name}`);
  return idx >= 0 && idx + 1 < process.argv.length ? process.argv[idx + 1] : fallback;
}

const country = (arg('country', 'us') || 'us').toLowerCase();
const category = (arg('category', 'SOCIAL') || 'SOCIAL').toUpperCase();
const num = parseInt(arg('num', '30'), 10);

async function main() {
  if (!api.category[category]) {
    process.stderr.write(`Unknown category: ${category}\n`);
    process.exit(2);
  }
  const rows = await api.list({
    category: api.category[category],
    collection: api.collection.TOP_FREE,
    country,
    num,
  });
  const out = rows.map((a, i) => ({
    rank: i + 1,
    appId: a.appId,
    title: a.title,
    developer: a.developer || '',
    url: a.url || `https://play.google.com/store/apps/details?id=${a.appId}`,
  }));
  process.stdout.write(JSON.stringify(out));
}

main().catch((e) => {
  process.stderr.write(`ERROR: ${e && e.message ? e.message : String(e)}\n`);
  process.exit(1);
});
