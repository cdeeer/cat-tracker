(function (global) {
  // Carto "Voyager" basemap — free, no API key, cleaner look than raw OSM tiles.
  // See https://github.com/CartoDB/basemap-styles for terms.
  const TILE_URL = 'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png';
  const TILE_ATTR = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>';
  const TILE_SUBDOMAINS = 'abcd';
  const DEFAULT_CENTER = [14.5995, 120.9842]; // Manila
  const DEFAULT_ZOOM = 11;

  function initMap(elementId, options) {
    options = options || {};
    const map = L.map(elementId).setView(options.center || DEFAULT_CENTER, options.zoom || DEFAULT_ZOOM);
    L.tileLayer(TILE_URL, {
      attribution: TILE_ATTR,
      subdomains: TILE_SUBDOMAINS,
      maxZoom: 19,
    }).addTo(map);
    return map;
  }

  function renderFeedingSites(map, sites) {
    const markers = [];
    sites.forEach(function (s) {
      const icon = L.divIcon({
        className: 'feeding-site-marker',
        html: '<div style="width:22px;height:22px;border-radius:50%;background:#FF8C61;border:3px solid #fff;box-shadow:0 0 0 1px #3B2E2A;"></div>',
        iconSize: [22, 22],
        iconAnchor: [11, 11],
      });
      const m = L.marker([s.lat, s.lng], { icon: icon }).addTo(map);
      let html = '<h4>' + escapeHtml(s.name) + '</h4>';
      html += '<div class="popup-meta">';
      html += '<div><strong>Foundation:</strong> <a href="' + s.foundation_url + '">' + escapeHtml(s.foundation) + '</a></div>';
      html += '<div><strong>Schedule:</strong> ' + escapeHtml(s.schedule) + '</div>';
      html += '<div><strong>Point person(s):</strong> ' + escapeHtml(s.point_person) + '</div>';
      if (s.contact_details) {
        html += '<div><strong>Contact:</strong> ' + escapeHtml(s.contact_details) + '</div>';
      }
      html += '</div>';
      if (s.cats && s.cats.length) {
        html += '<div style="font-weight:700; margin-top:0.4rem;">Cats here:</div>';
        html += '<ul class="popup-cats">';
        s.cats.forEach(function (c) {
          html += '<li style="display:flex; align-items:center; justify-content:space-between; gap:0.4rem;">';
          html += '<span><a href="' + c.url + '">' + escapeHtml(c.name) + '</a> <span class="text-muted" style="font-size:0.8rem;">· ' + escapeHtml(c.status) + '</span></span>';
          html += '<a class="btn btn-danger btn-sm" href="' + c.incident_url + '" style="font-size:0.75rem; padding:0.2rem 0.5rem; flex-shrink:0;">🚨</a>';
          html += '</li>';
        });
        html += '</ul>';
      } else {
        html += '<div class="text-muted" style="margin-top:0.4rem; font-size:0.9rem;">No cats currently associated.</div>';
      }
      m.bindPopup(html);
      markers.push(m);
    });
    return markers;
  }

  function renderReports(map, reports) {
    const markers = [];
    const bySlug = {};
    reports.forEach(function (r) {
      const icon = L.divIcon({
        className: 'cat-marker',
        html: '<div class="cat-marker-bubble" aria-label="Cat">🐱</div>',
        iconSize: [36, 36],
        iconAnchor: [18, 30],
        popupAnchor: [0, -28],
      });
      const m = L.marker([r.lat, r.lng], { icon: icon }).addTo(map);

      let html = '<div class="popup-cat">';
      if (r.photo_url) {
        html += '<img class="popup-cat-photo" src="' + r.photo_url + '" alt="' + escapeHtml(r.name) + '" data-cat-photo onerror="oggieCatPhotoFallback(this)">';
      } else {
        html += '<div class="popup-cat-photo cat-photo-emoji" aria-hidden="true" style="font-size:46px;"><span class="cat-glyph">😼</span></div>';
      }
      html += '<div class="popup-cat-body">';
      html += '<h4>🐱 ' + escapeHtml(r.name) + '</h4>';
      html += '<div class="popup-meta">';
      html += '<span class="badge badge-' + escapeHtml(r.status) + '">' + escapeHtml(r.status_display) + '</span>';
      if (r.is_verified) {
        html += ' <span class="badge badge-verified">✓ Verified</span>';
      }
      html += '</div>';
      html += '<div class="popup-meta">' + escapeHtml(r.foundation) + '</div>';
      html += '<div class="popup-meta"><strong>Age:</strong> ' + escapeHtml(r.age);
      if (r.gender) html += ' · ' + escapeHtml(r.gender);
      html += '</div>';
      if (r.address) {
        html += '<div class="popup-meta"><strong>Found near:</strong> ' + escapeHtml(r.address) + '</div>';
      }
      if (r.description) {
        html += '<p class="popup-desc">' + escapeHtml(r.description) + '</p>';
      }
      html += '<div style="display:flex; gap:0.4rem; flex-wrap:wrap; margin-top:0.5rem;">';
      html += '<a class="btn btn-primary btn-sm" href="' + r.url + '">View profile →</a>';
      html += '<a class="btn btn-danger btn-sm" href="' + r.incident_url + '">🚨 Report incident</a>';
      html += '</div>';
      html += '</div></div>';
      m.bindPopup(html, { maxWidth: 320, minWidth: 240 });

      if (r.slug) { bySlug[r.slug] = m; }
      markers.push(m);
    });
    markers.bySlug = bySlug;
    return markers;
  }

  function enablePicker(map, latInputId, lngInputId) {
    let marker = null;
    const latInput = document.getElementById(latInputId);
    const lngInput = document.getElementById(lngInputId);

    // If the hidden inputs already have values (edit mode), place the marker there.
    if (latInput.value && lngInput.value) {
      const initial = [parseFloat(latInput.value), parseFloat(lngInput.value)];
      marker = L.marker(initial, { draggable: true }).addTo(map);
      map.setView(initial, 15);
      marker.on('dragend', function (e) {
        const pos = e.target.getLatLng();
        latInput.value = pos.lat.toFixed(6);
        lngInput.value = pos.lng.toFixed(6);
      });
    }

    map.on('click', function (e) {
      if (marker) { map.removeLayer(marker); }
      marker = L.marker(e.latlng, { draggable: true }).addTo(map);
      latInput.value = e.latlng.lat.toFixed(6);
      lngInput.value = e.latlng.lng.toFixed(6);
      marker.on('dragend', function (ev) {
        const pos = ev.target.getLatLng();
        latInput.value = pos.lat.toFixed(6);
        lngInput.value = pos.lng.toFixed(6);
      });
    });
  }

  function escapeHtml(str) {
    if (str == null) return '';
    return String(str).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  global.OggieMap = {
    init: initMap,
    renderFeedingSites: renderFeedingSites,
    renderReports: renderReports,
    enablePicker: enablePicker,
  };
})(window);
