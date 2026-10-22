extends RefCounted
# Health and states for the prefabs that do not move (item.gd, block.gd),
# as a moving thing has them (thing.gd): qg:damage takes health; while it
# lives its qg:on-damage runs, at 0 its qg:on-death and the scene's
# qg:on-death of= its tag, and it is gone. qg:become changes its frame.
# The node keeps the values (health, state, _dead...); these work on them.


static func setup(node: Node, prefab: Dictionary) -> void:
	node.health = int(prefab.get("health", 1))
	node.on_damage = str(prefab.get("on_damage", "")) if prefab.get("on_damage") != null else ""
	node.on_death = str(prefab.get("on_death", "")) if prefab.get("on_death") != null else ""
	node.states = prefab.get("states", {})
	node.base_frame = int(prefab.get("frame", 0))
	if prefab.get("initial_state") != null:
		become(node, str(prefab["initial_state"]))


static func take_damage(node: Node, amount: int) -> void:
	if node._dead:
		return
	node.health -= amount
	if node.health > 0:
		if node.on_damage != "" and P.has_method(node.on_damage):
			P.call(node.on_damage, node, null)
		return
	node._dead = true
	if node.on_death != "" and P.has_method(node.on_death):
		P.call(node.on_death, node, null)
	var scene: Node = node.get_parent()
	if scene != null and scene.has_method("q_thing_died"):
		scene.q_thing_died(node)
	node.quantum_destroy()


static func become(node: Node, name_: String) -> void:
	if not node.states.has(name_):
		return
	node.state = name_
	var sprite: Node = node.get_node_or_null("Sprite")
	if sprite is Sprite2D:
		var f = node.states[name_].get("frame")
		sprite.frame = int(f) if f != null else node.base_frame   # a state without frame= keeps its own
