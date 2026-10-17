/** News feeds often give tiny thumbnails (Guardian 140 px, BBC 240 px) that blur when shown large.
 *  Rewrite them to the same picture at a usable size on the outlet's own image server. */
export function sharpImage(url: string | null | undefined, width: 1000 | 2000 = 1000): string | null {
  if (!url) return null;
  // Guardian: i.guim.co.uk URLs are signed per size, but media.guim.co.uk serves standard widths of the same crop.
  const g = url.match(/^https:\/\/i\.guim\.co\.uk\/img\/media\/([0-9a-f]+)\/([0-9_]+)\/master\/\d+\.\w+/);
  if (g) return `https://media.guim.co.uk/${g[1]}/${g[2]}/${width}.jpg`;
  // BBC: ichef.bbci.co.uk/{ace|news}/{standard|ws}/<width>/… → 976 px (their largest standard size).
  const b = url.match(/^(https:\/\/ichef\.bbci\.co\.uk\/(?:ace|news)\/(?:standard|ws)\/)\d+(\/.*)$/);
  if (b) return `${b[1]}976${b[2]}`;
  return url;
}
