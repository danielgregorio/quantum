"""
Runtime for Event System

Handles event registration, dispatch, and handler execution.
"""

from typing import Dict, List, Callable, Any, Optional
from dataclasses import dataclass, field
import time


@dataclass
class EventHandler:
    """Registered event handler"""
    event_name: str
    callback: Callable
    once: bool = False
    capture: bool = False
    debounce: Optional[int] = None
    throttle: Optional[int] = None
    last_called: float = 0


class EventBus:
    """Central event bus for Quantum applications"""

    def __init__(self):
        self._handlers: Dict[str, List[EventHandler]] = {}
        self._global_handlers: List[EventHandler] = []

    def on(self, event_name: str, callback: Callable, **options) -> EventHandler:
        """
        Register event handler

        Args:
            event_name: Name of event to listen for
            callback: Function to call when event fires
            **options: once, capture, debounce, throttle

        Returns:
            EventHandler instance
        """
        handler = EventHandler(
            event_name=event_name,
            callback=callback,
            once=options.get('once', False),
            capture=options.get('capture', False),
            debounce=options.get('debounce'),
            throttle=options.get('throttle')
        )

        if event_name not in self._handlers:
            self._handlers[event_name] = []

        self._handlers[event_name].append(handler)

        return handler

    def once(self, event_name: str, callback: Callable) -> EventHandler:
        """Register one-time event handler"""
        return self.on(event_name, callback, once=True)

    def off(self, event_name: str, callback: Optional[Callable] = None):
        """
        Unregister event handler(s)

        Args:
            event_name: Name of event
            callback: Specific callback to remove (if None, removes all)
        """
        if event_name not in self._handlers:
            return

        if callback is None:
            # Remove all handlers for this event
            del self._handlers[event_name]
        else:
            # Remove specific handler
            self._handlers[event_name] = [
                h for h in self._handlers[event_name]
                if h.callback != callback
            ]

    def dispatch(self, event_name: str, data: Any = None, **options) -> bool:
        """
        Dispatch (emit) an event

        Args:
            event_name: Name of event to fire
            data: Event data
            **options: bubbles, cancelable, etc

        Returns:
            True if event was not canceled
        """
        if event_name not in self._handlers:
            return True  # No handlers, event proceeds

        event_object = {
            'type': event_name,
            'data': data,
            'timestamp': time.time(),
            'bubbles': options.get('bubbles', True),
            'cancelable': options.get('cancelable', True),
            'defaultPrevented': False,
            'propagationStopped': False
        }

        # Execute handlers
        handlers_to_remove = []

        for handler in self._handlers[event_name]:
            # Check debounce
            if handler.debounce:
                current_time = time.time() * 1000  # Convert to ms
                if current_time - handler.last_called < handler.debounce:
                    continue  # Skip this call

            # Check throttle
            if handler.throttle:
                current_time = time.time() * 1000  # Convert to ms
                if current_time - handler.last_called < handler.throttle:
                    continue  # Skip this call

            # Call handler
            try:
                handler.callback(event_object)
                handler.last_called = time.time() * 1000
            except Exception as e:
                print(f"Error in event handler for '{event_name}': {e}")

            # Check if propagation was stopped
            if event_object.get('propagationStopped'):
                break

            # Mark for removal if once=true
            if handler.once:
                handlers_to_remove.append(handler)

        # Remove one-time handlers
        for handler in handlers_to_remove:
            self._handlers[event_name].remove(handler)

        # Return whether default was prevented
        return not event_object.get('defaultPrevented', False)

    def clear(self):
        """Clear all event handlers"""
        self._handlers.clear()

    def list_events(self) -> List[str]:
        """List all events with registered handlers"""
        return list(self._handlers.keys())

    def count_handlers(self, event_name: str) -> int:
        """Count handlers for specific event"""
        return len(self._handlers.get(event_name, []))


# Global event bus instance
_global_event_bus = EventBus()


def get_event_bus() -> EventBus:
    """Get global event bus instance"""
    return _global_event_bus


def on(event_name: str, callback: Callable, **options) -> EventHandler:
    """Register event handler on global bus"""
    return _global_event_bus.on(event_name, callback, **options)


def once(event_name: str, callback: Callable) -> EventHandler:
    """Register one-time event handler on global bus"""
    return _global_event_bus.once(event_name, callback)


def off(event_name: str, callback: Optional[Callable] = None):
    """Unregister event handler from global bus"""
    _global_event_bus.off(event_name, callback)


def dispatch(event_name: str, data: Any = None, **options) -> bool:
    """Dispatch event on global bus"""
    return _global_event_bus.dispatch(event_name, data, **options)


def clear():
    """Clear all handlers from global bus"""
    _global_event_bus.clear()
