// Configure HTMX
        htmx.config.defaultSwapStyle = "innerHTML";
        htmx.config.defaultSwapDelay = 0;
        htmx.config.historyCacheSize = 10;

        // Log HTMX events in debug mode
        if (window.location.hostname === 'localhost') {
            htmx.logAll();
        }