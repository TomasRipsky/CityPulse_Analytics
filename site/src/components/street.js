// The hero's New York: a night skyline with lit windows, and rain or snow. Seeded, so the city looks
// the same on every visit.
function random(seed) {
  let s = seed;
  return () => (s = (s * 16807) % 2147483647) / 2147483647;
}

/** Falling particles (rain drops or snowflakes): `n` <i> elements in a box of class `cls`. */
export function particles(n, cls, seed, [fast, slow]) {
  const r = random(seed);
  const box = document.createElement("div");
  box.className = cls;
  box.setAttribute("aria-hidden", "true");
  for (let i = 0; i < n; ++i) {
    const p = document.createElement("i");
    p.style.left = `${r() * 110}%`;
    p.style.animationDuration = `${fast + r() * (slow - fast)}s`;
    p.style.animationDelay = `${-r() * slow}s`;
    box.append(p);
  }
  return box;
}

/** Manhattan at night: generic blocks, then the Empire State, the Chrysler and One World Trade. */
export function skyline() {
  const W = 1440, H = 240, r = random(42), parts = [];
  const block = (x, w, h) => {
    parts.push(`<rect x="${x}" y="${H - h}" width="${w}" height="${h}" fill="currentColor"/>`);
    for (let wy = H - h + 10; wy < H - 8; wy += 14)
      for (let wx = x + 6; wx < x + w - 6; wx += 10)
        parts.push(`<rect class="win${r() < 0.72 ? " off" : ""}" x="${wx}" y="${wy}" width="4" height="6"/>`);
  };
  for (let x = 0; x < W; ) {
    const w = 34 + r() * 60;
    block(x, w, 40 + r() * (r() < 0.2 ? 140 : 90));
    x += w + 3;
  }
  // Empire State: setbacks and a mast
  block(400, 76, 120); block(412, 52, 150); block(424, 28, 178);
  parts.push(`<rect x="433" y="${H - 196}" width="10" height="18" fill="currentColor"/><rect class="spire" x="437" y="${H - 236}" width="2" height="40"/>`);
  // Chrysler: a crown of arches and a needle
  block(760, 52, 150);
  parts.push(`<path d="M766 ${H - 150}L786 ${H - 196}L806 ${H - 150}Z" fill="currentColor"/><path class="spire" d="M771 ${H - 156}l15-28 15 28M776 ${H - 156}l10-18 10 18" fill="none" stroke="#c9d3e1" stroke-width="1.5"/><rect class="spire" x="785" y="${H - 228}" width="2" height="34"/>`);
  // One World Trade Center: a tapered tower and its antenna
  parts.push(`<path d="M1110 ${H}L1166 ${H}L1152 ${H - 205}L1124 ${H - 205}Z" fill="currentColor"/><rect class="spire" x="1137" y="${H - 240}" width="2" height="35"/>`);
  for (let wy = H - 195; wy < H - 8; wy += 14) parts.push(`<rect class="win${r() < 0.6 ? " off" : ""}" x="${1128 + r() * 16}" y="${wy}" width="4" height="6"/>`);
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("class", "skyline");
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
  svg.setAttribute("preserveAspectRatio", "xMidYMax slice");
  svg.setAttribute("aria-hidden", "true");
  svg.innerHTML = parts.join("");
  return svg;
}
