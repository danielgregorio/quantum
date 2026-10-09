extends Area2D
# The area a moving thing (thing.gd) is touched through. A character's
# sensor sees areas; this one answers for its owner.


func quantum_owner() -> Node:
	return get_parent()


func quantum_tag() -> String:
	return get_parent().quantum_tag()
