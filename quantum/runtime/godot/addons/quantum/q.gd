extends Node
# Q: the helpers the compiled scripts call. An autoload (project.godot),
# so every script sees `Q`.
#
# Where GDScript's operators differ from Quantum's expression semantics
# (quantum/core/expressions.py), the compiler emits one of these instead.


# `/` in Quantum is a float division, whatever the operands.
static func div(a, b):
	return float(a) / float(b)


# `//` floors, like Python.
static func floordiv(a, b):
	return floori(float(a) / float(b))


# `%` follows the divisor's sign, like Python.
static func mod(a, b):
	return fposmod(float(a), float(b))


# `len()` of a string, an array or a dictionary.
static func len(v) -> int:
	if v is String:
		return (v as String).length()
	if v is Array or v is Dictionary:
		return v.size()
	return 0


# Removes a thing from the scene at the end of the tick.
static func destroy(node) -> void:
	if node == null or not is_instance_valid(node):
		return
	if node.has_method("quantum_destroy"):
		node.quantum_destroy()
	else:
		node.queue_free()
