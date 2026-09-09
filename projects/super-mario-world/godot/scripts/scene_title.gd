extends Node2D

func _ready():
	SceneManager.current_scene_name = "title"
	QuantumBridge.register_sprite("title-bg", $"title-bg")

	# Event listeners
	QuantumEventBus.listen("press-start", Callable(self, "_on_press_start"))


func _on_press_start(_data = null):
	SceneManager.transition_to("world-map", "fade", 0.5, {})
