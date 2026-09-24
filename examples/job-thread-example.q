<?xml version="1.0" encoding="UTF-8"?>
<!--
Example: Async Threads with q:thread
Demonstrates async execution similar to ColdFusion's cfthread
-->
<q:component xmlns:q="https://quantum.lang/ns" name="ThreadExample">
    <!-- State -->
    <q:set name="processingStatus" value="idle" />
    <q:set name="processedCount" value="0" />

    <!-- Start processing in background -->
    <q:action name="startBulkEmail">
        <q:set name="processingStatus" value="processing" />

        <!-- Launch async thread -->
        <q:thread name="email-sender"
                  priority="normal"
                  timeout="5m"
                  on-complete="onEmailsComplete"
                  on-error="onEmailsError">

            <q:query name="subscribers" datasource="db">
                SELECT id, email, name FROM subscribers
                WHERE status = 'active'
            </q:query>

            <q:set name="count" value="0" />

            <q:loop type="query" var="sub" items="{subscribers}">
                <q:mail to="{sub.email}" subject="Newsletter">
                    <q:body template="newsletter.html">
                        <q:param name="name" value="{sub.name}" />
                    </q:body>
                </q:mail>

                <q:set name="count" operation="increment" />

                <!-- Rate limiting: 100ms delay between emails -->
                <q:set name="_delay" value="100" />
            </q:loop>

            <q:return value="{count}" />
        </q:thread>

        <p>Email sending started in background...</p>
    </q:action>

    <!-- Join thread (wait for completion) -->
    <q:action name="waitForCompletion">
        <q:thread name="email-sender" action="join" timeout="60s" />
        <p>Thread completed!</p>
    </q:action>

    <!-- Terminate thread -->
    <q:action name="cancelProcessing">
        <q:thread name="email-sender" action="terminate" />
        <q:set name="processingStatus" value="cancelled" />
        <p>Processing cancelled</p>
    </q:action>

    <!-- Callbacks -->
    <q:function name="onEmailsComplete">
        <q:param name="result" type="any" />
        <q:set name="processingStatus" value="completed" />
        <q:set name="processedCount" value="{result}" />
        <q:log level="info">Email sending complete: {result} emails sent</q:log>
    </q:function>

    <q:function name="onEmailsError">
        <q:param name="error" type="string" />
        <q:set name="processingStatus" value="error" />
        <q:log level="error">Email sending failed: {error}</q:log>
    </q:function>

    <!-- Multiple parallel threads -->
    <q:action name="parallelProcessing">
        <!-- Thread 1: Process images -->
        <q:thread name="image-processor" priority="high">
            <q:invoke function="processImages" />
        </q:thread>

        <!-- Thread 2: Generate reports -->
        <q:thread name="report-generator" priority="normal">
            <q:invoke function="generateReports" />
        </q:thread>

        <!-- Thread 3: Send notifications -->
        <q:thread name="notifier" priority="low">
            <q:invoke function="sendNotifications" />
        </q:thread>

        <p>Started 3 parallel threads</p>
    </q:action>

    <!-- Wait for all threads -->
    <q:action name="waitForAll">
        <q:thread name="image-processor" action="join" />
        <q:thread name="report-generator" action="join" />
        <q:thread name="notifier" action="join" />
        <p>All threads completed!</p>
    </q:action>

    <!-- Display UI -->
    <div>
        <h2>Background Processing</h2>
        <p>Status: {processingStatus}</p>
        <p>Processed: {processedCount}</p>

        <button onclick="startBulkEmail()">Start Email Campaign</button>
        <button onclick="waitForCompletion()">Wait for Completion</button>
        <button onclick="cancelProcessing()">Cancel</button>
    </div>
</q:component>
