// CityPulse showcase site — GitHub Pages for this repository. Built from small, committed exports of
// the prod marts (`make site-data`); a build needs no cloud access.
export default {
  title: "CityPulse",
  root: "src",
  base: "/CityPulse_Analytics/",
  style: "style.css",
  globalStylesheets: [], // no third-party font requests: system fonts only
  pages: [
    {name: "What the weather does", path: "/weather"},
    {name: "When New York rides", path: "/rhythm"},
    {name: "How it is built", path: "/built"}
  ],
  footer:
    'CityPulse by Tomas Ripsky · <a href="https://github.com/TomasRipsky/CityPulse_Analytics">source</a> · weather data by <a href="https://open-meteo.com/">Open-Meteo.com</a> (CC BY 4.0) · trips from <a href="https://citibikenyc.com/system-data">Citi Bike System Data</a>; not affiliated with Citi Bike or Lyft'
};
