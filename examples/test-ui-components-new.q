<?xml version="1.0" encoding="UTF-8"?>
<!--
    Quantum UI - New Component Library Demo

    Demonstrates the new components:
    - ui:toast - Toast notifications
    - ui:carousel - Image/content slider
    - ui:stepper - Wizard/step progress
    - ui:calendar - Date picker
-->
<q:application id="NewComponentsDemo" type="ui" theme="dark">

    <ui:window title="New Components Library">
        <ui:vbox padding="lg" gap="lg">

            <!-- Header -->
            <ui:text size="2xl" weight="bold">New Components Library</ui:text>
            <ui:text color="muted">
                Demonstration of toast, carousel, stepper, and calendar components.
            </ui:text>

            <ui:rule />

            <!-- Toast Notifications -->
            <ui:panel title="Toast Notifications">
                <ui:text size="sm" color="muted">
                    Click buttons to show toast notifications at different positions.
                </ui:text>
                <ui:hbox gap="md" padding="md">
                    <ui:button variant="info" on-click="__quantumToast.show({variant: 'info', title: 'Information', message: 'This is an informational message.'})">
                        Info Toast
                    </ui:button>
                    <ui:button variant="success" on-click="__quantumToast.show({variant: 'success', title: 'Success', message: 'Operation completed successfully!'})">
                        Success Toast
                    </ui:button>
                    <ui:button variant="warning" on-click="__quantumToast.show({variant: 'warning', title: 'Warning', message: 'Please review your input.'})">
                        Warning Toast
                    </ui:button>
                    <ui:button variant="danger" on-click="__quantumToast.show({variant: 'danger', title: 'Error', message: 'An error occurred. Please try again.'})">
                        Error Toast
                    </ui:button>
                </ui:hbox>

                <ui:hbox gap="sm" padding="md">
                    <ui:text size="sm">Position:</ui:text>
                    <ui:select bind="toastPosition">
                        <ui:option value="top-right">Top Right</ui:option>
                        <ui:option value="top-left">Top Left</ui:option>
                        <ui:option value="bottom-right">Bottom Right</ui:option>
                        <ui:option value="bottom-left">Bottom Left</ui:option>
                        <ui:option value="top-center">Top Center</ui:option>
                        <ui:option value="bottom-center">Bottom Center</ui:option>
                    </ui:select>
                </ui:hbox>
            </ui:panel>

            <!-- Carousel -->
            <ui:panel title="Carousel / Slider">
                <ui:carousel
                    id="demo-carousel"
                    auto-play="true"
                    interval="4000"
                    show-indicators="true"
                    show-arrows="true"
                    animation="slide">

                    <ui:slide>
                        <ui:vbox padding="xl" background="primary" align="center">
                            <ui:text size="xl" weight="bold" color="white">Slide 1</ui:text>
                            <ui:text color="white">Welcome to Quantum Framework</ui:text>
                        </ui:vbox>
                    </ui:slide>

                    <ui:slide>
                        <ui:vbox padding="xl" background="success" align="center">
                            <ui:text size="xl" weight="bold" color="white">Slide 2</ui:text>
                            <ui:text color="white">Build declarative applications</ui:text>
                        </ui:vbox>
                    </ui:slide>

                    <ui:slide>
                        <ui:vbox padding="xl" background="info" align="center">
                            <ui:text size="xl" weight="bold" color="white">Slide 3</ui:text>
                            <ui:text color="white">Deploy anywhere - Web, Desktop, Mobile</ui:text>
                        </ui:vbox>
                    </ui:slide>

                </ui:carousel>
            </ui:panel>

            <!-- Stepper -->
            <ui:panel title="Stepper / Wizard">
                <ui:stepper
                    id="demo-stepper"
                    orientation="horizontal"
                    current="0"
                    linear="true">

                    <ui:step title="Account" description="Create your account">
                        <ui:form>
                            <ui:formitem label="Email">
                                <ui:input type="email" placeholder="your@email.com" />
                            </ui:formitem>
                            <ui:formitem label="Password">
                                <ui:input type="password" placeholder="Choose a password" />
                            </ui:formitem>
                        </ui:form>
                    </ui:step>

                    <ui:step title="Profile" description="Tell us about yourself">
                        <ui:form>
                            <ui:formitem label="Name">
                                <ui:input placeholder="Your full name" />
                            </ui:formitem>
                            <ui:formitem label="Company">
                                <ui:input placeholder="Company name (optional)" />
                            </ui:formitem>
                        </ui:form>
                    </ui:step>

                    <ui:step title="Preferences" description="Customize your experience" optional="true">
                        <ui:form>
                            <ui:formitem label="Theme">
                                <ui:select>
                                    <ui:option value="dark">Dark Mode</ui:option>
                                    <ui:option value="light">Light Mode</ui:option>
                                </ui:select>
                            </ui:formitem>
                            <ui:formitem label="Notifications">
                                <ui:switch label="Enable email notifications" />
                            </ui:formitem>
                        </ui:form>
                    </ui:step>

                    <ui:step title="Complete" description="All done!">
                        <ui:vbox align="center" padding="lg">
                            <ui:text size="xl" color="success">Registration Complete!</ui:text>
                            <ui:text color="muted">Welcome to Quantum Framework</ui:text>
                        </ui:vbox>
                    </ui:step>

                </ui:stepper>

                <ui:hbox gap="md" justify="end" padding="md">
                    <ui:button variant="secondary" on-click="__quantumStepper.get('demo-stepper').prev()">Previous</ui:button>
                    <ui:button variant="primary" on-click="var s = __quantumStepper.get('demo-stepper'); s.complete(); s.next()">Next</ui:button>
                </ui:hbox>
            </ui:panel>

            <!-- Calendar -->
            <ui:hbox gap="lg">
                <ui:panel title="Single Date Selection" width="1/2">
                    <ui:calendar
                        id="calendar-single"
                        mode="single"
                        bind="selectedDate"
                    />
                    <ui:text size="sm" padding="md">
                        Selected: <ui:text weight="bold">{selectedDate}</ui:text>
                    </ui:text>
                </ui:panel>

                <ui:panel title="Date Range Selection" width="1/2">
                    <ui:calendar
                        id="calendar-range"
                        mode="range"
                        bind="dateRange"
                    />
                    <ui:text size="sm" padding="md">
                        Range: <ui:text weight="bold">{dateRange.start}</ui:text>
                        to <ui:text weight="bold">{dateRange.end}</ui:text>
                    </ui:text>
                </ui:panel>
            </ui:hbox>

            <!-- Date Picker Input -->
            <ui:panel title="Date Picker Input">
                <ui:form>
                    <ui:formitem label="Appointment Date">
                        <ui:date-picker
                            bind="appointmentDate"
                            placeholder="Select a date"
                            min-date="2024-01-01"
                            format="MM/DD/YYYY"
                        />
                    </ui:formitem>
                    <ui:formitem label="Date Range">
                        <ui:hbox gap="md">
                            <ui:date-picker bind="startDate" placeholder="Start date" />
                            <ui:text>to</ui:text>
                            <ui:date-picker bind="endDate" placeholder="End date" />
                        </ui:hbox>
                    </ui:formitem>
                </ui:form>
            </ui:panel>

        </ui:vbox>
    </ui:window>

    <!-- Toast Container -->
    <ui:toast-container position="top-right" max-toasts="5" />

    <!-- A standalone UI build draws layout only (UI-8): the buttons call the
         components' own JavaScript directly. Logic belongs in pages. -->

</q:application>
