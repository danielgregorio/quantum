#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quantum CLI - Job Management Commands

Commands for managing scheduled jobs, threads, and job queues.
"""

import argparse
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Optional

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def create_jobs_parser(subparsers):
    """Add jobs subcommand to CLI parser"""
    jobs_parser = subparsers.add_parser(
        'jobs',
        help='Manage scheduled jobs and job queues',
        description='Commands for managing scheduled jobs, threads, and job queues'
    )

    jobs_sub = jobs_parser.add_subparsers(dest='jobs_action', help='Job action')

    # List jobs
    list_parser = jobs_sub.add_parser('list', help='List all scheduled jobs')
    list_parser.add_argument('--status', choices=['all', 'active', 'paused', 'pending', 'running', 'failed'],
                             default='all', help='Filter by status')
    list_parser.add_argument('--queue', help='Filter by queue name')
    list_parser.add_argument('--format', choices=['table', 'json'], default='table', help='Output format')

    # Job status
    status_parser = jobs_sub.add_parser('status', help='Get detailed job status')
    status_parser.add_argument('name', help='Job name')
    status_parser.add_argument('--format', choices=['table', 'json'], default='table', help='Output format')

    # Run job manually
    run_parser = jobs_sub.add_parser('run', help='Run a job manually')
    run_parser.add_argument('name', help='Job name')
    run_parser.add_argument('--sync', action='store_true', help='Wait for job to complete')
    run_parser.add_argument('--params', help='JSON parameters for the job')

    # Pause job
    pause_parser = jobs_sub.add_parser('pause', help='Pause a scheduled job')
    pause_parser.add_argument('name', help='Job name')

    # Resume job
    resume_parser = jobs_sub.add_parser('resume', help='Resume a paused job')
    resume_parser.add_argument('name', help='Job name')

    # Cancel job
    cancel_parser = jobs_sub.add_parser('cancel', help='Cancel a running or pending job')
    cancel_parser.add_argument('name', help='Job name or job ID')

    # Job history
    history_parser = jobs_sub.add_parser('history', help='View job execution history')
    history_parser.add_argument('name', nargs='?', help='Job name (optional, shows all if not specified)')
    history_parser.add_argument('--limit', type=int, default=10, help='Number of entries to show')
    history_parser.add_argument('--status', choices=['all', 'success', 'failed'], default='all')
    history_parser.add_argument('--format', choices=['table', 'json'], default='table', help='Output format')

    # Worker
    worker_parser = jobs_sub.add_parser('worker', help='Start a job worker process')
    worker_sub = worker_parser.add_subparsers(dest='worker_action', help='Worker action')

    start_worker = worker_sub.add_parser('start', help='Start worker')
    start_worker.add_argument('--queue', default='default', help='Queue(s) to process (comma-separated)')
    start_worker.add_argument('--concurrency', type=int, default=4, help='Number of concurrent workers')
    start_worker.add_argument('--poll-interval', type=float, default=1.0, help='Poll interval in seconds')

    stop_worker = worker_sub.add_parser('stop', help='Stop worker')
    stop_worker.add_argument('--graceful', action='store_true', help='Wait for running jobs to complete')

    # Queues management
    queues_parser = jobs_sub.add_parser('queues', help='Manage job queues')
    queues_sub = queues_parser.add_subparsers(dest='queues_action', help='Queue action')

    list_queues = queues_sub.add_parser('list', help='List all queues')
    list_queues.add_argument('--format', choices=['table', 'json'], default='table')

    purge_queue = queues_sub.add_parser('purge', help='Purge all jobs from a queue')
    purge_queue.add_argument('name', help='Queue name')
    purge_queue.add_argument('--status', choices=['all', 'pending', 'failed'], default='all')

    stats_queue = queues_sub.add_parser('stats', help='Show queue statistics')
    stats_queue.add_argument('name', nargs='?', help='Queue name (optional)')

    return jobs_parser


def handle_jobs(args) -> int:
    """Handle jobs command"""
    from runtime.job_executor import JobExecutor

    if not args.jobs_action:
        print("Usage: quantum jobs <action>")
        print("Actions: list, status, run, pause, resume, cancel, history, worker, queues")
        return 1

    try:
        executor = JobExecutor()

        if args.jobs_action == 'list':
            return _handle_jobs_list(executor, args)
        elif args.jobs_action == 'status':
            return _handle_jobs_status(executor, args)
        elif args.jobs_action == 'run':
            return _handle_jobs_run(executor, args)
        elif args.jobs_action == 'pause':
            return _handle_jobs_pause(executor, args)
        elif args.jobs_action == 'resume':
            return _handle_jobs_resume(executor, args)
        elif args.jobs_action == 'cancel':
            return _handle_jobs_cancel(executor, args)
        elif args.jobs_action == 'history':
            return _handle_jobs_history(executor, args)
        elif args.jobs_action == 'worker':
            return _handle_jobs_worker(executor, args)
        elif args.jobs_action == 'queues':
            return _handle_jobs_queues(executor, args)
        else:
            print(f"Unknown action: {args.jobs_action}")
            return 1

    except Exception as e:
        print(f"[ERROR] {e}")
        return 1


def _handle_jobs_list(executor, args) -> int:
    """List all jobs"""
    jobs = executor.list_jobs(
        status=args.status if args.status != 'all' else None,
        queue=args.queue
    )

    if args.format == 'json':
        print(json.dumps(jobs, indent=2, default=str))
    else:
        if not jobs:
            print("No jobs found.")
            return 0

        # Table format
        print(f"{'Name':<25} {'Queue':<15} {'Status':<10} {'Next Run':<20} {'Last Run':<20}")
        print("-" * 95)
        for job in jobs:
            next_run = job.get('next_run', '-')
            last_run = job.get('last_run', '-')
            if isinstance(next_run, datetime):
                next_run = next_run.strftime('%Y-%m-%d %H:%M:%S')
            if isinstance(last_run, datetime):
                last_run = last_run.strftime('%Y-%m-%d %H:%M:%S')
            print(f"{job['name']:<25} {job.get('queue', 'default'):<15} {job['status']:<10} {next_run:<20} {last_run:<20}")

    return 0


def _handle_jobs_status(executor, args) -> int:
    """Get job status"""
    job = executor.get_job_status(args.name)

    if not job:
        print(f"Job not found: {args.name}")
        return 1

    if args.format == 'json':
        print(json.dumps(job, indent=2, default=str))
    else:
        print(f"Job: {job['name']}")
        print(f"Status: {job['status']}")
        print(f"Queue: {job.get('queue', 'default')}")
        if job.get('interval'):
            print(f"Interval: {job['interval']}")
        if job.get('cron'):
            print(f"Cron: {job['cron']}")
        print(f"Last Run: {job.get('last_run', 'Never')}")
        print(f"Next Run: {job.get('next_run', '-')}")
        print(f"Run Count: {job.get('run_count', 0)}")
        print(f"Error Count: {job.get('error_count', 0)}")
        if job.get('last_error'):
            print(f"Last Error: {job['last_error']}")

    return 0


def _handle_jobs_run(executor, args) -> int:
    """Run job manually"""
    params = {}
    if args.params:
        try:
            params = json.loads(args.params)
        except json.JSONDecodeError as e:
            print(f"Invalid JSON parameters: {e}")
            return 1

    print(f"Running job: {args.name}...")
    result = executor.run_job_now(args.name, params=params, wait=args.sync)

    if args.sync:
        if result.get('success'):
            print(f"Job completed successfully.")
            if result.get('result'):
                print(f"Result: {result['result']}")
        else:
            print(f"Job failed: {result.get('error', 'Unknown error')}")
            return 1
    else:
        print(f"Job queued for execution. Job ID: {result.get('job_id', 'N/A')}")

    return 0


def _handle_jobs_pause(executor, args) -> int:
    """Pause a scheduled job"""
    if executor.pause_job(args.name):
        print(f"Job paused: {args.name}")
        return 0
    else:
        print(f"Failed to pause job: {args.name}")
        return 1


def _handle_jobs_resume(executor, args) -> int:
    """Resume a paused job"""
    if executor.resume_job(args.name):
        print(f"Job resumed: {args.name}")
        return 0
    else:
        print(f"Failed to resume job: {args.name}")
        return 1


def _handle_jobs_cancel(executor, args) -> int:
    """Cancel a job"""
    if executor.cancel_job(args.name):
        print(f"Job cancelled: {args.name}")
        return 0
    else:
        print(f"Failed to cancel job: {args.name}")
        return 1


def _handle_jobs_history(executor, args) -> int:
    """View job history"""
    history = executor.get_job_history(
        name=args.name,
        limit=args.limit,
        status=args.status if args.status != 'all' else None
    )

    if args.format == 'json':
        print(json.dumps(history, indent=2, default=str))
    else:
        if not history:
            print("No history found.")
            return 0

        print(f"{'Job':<20} {'Status':<10} {'Started':<20} {'Duration':<12} {'Error':<30}")
        print("-" * 95)
        for entry in history:
            started = entry.get('started_at', '-')
            if isinstance(started, datetime):
                started = started.strftime('%Y-%m-%d %H:%M:%S')

            duration = entry.get('duration', '-')
            if isinstance(duration, (int, float)):
                duration = f"{duration:.2f}s"

            error = entry.get('error', '')[:30] if entry.get('error') else ''

            print(f"{entry['name']:<20} {entry['status']:<10} {started:<20} {str(duration):<12} {error:<30}")

    return 0


def _handle_jobs_worker(executor, args) -> int:
    """Handle worker commands"""
    if not args.worker_action:
        print("Usage: quantum jobs worker <start|stop>")
        return 1

    if args.worker_action == 'start':
        queues = [q.strip() for q in args.queue.split(',')]
        print(f"Starting worker...")
        print(f"  Queues: {', '.join(queues)}")
        print(f"  Concurrency: {args.concurrency}")
        print(f"  Poll interval: {args.poll_interval}s")
        print("")
        print("Press Ctrl+C to stop the worker.")
        print("")

        try:
            executor.start_worker(
                queues=queues,
                concurrency=args.concurrency,
                poll_interval=args.poll_interval
            )
        except KeyboardInterrupt:
            print("\nStopping worker...")
            executor.stop_worker(graceful=True)
            print("Worker stopped.")

        return 0

    elif args.worker_action == 'stop':
        executor.stop_worker(graceful=args.graceful)
        print("Worker stop signal sent.")
        return 0

    return 1


def _handle_jobs_queues(executor, args) -> int:
    """Handle queue management commands"""
    if not args.queues_action:
        print("Usage: quantum jobs queues <list|purge|stats>")
        return 1

    if args.queues_action == 'list':
        queues = executor.list_queues()

        if args.format == 'json':
            print(json.dumps(queues, indent=2))
        else:
            if not queues:
                print("No queues found.")
                return 0

            print(f"{'Queue':<20} {'Pending':<10} {'Running':<10} {'Completed':<10} {'Failed':<10}")
            print("-" * 65)
            for q in queues:
                print(f"{q['name']:<20} {q.get('pending', 0):<10} {q.get('running', 0):<10} {q.get('completed', 0):<10} {q.get('failed', 0):<10}")

        return 0

    elif args.queues_action == 'purge':
        count = executor.purge_queue(args.name, status=args.status if args.status != 'all' else None)
        print(f"Purged {count} job(s) from queue: {args.name}")
        return 0

    elif args.queues_action == 'stats':
        stats = executor.get_queue_stats(args.name)

        print("Queue Statistics")
        print("-" * 40)
        for key, value in stats.items():
            print(f"  {key}: {value}")

        return 0

    return 1
