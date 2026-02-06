<?xml version="1.0" encoding="UTF-8"?>
<!--
    Quantum UI Animation System Demo

    This example demonstrates all the animation features available in the
    Quantum UI Engine's animation system.
-->
<q:application id="AnimationsDemo" type="ui">
    <ui:window title="Animation System Demo">

        <!-- Header with fade-in animation -->
        <ui:animate type="fade" duration="500">
            <ui:header title="Quantum Animation System" />
        </ui:animate>

        <ui:vbox padding="24" gap="24">

            <!-- Section 1: Basic Animations -->
            <ui:panel title="Basic Animation Types">
                <ui:grid columns="3" gap="16">

                    <!-- Fade Animation -->
                    <ui:animate type="fade" duration="300">
                        <ui:panel background="#f0f9ff" padding="16">
                            <ui:text weight="bold">Fade</ui:text>
                            <ui:text>Fades in on load</ui:text>
                        </ui:panel>
                    </ui:animate>

                    <!-- Slide Animation -->
                    <ui:animate type="slide-left" duration="400" delay="100">
                        <ui:panel background="#f0fdf4" padding="16">
                            <ui:text weight="bold">Slide Left</ui:text>
                            <ui:text>Slides in from left</ui:text>
                        </ui:panel>
                    </ui:animate>

                    <!-- Scale Animation -->
                    <ui:animate type="scale" duration="300" delay="200">
                        <ui:panel background="#fef3c7" padding="16">
                            <ui:text weight="bold">Scale</ui:text>
                            <ui:text>Scales in on load</ui:text>
                        </ui:panel>
                    </ui:animate>

                    <!-- Rotate Animation -->
                    <ui:animate type="rotate-in" duration="500" delay="300">
                        <ui:panel background="#fee2e2" padding="16">
                            <ui:text weight="bold">Rotate</ui:text>
                            <ui:text>Rotates into view</ui:text>
                        </ui:panel>
                    </ui:animate>

                    <!-- Bounce Animation -->
                    <ui:animate type="bounce" duration="600" delay="400">
                        <ui:panel background="#e0e7ff" padding="16">
                            <ui:text weight="bold">Bounce</ui:text>
                            <ui:text>Bounces in on load</ui:text>
                        </ui:panel>
                    </ui:animate>

                    <!-- Shake Animation -->
                    <ui:animate type="shake" duration="400" delay="500">
                        <ui:panel background="#fce7f3" padding="16">
                            <ui:text weight="bold">Shake</ui:text>
                            <ui:text>Shakes on load</ui:text>
                        </ui:panel>
                    </ui:animate>

                </ui:grid>
            </ui:panel>

            <!-- Section 2: Animation Triggers -->
            <ui:panel title="Animation Triggers">
                <ui:hbox gap="16">

                    <!-- On-Load (default) -->
                    <ui:animate type="fade" trigger="on-load">
                        <ui:panel background="#dbeafe" padding="16">
                            <ui:text weight="bold">On Load</ui:text>
                            <ui:text>Plays when page loads (default)</ui:text>
                        </ui:panel>
                    </ui:animate>

                    <!-- On-Hover -->
                    <ui:animate type="pulse" trigger="on-hover" repeat="infinite">
                        <ui:panel background="#dcfce7" padding="16">
                            <ui:text weight="bold">On Hover</ui:text>
                            <ui:text>Hover over me!</ui:text>
                        </ui:panel>
                    </ui:animate>

                    <!-- On-Click -->
                    <ui:animate type="shake" trigger="on-click" duration="400">
                        <ui:panel background="#fef9c3" padding="16">
                            <ui:text weight="bold">On Click</ui:text>
                            <ui:text>Click me to shake!</ui:text>
                        </ui:panel>
                    </ui:animate>

                    <!-- On-Visible -->
                    <ui:animate type="slide-up" trigger="on-visible" duration="500">
                        <ui:panel background="#fce7f3" padding="16">
                            <ui:text weight="bold">On Visible</ui:text>
                            <ui:text>Animates when scrolled into view</ui:text>
                        </ui:panel>
                    </ui:animate>

                </ui:hbox>
            </ui:panel>

            <!-- Section 3: Easing Functions -->
            <ui:panel title="Easing Functions">
                <ui:grid columns="3" gap="16">

                    <ui:animate type="slide-right" easing="linear" duration="500">
                        <ui:panel background="#f0f9ff" padding="16">
                            <ui:text weight="bold">Linear</ui:text>
                            <ui:text>Constant speed</ui:text>
                        </ui:panel>
                    </ui:animate>

                    <ui:animate type="slide-right" easing="ease-in" duration="500" delay="100">
                        <ui:panel background="#f0fdf4" padding="16">
                            <ui:text weight="bold">Ease In</ui:text>
                            <ui:text>Starts slow, ends fast</ui:text>
                        </ui:panel>
                    </ui:animate>

                    <ui:animate type="slide-right" easing="ease-out" duration="500" delay="200">
                        <ui:panel background="#fef3c7" padding="16">
                            <ui:text weight="bold">Ease Out</ui:text>
                            <ui:text>Starts fast, ends slow</ui:text>
                        </ui:panel>
                    </ui:animate>

                    <ui:animate type="slide-right" easing="ease-in-out" duration="500" delay="300">
                        <ui:panel background="#fee2e2" padding="16">
                            <ui:text weight="bold">Ease In-Out</ui:text>
                            <ui:text>Slow start and end</ui:text>
                        </ui:panel>
                    </ui:animate>

                    <ui:animate type="slide-right" easing="spring" duration="500" delay="400">
                        <ui:panel background="#e0e7ff" padding="16">
                            <ui:text weight="bold">Spring</ui:text>
                            <ui:text>Bouncy overshoot</ui:text>
                        </ui:panel>
                    </ui:animate>

                    <ui:animate type="slide-right" easing="bounce" duration="500" delay="500">
                        <ui:panel background="#fce7f3" padding="16">
                            <ui:text weight="bold">Bounce</ui:text>
                            <ui:text>Elastic bounce effect</ui:text>
                        </ui:panel>
                    </ui:animate>

                </ui:grid>
            </ui:panel>

            <!-- Section 4: Nested Animations -->
            <ui:panel title="Nested & Staggered Animations">
                <ui:animate type="fade" duration="300">
                    <ui:vbox gap="8">
                        <ui:animate type="slide-left" delay="100">
                            <ui:text size="lg">Item 1 - Slides in first</ui:text>
                        </ui:animate>
                        <ui:animate type="slide-left" delay="200">
                            <ui:text size="lg">Item 2 - Slides in second</ui:text>
                        </ui:animate>
                        <ui:animate type="slide-left" delay="300">
                            <ui:text size="lg">Item 3 - Slides in third</ui:text>
                        </ui:animate>
                        <ui:animate type="slide-left" delay="400">
                            <ui:text size="lg">Item 4 - Slides in fourth</ui:text>
                        </ui:animate>
                    </ui:vbox>
                </ui:animate>
            </ui:panel>

            <!-- Section 5: Repeating Animations -->
            <ui:panel title="Repeating Animations">
                <ui:hbox gap="16" align="center">

                    <ui:animate type="pulse" repeat="infinite" duration="1000">
                        <ui:badge variant="primary">Pulse Forever</ui:badge>
                    </ui:animate>

                    <ui:animate type="bounce" repeat="3" duration="800">
                        <ui:badge variant="success">Bounce 3x</ui:badge>
                    </ui:animate>

                    <ui:animate type="shake" repeat="2" duration="400">
                        <ui:badge variant="warning">Shake 2x</ui:badge>
                    </ui:animate>

                    <ui:animate type="rotate" repeat="infinite" duration="2000" direction="normal">
                        <ui:loading />
                    </ui:animate>

                </ui:hbox>
            </ui:panel>

            <!-- Footer -->
            <ui:animate type="fade-in" trigger="on-visible" delay="200">
                <ui:footer>Quantum UI Animation System - Declarative animations for web applications</ui:footer>
            </ui:animate>

        </ui:vbox>

    </ui:window>
</q:application>
