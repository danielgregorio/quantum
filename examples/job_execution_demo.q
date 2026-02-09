<?xml version="1.0" encoding="UTF-8"?>
<!--
  Job Execution System Demo

  This example demonstrates the three main job execution features:
  1. q:schedule - Scheduled task execution (like cfschedule)
  2. q:thread - Async thread execution (like cfthread)
  3. q:job - Job queue for batch processing
-->

<q:component name="JobExecutionDemo" xmlns:q="https://quantum.lang/ns">

    <!-- ======================================
         SCHEDULED TASKS (q:schedule)
         ====================================== -->

    <!-- Daily cleanup task - runs every 24 hours -->
    <q:schedule name="dailyCleanup" interval="1d" timezone="America/Sao_Paulo">
        <q:set name="cleanupTime" value="{now()}" />
        <q:log level="info" message="Running daily cleanup at {cleanupTime}" />
        <!-- In a real app, this would delete old records, temp files, etc. -->
    </q:schedule>

    <!-- Hourly stats aggregation using cron expression -->
    <q:schedule name="hourlyStats" cron="0 * * * *" retry="3">
        <q:log level="info" message="Aggregating hourly statistics..." />
    </q:schedule>

    <!-- One-time scheduled task for a specific date -->
    <q:schedule name="newYearGreeting" at="2025-01-01T00:00:00" timezone="UTC">
        <q:log level="info" message="Happy New Year!" />
    </q:schedule>

    <!-- Pause/Resume/Delete schedule actions -->
    <!-- <q:schedule name="dailyCleanup" action="pause" /> -->
    <!-- <q:schedule name="dailyCleanup" action="resume" /> -->
    <!-- <q:schedule name="dailyCleanup" action="delete" /> -->


    <!-- ======================================
         ASYNC THREADS (q:thread)
         ====================================== -->

    <!-- Background email sending thread -->
    <q:thread name="emailSender" priority="high" timeout="5m">
        <q:set name="emailsSent" value="0" />
        <q:log level="info" message="Starting email batch send..." />
        <!-- In a real app, this would loop through pending emails -->
        <q:set name="emailsSent" value="10" />
        <q:log level="info" message="Sent {emailsSent} emails" />
    </q:thread>

    <!-- Low priority background processing thread -->
    <q:thread name="imageProcessor" priority="low" timeout="10m"
              onComplete="handleImageProcessingComplete"
              onError="handleImageProcessingError">
        <q:log level="info" message="Processing images in background..." />
    </q:thread>

    <!-- Wait for a thread to complete -->
    <!-- <q:thread name="emailSender" action="join" /> -->

    <!-- Terminate a running thread -->
    <!-- <q:thread name="imageProcessor" action="terminate" /> -->


    <!-- ======================================
         JOB QUEUE (q:job)
         ====================================== -->

    <!-- Define a job handler for sending emails -->
    <q:job name="sendEmail" queue="emails" priority="5" attempts="3" backoff="30s">
        <q:param name="to" type="string" required="true" />
        <q:param name="subject" type="string" required="true" />
        <q:param name="body" type="string" />

        <q:log level="info" message="Sending email to {to}: {subject}" />
        <!-- <q:mail to="{to}" subject="{subject}">{body}</q:mail> -->
        <q:set name="emailResult" value="sent" />
    </q:job>

    <!-- Define a job handler for order processing -->
    <q:job name="processOrder" queue="orders" priority="8" attempts="5" backoff="1m">
        <q:param name="orderId" type="string" required="true" />
        <q:param name="customerId" type="string" />

        <q:log level="info" message="Processing order {orderId} for customer {customerId}" />
        <!-- Order processing logic here -->
    </q:job>

    <!-- Dispatch jobs to the queue -->
    <q:set name="customerEmail" value="customer@example.com" />
    <q:set name="orderId" value="ORD-12345" />

    <!-- Dispatch email job with delay -->
    <q:job name="sendEmail" action="dispatch" queue="emails" delay="30s">
        <q:param name="to" value="{customerEmail}" />
        <q:param name="subject" value="Order Confirmation" />
        <q:param name="body" value="Thank you for your order!" />
    </q:job>

    <!-- Dispatch order processing job immediately -->
    <q:job name="processOrder" action="dispatch" queue="orders">
        <q:param name="orderId" value="{orderId}" />
        <q:param name="customerId" value="CUST-001" />
    </q:job>


    <!-- ======================================
         CALLBACK FUNCTIONS
         ====================================== -->

    <q:function name="handleImageProcessingComplete">
        <q:param name="result" type="any" />
        <q:log level="info" message="Image processing completed: {result}" />
    </q:function>

    <q:function name="handleImageProcessingError">
        <q:param name="error" type="string" />
        <q:log level="error" message="Image processing failed: {error}" />
    </q:function>


    <!-- ======================================
         DISPLAY DEMO RESULTS
         ====================================== -->

    <div class="job-demo">
        <h1>Job Execution System Demo</h1>

        <section class="schedules">
            <h2>Scheduled Tasks</h2>
            <ul>
                <li>Daily Cleanup: {schedule_dailyCleanup.trigger_info}</li>
                <li>Hourly Stats: {schedule_hourlyStats.trigger_info}</li>
                <li>New Year Greeting: {schedule_newYearGreeting.trigger_info}</li>
            </ul>
        </section>

        <section class="threads">
            <h2>Background Threads</h2>
            <ul>
                <li>Email Sender: {thread_emailSender.status}</li>
                <li>Image Processor: {thread_imageProcessor.status}</li>
            </ul>
        </section>

        <section class="jobs">
            <h2>Job Queue</h2>
            <ul>
                <li>Email Job: ID #{dispatched_job_sendEmail.job_id}</li>
                <li>Order Job: ID #{dispatched_job_processOrder.job_id}</li>
            </ul>
        </section>
    </div>

</q:component>
