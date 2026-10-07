// CityPulse showcase site — GitHub Pages for this repository. Built from small, committed exports of
// the prod marts (`make site-data`); a build needs no cloud access. One long page, New York at night:
// the layout and every illustration live in src/index.md and src/style.css.
export default {
  title: "CityPulse",
  root: "src",
  base: "/CityPulse_Analytics/",
  style: "style.css",
  globalStylesheets: [], // no third-party font requests: system fonts only
  head: '<meta name="theme-color" content="#0b1019"><link rel="icon" href="data:image/svg+xml,%3Csvg xmlns=\'http://www.w3.org/2000/svg\' viewBox=\'0 0 32 32\'%3E%3Crect width=\'32\' height=\'32\' rx=\'7\' fill=\'%230b1019\'/%3E%3Cg fill=\'none\' stroke=\'%23f5c518\' stroke-width=\'2.4\'%3E%3Ccircle cx=\'9\' cy=\'20\' r=\'5\'/%3E%3Ccircle cx=\'23\' cy=\'20\' r=\'5\'/%3E%3Cpath d=\'M9 20l5-8h7l2 8M14 12l-1.5-3H11\'/%3E%3C/g%3E%3C/svg%3E">',
  pages: [],
  sidebar: false,
  pager: false,
  toc: false,
  header: "",
  footer: ""
};
