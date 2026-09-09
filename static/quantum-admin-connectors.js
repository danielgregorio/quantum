/**
 * Quantum Admin - Connectors Page
 * Dynamic Provider <-> Type filtering
 */
(function () {
  'use strict';

  var typeProviders = {
    database: ['postgres', 'mysql', 'mariadb', 'mongodb', 'sqlite', 'influxdb'],
    mq:       ['rabbitmq', 'redis_queue', 'kafka'],
    cache:    ['redis', 'memcached'],
    storage:  ['s3', 'minio', 'local'],
    ai:       ['ollama', 'lmstudio', 'anthropic', 'openai', 'openrouter']
  };

  // Build reverse map: provider -> type
  var providerType = {};
  Object.keys(typeProviders).forEach(function (type) {
    typeProviders[type].forEach(function (prov) {
      providerType[prov] = type;
    });
  });

  var typeSelect = document.querySelector('select[name="conn_type"]');
  var providerSelect = document.querySelector('select[name="provider"]');

  if (!typeSelect || !providerSelect) return;

  // Store original options with their optgroup labels
  var allOptions = [];
  var optgroups = providerSelect.querySelectorAll('optgroup');
  optgroups.forEach(function (og) {
    var label = og.getAttribute('label') || '';
    var opts = og.querySelectorAll('option');
    opts.forEach(function (opt) {
      allOptions.push({ value: opt.value, text: opt.textContent, group: label });
    });
  });

  var syncing = false;

  function rebuildProviderOptions(allowedType) {
    // Remove everything except the placeholder
    while (providerSelect.options.length > 1) {
      providerSelect.remove(1);
    }
    // Remove old optgroups
    var oldGroups = providerSelect.querySelectorAll('optgroup');
    oldGroups.forEach(function (g) { g.remove(); });

    if (!allowedType) {
      // Show all grouped
      var groups = {};
      allOptions.forEach(function (o) {
        if (!groups[o.group]) groups[o.group] = [];
        groups[o.group].push(o);
      });
      Object.keys(groups).forEach(function (gName) {
        var og = document.createElement('optgroup');
        og.label = gName;
        groups[gName].forEach(function (o) {
          var opt = document.createElement('option');
          opt.value = o.value;
          opt.textContent = o.text;
          og.appendChild(opt);
        });
        providerSelect.appendChild(og);
      });
    } else {
      // Show only providers for this type, flat (no optgroup)
      var allowed = typeProviders[allowedType] || [];
      allOptions.forEach(function (o) {
        if (allowed.indexOf(o.value) !== -1) {
          var opt = document.createElement('option');
          opt.value = o.value;
          opt.textContent = o.text;
          providerSelect.appendChild(opt);
        }
      });
    }
  }

  typeSelect.addEventListener('change', function () {
    if (syncing) return;
    syncing = true;
    var selectedType = typeSelect.value;
    var currentProvider = providerSelect.value;
    rebuildProviderOptions(selectedType);

    // Try to keep current provider if it belongs to the new type
    if (currentProvider) {
      var allowed = typeProviders[selectedType] || [];
      if (allowed.indexOf(currentProvider) !== -1) {
        providerSelect.value = currentProvider;
      } else {
        providerSelect.value = '';
      }
    }
    syncing = false;
  });

  providerSelect.addEventListener('change', function () {
    if (syncing) return;
    syncing = true;
    var prov = providerSelect.value;
    if (prov && providerType[prov]) {
      typeSelect.value = providerType[prov];
      // Also filter providers to match the auto-selected type
      rebuildProviderOptions(providerType[prov]);
      providerSelect.value = prov;
    }
    syncing = false;
  });

  // On load: if type is pre-selected (edit mode), filter providers
  if (typeSelect.value) {
    var editProvider = providerSelect.value;
    rebuildProviderOptions(typeSelect.value);
    if (editProvider) {
      providerSelect.value = editProvider;
    }
  }
})();
