// Helpers for the BI page.
import * as d3 from "npm:d3";
import {html} from "npm:htl";

/** "2025-07" → "Jul 2025" (or "J" when short). */
export function monthLabel(m, short = false) {
  const date = new Date(`${m}-01T00:00:00Z`);
  return short ? d3.utcFormat("%b")(date).slice(0, 1) : d3.utcFormat("%b %Y")(date);
}

/** "2025-07" shifted by n months → "2025-05" for n = −2. */
export function shiftMonth(m, n) {
  const date = d3.utcMonth.offset(new Date(`${m}-01T00:00:00Z`), n);
  return d3.utcFormat("%Y-%m")(date);
}

/** A button that saves `rows` (an array of objects) as a CSV file. */
export function downloadButton(rows, filename) {
  const button = html`<button class="btn ghost small" type="button">Download CSV</button>`;
  button.onclick = () => {
    const url = URL.createObjectURL(new Blob([d3.csvFormat(rows)], {type: "text/csv"}));
    const a = Object.assign(document.createElement("a"), {href: url, download: filename});
    a.click();
    URL.revokeObjectURL(url);
  };
  return button;
}
