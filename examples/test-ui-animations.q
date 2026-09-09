<?xml version="1.0" encoding="UTF-8"?>
<!--
    Quantum UI - Animation System Demo

    Demonstrates all available animations:
    - Fade (fade-in, fade-out)
    - Slide (slide-left, slide-right, slide-up, slide-down)
    - Scale (scale-in, scale-out)
    - Rotate (rotate, rotate-in)
    - Bounce
    - Pulse
    - Shake

    Triggers:
    - on-load: Play immediately when page loads
    - on-hover: Play when mouse hovers
    - on-click: Play on click
    - on-visible: Play when element becomes visible (scroll)
-->
<q:application id="AnimationDemo" type="ui" theme="dark">

    <ui:window title="Quantum Animation System">
        <ui:vbox padding="lg" gap="lg">

            <!-- Header with fade animation -->
            <ui:vbox animate="fade" anim-duration="500ms">
                <ui:text size="2xl" weight="bold">Animation System</ui:text>
                <ui:text color="muted">
                    Interactive demo of all available animations and triggers.
                </ui:text>
            </ui:vbox>

            <ui:rule />

            <!-- On-Load Animations -->
            <ui:panel title="On-Load Animations">
                <ui:text size="sm" color="muted">
                    These animations play automatically when the page loads.
                </ui:text>
                <ui:hbox gap="md" padding="md">
                    <ui:card animate="fade" anim-delay="0ms">
                        <ui:card-body>
                            <ui:text weight="bold">Fade In</ui:text>
                            <ui:text size="sm">animate="fade"</ui:text>
                        </ui:card-body>
                    </ui:card>

                    <ui:card animate="slide-left" anim-delay="100ms">
                        <ui:card-body>
                            <ui:text weight="bold">Slide Left</ui:text>
                            <ui:text size="sm">animate="slide-left"</ui:text>
                        </ui:card-body>
                    </ui:card>

                    <ui:card animate="slide-up" anim-delay="200ms">
                        <ui:card-body>
                            <ui:text weight="bold">Slide Up</ui:text>
                            <ui:text size="sm">animate="slide-up"</ui:text>
                        </ui:card-body>
                    </ui:card>

                    <ui:card animate="scale" anim-delay="300ms">
                        <ui:card-body>
                            <ui:text weight="bold">Scale In</ui:text>
                            <ui:text size="sm">animate="scale"</ui:text>
                        </ui:card-body>
                    </ui:card>

                    <ui:card animate="rotate-in" anim-delay="400ms">
                        <ui:card-body>
                            <ui:text weight="bold">Rotate In</ui:text>
                            <ui:text size="sm">animate="rotate-in"</ui:text>
                        </ui:card-body>
                    </ui:card>
                </ui:hbox>
            </ui:panel>

            <!-- On-Hover Animations -->
            <ui:panel title="On-Hover Animations">
                <ui:text size="sm" color="muted">
                    Hover over these elements to trigger the animation.
                </ui:text>
                <ui:hbox gap="md" padding="md">
                    <ui:button
                        variant="primary"
                        animate="pulse"
                        anim-trigger="on-hover"
                        anim-repeat="infinite">
                        Pulse (Hover Me)
                    </ui:button>

                    <ui:button
                        variant="secondary"
                        animate="bounce"
                        anim-trigger="on-hover">
                        Bounce (Hover Me)
                    </ui:button>

                    <ui:button
                        variant="success"
                        animate="shake"
                        anim-trigger="on-hover">
                        Shake (Hover Me)
                    </ui:button>

                    <ui:button
                        variant="danger"
                        animate="rotate"
                        anim-trigger="on-hover"
                        anim-duration="1s">
                        Rotate (Hover Me)
                    </ui:button>
                </ui:hbox>
            </ui:panel>

            <!-- On-Click Animations -->
            <ui:panel title="On-Click Animations">
                <ui:text size="sm" color="muted">
                    Click these elements to trigger the animation.
                </ui:text>
                <ui:hbox gap="md" padding="md">
                    <ui:card
                        animate="bounce"
                        anim-trigger="on-click"
                        anim-duration="600ms">
                        <ui:card-body>
                            <ui:text weight="bold">Click to Bounce</ui:text>
                        </ui:card-body>
                    </ui:card>

                    <ui:card
                        animate="shake"
                        anim-trigger="on-click"
                        anim-duration="400ms">
                        <ui:card-body>
                            <ui:text weight="bold">Click to Shake</ui:text>
                        </ui:card-body>
                    </ui:card>

                    <ui:card
                        animate="pulse"
                        anim-trigger="on-click"
                        anim-duration="300ms">
                        <ui:card-body>
                            <ui:text weight="bold">Click to Pulse</ui:text>
                        </ui:card-body>
                    </ui:card>
                </ui:hbox>
            </ui:panel>

            <!-- Easing Functions -->
            <ui:panel title="Easing Functions">
                <ui:text size="sm" color="muted">
                    Different easing curves affect how animations feel.
                </ui:text>
                <ui:hbox gap="md" padding="md">
                    <ui:card
                        animate="slide-up"
                        anim-easing="linear"
                        anim-trigger="on-click">
                        <ui:card-body>
                            <ui:text weight="bold">Linear</ui:text>
                            <ui:text size="sm" color="muted">Constant speed</ui:text>
                        </ui:card-body>
                    </ui:card>

                    <ui:card
                        animate="slide-up"
                        anim-easing="ease"
                        anim-trigger="on-click">
                        <ui:card-body>
                            <ui:text weight="bold">Ease</ui:text>
                            <ui:text size="sm" color="muted">Slow start/end</ui:text>
                        </ui:card-body>
                    </ui:card>

                    <ui:card
                        animate="slide-up"
                        anim-easing="spring"
                        anim-trigger="on-click">
                        <ui:card-body>
                            <ui:text weight="bold">Spring</ui:text>
                            <ui:text size="sm" color="muted">Overshoot effect</ui:text>
                        </ui:card-body>
                    </ui:card>

                    <ui:card
                        animate="slide-up"
                        anim-easing="bounce"
                        anim-trigger="on-click">
                        <ui:card-body>
                            <ui:text weight="bold">Bounce</ui:text>
                            <ui:text size="sm" color="muted">Bouncy overshoot</ui:text>
                        </ui:card-body>
                    </ui:card>
                </ui:hbox>
            </ui:panel>

            <!-- Duration Examples -->
            <ui:panel title="Duration Variations">
                <ui:text size="sm" color="muted">
                    Animation duration affects how fast or slow animations play.
                </ui:text>
                <ui:hbox gap="md" padding="md">
                    <ui:button
                        variant="primary"
                        animate="fade"
                        anim-duration="100ms"
                        anim-trigger="on-click">
                        100ms (Fast)
                    </ui:button>

                    <ui:button
                        variant="secondary"
                        animate="fade"
                        anim-duration="300ms"
                        anim-trigger="on-click">
                        300ms (Default)
                    </ui:button>

                    <ui:button
                        variant="success"
                        animate="fade"
                        anim-duration="600ms"
                        anim-trigger="on-click">
                        600ms (Slow)
                    </ui:button>

                    <ui:button
                        variant="warning"
                        animate="fade"
                        anim-duration="1000ms"
                        anim-trigger="on-click">
                        1000ms (Very Slow)
                    </ui:button>
                </ui:hbox>
            </ui:panel>

            <!-- Infinite Animations -->
            <ui:panel title="Infinite Animations">
                <ui:text size="sm" color="muted">
                    These animations loop continuously.
                </ui:text>
                <ui:hbox gap="lg" padding="md" justify="center">
                    <ui:loading animate="rotate" anim-repeat="infinite" anim-duration="1s" />

                    <ui:badge
                        variant="danger"
                        animate="pulse"
                        anim-repeat="infinite"
                        anim-duration="1.5s">
                        LIVE
                    </ui:badge>

                    <ui:badge
                        variant="success"
                        animate="bounce"
                        anim-repeat="infinite"
                        anim-duration="2s">
                        NEW!
                    </ui:badge>
                </ui:hbox>
            </ui:panel>

            <!-- Accessibility Note -->
            <ui:alert variant="info" title="Accessibility">
                Animations are automatically disabled when the user has enabled
                "prefers-reduced-motion" in their system settings.
            </ui:alert>

        </ui:vbox>
    </ui:window>

</q:application>
