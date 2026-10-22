extends Node
# What a character or a thing carries (qg:attach): each carried thing goes
# where its carrier goes, at its offset, every tick after everything has moved.
# A node of the carrier's ("Carried"), so it goes with it.

var carried: Array = []   # [thing, offset]


func _ready() -> void:
	name = "Carried"
	process_physics_priority = 90   # after the bodies and the things have moved this tick


func _physics_process(_delta: float) -> void:
	var carrier := get_parent() as Node2D
	for entry in carried.duplicate():
		var thing = entry[0]
		if not is_instance_valid(thing) or thing.is_queued_for_deletion():
			carried.erase(entry)
			continue
		(thing as Node2D).position = carrier.position + (entry[1] as Vector2)
