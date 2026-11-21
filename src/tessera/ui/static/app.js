"use strict";
(function () {
  const POLL_MS = 2000;
  const token = new URLSearchParams(window.location.hash.slice(1)).get("token");
  const headers = token ? { Authorization: "Bearer " + token } : {};
  const layers = new Map();
  let map;
  let fitted = false;

  function level(score) {
    if (score >= 0.8) return "ok";
    if (score >= 0.5) return "warn";
    return "bad";
  }

  const colors = { ok: "#3fb950", warn: "#d29922", bad: "#f85149" };

  function el(tag, cls, text) {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text !== undefined) node.textContent = String(text);
    return node;
  }

  function tooltip(props) {
    const box = el("div", "tip");
    box.appendChild(el("b", null, props.entity_id));
    box.appendChild(el("div", null, "source " + props.source_id));
    box.appendChild(el("div", null, "integrity " + props.integrity.toFixed(2)));
    if (props.integrity_reasons.length) box.appendChild(el("div", null, props.integrity_reasons.join(", ")));
    if (props.speed_mps !== undefined) box.appendChild(el("div", null, props.speed_mps.toFixed(1) + " m/s"));
    box.appendChild(el("div", null, new Date(props.observed_at).toISOString().slice(11, 19) + "Z"));
    return box;
  }

  function render(collection) {
    const seen = new Set();
    const list = document.getElementById("entity-list");
    list.replaceChildren();
    let flagged = 0;
    const bounds = [];
    for (const feature of collection.features) {
      const props = feature.properties;
      const key = props.source_id + "/" + props.entity_id;
      const [lon, lat] = feature.geometry.coordinates;
      const lvl = level(props.integrity);
      if (lvl === "bad") flagged += 1;
      seen.add(key);
      bounds.push([lat, lon]);
      const trail = props.trail.map(([x, y]) => [y, x]);
      let layer = layers.get(key);
      if (!layer) {
        layer = {
          line: L.polyline(trail, { weight: 2, opacity: 0.7 }).addTo(map),
          point: L.circleMarker([lat, lon], { radius: 7, weight: 2, fillOpacity: 0.9 }).addTo(map),
        };
        layers.set(key, layer);
      }
      layer.line.setLatLngs(trail);
      layer.line.setStyle({ color: colors[lvl] });
      layer.point.setLatLng([lat, lon]);
      layer.point.setStyle({ color: "#0e1116", fillColor: colors[lvl] });
      layer.point.unbindTooltip().bindTooltip(tooltip(props), { direction: "top" });

      const item = el("li");
      item.tabIndex = 0;
      item.appendChild(el("span", "dot " + lvl));
      item.appendChild(el("span", "name", props.entity_id));
      item.appendChild(el("span", "score", props.integrity.toFixed(2)));
      item.appendChild(el("span", "meta", props.source_id + " / " + props.fixes_in_window + " fixes, " + props.flagged_in_window + " flagged"));
      const focus = () => map.setView([lat, lon], Math.max(map.getZoom(), 15));
      item.addEventListener("click", focus);
      item.addEventListener("keydown", (e) => { if (e.key === "Enter") focus(); });
      list.appendChild(item);
    }
    for (const [key, layer] of layers) {
      if (!seen.has(key)) {
        map.removeLayer(layer.line);
        map.removeLayer(layer.point);
        layers.delete(key);
      }
    }
    if (!fitted && bounds.length) {
      map.fitBounds(bounds, { maxZoom: 16, padding: [40, 40] });
      fitted = true;
    }
    document.getElementById("empty-hint").hidden = collection.features.length > 0;
    document.getElementById("stat-entities").textContent = String(collection.features.length);
    document.getElementById("stat-flagged").textContent = String(flagged);
    document.getElementById("stat-updated").textContent = new Date().toISOString().slice(11, 19) + "Z";
  }

  function setLink(state, text) {
    const node = document.getElementById("link-state");
    node.className = "link " + state;
    node.textContent = text;
  }

  async function poll() {
    try {
      const response = await fetch("/v1/features", { headers, cache: "no-store" });
      if (response.status === 401) {
        setLink("down", "unauthorized: open with #token=...");
      } else if (!response.ok) {
        setLink("down", "error " + response.status);
      } else {
        render(await response.json());
        setLink("up", "live");
      }
    } catch (err) {
      setLink("down", "offline, retrying");
    }
    window.setTimeout(poll, POLL_MS);
  }

  async function start() {
    const [config, health] = await Promise.all([
      fetch("/v1/config", { cache: "no-store" }).then((r) => r.json()),
      fetch("/healthz", { cache: "no-store" }).then((r) => r.json()),
    ]);
    document.getElementById("mode").textContent = health.mode;
    map = L.map("map", { zoomControl: true }).setView([48.137, 11.575], 12);
    L.tileLayer(config.tile_url, { maxZoom: 19, attribution: config.tile_attribution }).addTo(map);
    poll();
  }

  start().catch(() => setLink("down", "failed to start"));
})();
