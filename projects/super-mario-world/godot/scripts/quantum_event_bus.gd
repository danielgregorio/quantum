extends Node
## Quantum Event Bus - Global event system autoload
## Allows decoupled communication between game objects.

var _listeners: Dictionary = {}

func emit_event(event_name: String, data: Dictionary = {}):
	if event_name in _listeners:
		for callback in _listeners[event_name]:
			if callback.is_valid():
				callback.call(data)

func listen(event_name: String, callback: Callable):
	if event_name not in _listeners:
		_listeners[event_name] = []
	_listeners[event_name].append(callback)

func remove_listener(event_name: String, callback: Callable):
	if event_name in _listeners:
		_listeners[event_name].erase(callback)

func clear(event_name: String = ""):
	if event_name:
		_listeners.erase(event_name)
	else:
		_listeners.clear()
