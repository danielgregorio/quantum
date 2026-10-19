//! The pending suggestion requests.
//!
//! Generating with the local model takes seconds, while requests can arrive
//! in bursts (twenty `rm -rf` in a script, a crash-looping service). Rather
//! than build up minutes of stale work, the queue keeps a few requests and
//! drops the oldest when a new one arrives: the latest event is the one a
//! user is most likely looking at.
//!
//! A question a user typed is different: someone is waiting on that exact
//! answer. Those go in a lane of their own, answered first and never
//! dropped to make room for events.

use std::collections::VecDeque;
use std::sync::Mutex;
use tokio::sync::Notify;

pub struct RequestQueue<T> {
    items: Mutex<Lanes<T>>,
    capacity: usize,
    ready: Notify,
}

struct Lanes<T> {
    /// Users' questions, in the order asked.
    priority: VecDeque<T>,
    /// Everything else, bounded by `capacity`.
    events: VecDeque<T>,
}

impl<T> RequestQueue<T> {
    pub fn new(capacity: usize) -> Self {
        Self {
            items: Mutex::new(Lanes {
                priority: VecDeque::new(),
                events: VecDeque::with_capacity(capacity),
            }),
            capacity: capacity.max(1),
            ready: Notify::new(),
        }
    }

    /// Queue `item`; returns the oldest request if it had to make room.
    pub fn push(&self, item: T) -> Option<T> {
        let dropped = {
            let mut lanes = self.items.lock().expect("queue lock poisoned");
            let dropped = if lanes.events.len() >= self.capacity {
                lanes.events.pop_front()
            } else {
                None
            };
            lanes.events.push_back(item);
            dropped
        };
        self.ready.notify_one();
        dropped
    }

    /// Queue a user's question: ahead of every event, never dropped.
    pub fn push_priority(&self, item: T) {
        self.items
            .lock()
            .expect("queue lock poisoned")
            .priority
            .push_back(item);
        self.ready.notify_one();
    }

    /// Wait for the next request: questions first, then events, each
    /// oldest first.
    pub async fn pop(&self) -> T {
        loop {
            {
                let mut lanes = self.items.lock().expect("queue lock poisoned");
                if let Some(item) = lanes
                    .priority
                    .pop_front()
                    .or_else(|| lanes.events.pop_front())
                {
                    return item;
                }
            }
            // A push between the check above and this await still wakes us:
            // notify_one stores a permit when nobody is waiting yet.
            self.ready.notified().await;
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::Arc;
    use std::time::Duration;

    #[tokio::test]
    async fn requests_come_out_oldest_first() {
        let queue = RequestQueue::new(4);
        queue.push(1);
        queue.push(2);
        assert_eq!(queue.pop().await, 1);
        assert_eq!(queue.pop().await, 2);
    }

    #[tokio::test]
    async fn a_full_queue_drops_its_oldest_request() {
        let queue = RequestQueue::new(2);
        assert_eq!(queue.push(1), None);
        assert_eq!(queue.push(2), None);
        assert_eq!(queue.push(3), Some(1));
        assert_eq!(queue.pop().await, 2);
        assert_eq!(queue.pop().await, 3);
    }

    #[tokio::test]
    async fn questions_jump_the_queue_and_survive_event_bursts() {
        let queue = RequestQueue::new(2);
        queue.push(1);
        queue.push_priority(100);
        for event in 2..10 {
            // A burst of events only ever drops other events.
            assert_ne!(queue.push(event), Some(100));
        }
        queue.push_priority(101);
        assert_eq!(queue.pop().await, 100);
        assert_eq!(queue.pop().await, 101);
        assert_eq!(queue.pop().await, 8);
        assert_eq!(queue.pop().await, 9);
    }

    #[tokio::test]
    async fn a_waiting_worker_wakes_up_on_push() {
        let queue = Arc::new(RequestQueue::new(2));
        let waiting = tokio::spawn({
            let queue = queue.clone();
            async move { queue.pop().await }
        });
        tokio::time::sleep(Duration::from_millis(20)).await;
        queue.push(7);
        let popped = tokio::time::timeout(Duration::from_secs(1), waiting)
            .await
            .expect("worker never woke")
            .unwrap();
        assert_eq!(popped, 7);
    }
}
