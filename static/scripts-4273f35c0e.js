htmx.config.defaultSwapStyle = "innerHTML";
        htmx.config.defaultSwapDelay = 0;
        htmx.config.historyCacheSize = 10;
        if (window.location.hostname === 'localhost') {
            htmx.logAll();
        }