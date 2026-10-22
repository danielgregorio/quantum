extends CanvasLayer
# qg:camera player=: one view per player. On one machine the screen splits,
# side by side for two, in quarters for three or four (the fourth corner dark
# with three), each view with its camera over the same scene. Over the network
# each machine shows its own player's view, the whole screen; the others' run
# unseen, so what is on the screen (qg:on-screen-exit: on some player's view)
# is the same on every machine. One who watches sees them all, split.
#
# The views draw the scene's world (World2D): the scene's own CanvasLayers
# (its HUD, menus, dialogues) stay over the whole screen, over the views.

const GAP := 2.0   # the dark line between two views

var views: Array = []   # [camera, the size of its view in screen pixels], in the order of the players
var _subviews: Array = []


# The cameras of the players who play (a camera that follows no one present
# is not made); on this machine, `mine` is the seat (0: one machine for all).
func build(scene: Node, cameras: Array, screen: Vector2, mine: int) -> Camera2D:
	name = "Split"
	layer = 1                 # the HUD's layer: put first among the scene's children, it is under them
	var shown: Camera2D = null
	cameras.sort_custom(func(a, b): return a.player < b.player)
	var own := cameras.filter(func(c): return c.player == mine)
	if mine > 0 and not own.is_empty():
		# over the network: every view is a whole screen; this machine shows its own
		for cam in cameras:
			scene.add_child(cam)
			views.append([cam, screen])
		shown = own[0]
	else:
		var rects := layout(cameras.size(), screen)
		var dark := ColorRect.new()
		dark.color = Color(0.04, 0.04, 0.06)
		dark.size = screen
		dark.mouse_filter = Control.MOUSE_FILTER_IGNORE
		add_child(dark)
		for i in cameras.size():
			var r: Rect2 = rects[i]
			var box := SubViewportContainer.new()
			box.position = r.position
			box.size = r.size
			box.stretch = true
			box.mouse_filter = Control.MOUSE_FILTER_IGNORE
			var view := SubViewport.new()
			view.size = Vector2i(r.size)
			view.handle_input_locally = false
			view.gui_disable_input = true
			view.add_child(cameras[i])
			box.add_child(view)
			add_child(box)
			_subviews.append(view)
			views.append([cameras[i], r.size])
		shown = cameras[0]
	scene.add_child(self)
	scene.move_child(self, 0)   # under the scene's HUD, menus and dialogues
	return shown


# In the tree: each view shows the scene's world, drawn as the screen draws it.
func _ready() -> void:
	var screen := get_viewport()
	for i in _subviews.size():
		var view: SubViewport = _subviews[i]
		view.world_2d = screen.world_2d   # the scene, seen again through this view's camera
		view.canvas_item_default_texture_filter = screen.canvas_item_default_texture_filter
		view.snap_2d_transforms_to_pixel = screen.snap_2d_transforms_to_pixel
		(views[i][0] as Camera2D).make_current()


# Where each of n views is on the screen: one, the whole of it; two, side by
# side; three or four, the quarters.
static func layout(n: int, screen: Vector2) -> Array:
	if n <= 1:
		return [Rect2(Vector2.ZERO, screen)]
	if n == 2:
		var w := floorf((screen.x - GAP) / 2.0)
		return [Rect2(0, 0, w, screen.y), Rect2(screen.x - w, 0, w, screen.y)]
	var qw := floorf((screen.x - GAP) / 2.0)
	var qh := floorf((screen.y - GAP) / 2.0)
	var out := []
	for i in n:
		out.append(Rect2(0.0 if i % 2 == 0 else screen.x - qw, 0.0 if i < 2 else screen.y - qh, qw, qh))
	return out
