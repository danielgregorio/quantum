extends "res://addons/quantum/grid_body.gd"
# The pointer controller (qg:character controller="pointer"): a grid walker
# that its player's click also moves. The click (its "click" action, where
# its qg:cursor is) chooses a cell, and it walks there a cell at a time by
# the shortest way over the cells no wall and no thing closes (right, down,
# left, up, in that order, on a tie), pushing nothing on the way. A click on
# a thing walks up to it and steps into it once: someone is talked to, a
# door tried. A pushable one (a crate) is pushed by a click only when it is
# next to the walker, away from it; further off, the walk ends beside it.
# A key held takes over.
# The click and the cursor travel with the input, so a replay and every peer
# walk the same way.

var _route: Array = []   # the cells still to walk to, the next first


func _wanted() -> Vector2i:
	var keys := super._wanted()
	if keys != Vector2i.ZERO:
		_route.clear()
		return keys
	if Q.tapped(_a("click")) and Q.cursors.has(player):
		var at: Vector2 = Q.cursors[player]
		var to := _cell_at(at)
		_route = _way(cell(), to)
		var thing := _thing_in(to)
		if thing != null and thing.get("pushable") == true and _route.size() > 1:
			_route.pop_back()   # beside it: the next click pushes it, which way is then plain
		Q.event("route", {"who": String(name), "cells": _route.size()})
	while not _route.is_empty() and _route[0] == cell():
		_route.pop_front()
	if _route.is_empty():
		return Vector2i.ZERO
	var next: Vector2i = _route[0]
	if _wall(next):
		_route.clear()   # something came in the way: it stops
		return Vector2i.ZERO
	if _thing_in(next) != null:
		var last := _route.size() == 1
		_route.clear()   # the thing clicked: stepped into once; any other in the way stops it
		_routed = last
		return next - cell() if last else Vector2i.ZERO
	_routed = true
	return next - cell()


func _way(from: Vector2i, to: Vector2i) -> Array:
	if from == to or _wall(to):
		return []
	var map := _map()
	if map != null and (map.shape != "square" or map.has_costs()):
		# a map of hexes, or of costs: the cheapest way (qg:tile cost=), round the things on it
		var way: Array = map.path(from, to, 4096, _things_cells())
		if not way.is_empty():
			way.pop_front()
		return way
	var came := {from: from}
	var todo := [from]
	var steps := [Vector2i.RIGHT, Vector2i.DOWN, Vector2i.LEFT, Vector2i.UP]
	while not todo.is_empty():
		var c: Vector2i = todo.pop_front()
		if c == to:
			break
		for d in steps:
			var n: Vector2i = c + d
			if came.has(n) or _wall(n) or (n != to and _thing_in(n) != null):
				continue
			came[n] = c
			todo.append(n)
	if not came.has(to):
		return []
	var way := []
	var c: Vector2i = to
	while c != from:
		way.push_front(c)
		c = came[c]
	return way


# The cells things stand in (a walk goes round them, but to the one clicked).
func _things_cells() -> Dictionary:
	var out := {}
	for n in get_tree().get_nodes_in_group("q_thing"):
		if n.get_parent() == _scene and not n.is_queued_for_deletion() and n != self and not n.has_meta("q_carrier"):
			out[_cell_at(n.position)] = true
	return out
