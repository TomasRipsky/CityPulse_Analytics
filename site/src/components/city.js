// Shared encodings and formats for every CityPulse page.
import * as d3 from "npm:d3";

export const colors = {all: "var(--theme-foreground)", member: "var(--series-1)", casual: "var(--series-2)"};
export const riders = ["all", "member", "casual"];
export const riderLabel = {all: "all riders", member: "members", casual: "casual riders"};

export const fmt = {
  count: d3.format(","),
  millions: (n) => `${d3.format(".1f")(n / 1e6)} M`,
  signedPct: (p) => `${p > 0 ? "+" : p < 0 ? "−" : ""}${d3.format(".0f")(Math.abs(p))}%`,
  date: d3.utcFormat("%-d %B %Y")
};

/** The effect of one band for one rider, from effects.csv. */
export function effect(effects, condition, band, rider = "all") {
  return effects.find((d) => d.condition === condition && d.band === band && d.rider === rider);
}
