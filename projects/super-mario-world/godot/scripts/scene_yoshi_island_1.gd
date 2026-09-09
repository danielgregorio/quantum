extends Node2D

# State variables
var isDead = 0
var time_left = 300

func _ready():
	SceneManager.current_scene_name = "yoshi-island-1"
	QuantumBridge.register_sprite("_preload_used", $_preload_used)
	QuantumBridge.register_sprite("_preload_death", $_preload_death)
	QuantumBridge.register_sprite("level-bg", $"level-bg")
	QuantumBridge.register_sprite("goal", $goal)
	QuantumBridge.register_sprite("mario", $mario)
	QuantumBridge.register_sprite("deathzone", $deathzone)

	# Death texture
	$mario.set_death_texture($_preload_death.texture)

	# Initialize HUD
	$HUD.update_label("lives", SceneManager.get_state("lives", 5))
	$HUD.update_label("coins", SceneManager.get_state("coins", 0))
	$HUD.update_label("score", SceneManager.get_state("score", 0))
	$HUD.update_label("yoshi_coins", SceneManager.get_state("yoshi_coins", 0))
	$HUD.set_time(300)

	# Event listeners
	QuantumEventBus.listen("coin-collected", Callable(self, "_on_coin_collected"))
	QuantumEventBus.listen("yoshi-coin-collected", Callable(self, "_on_yoshi_coin_collected"))
	QuantumEventBus.listen("block-hit", Callable(self, "_on_block_hit"))
	QuantumEventBus.listen("enemy-collision", Callable(self, "_on_enemy_collision"))
	QuantumEventBus.listen("fell-in-pit", Callable(self, "_on_fell_in_pit"))
	QuantumEventBus.listen("level-complete", Callable(self, "_on_level_complete"))
	QuantumEventBus.listen("game-over", Callable(self, "_on_game_over"))
	QuantumEventBus.listen("enemy-stomped", Callable(self, "_on_enemy_stomped"))
	QuantumEventBus.listen("mario-died", Callable(self, "_on_mario_died"))
	QuantumEventBus.listen("powerup-collected", Callable(self, "_on_powerup_collected"))
	QuantumEventBus.listen("banzai-launch", Callable(self, "_on_banzai_launch"))


	# Start background music
	_play_sound("bgm-level")

func _on_coin_collected(_data = null):
	_play_sound("sfx-coin")
	SceneManager.set_state("score", SceneManager.get_state("score", 0) + 10)
	$HUD.update_label("score", SceneManager.get_state("score", 0))
	SceneManager.set_state("coins", SceneManager.get_state("coins", 0) + 1)
	$HUD.update_label("coins", SceneManager.get_state("coins", 0))

func _on_yoshi_coin_collected(_data = null):
	SceneManager.set_state("score", SceneManager.get_state("score", 0) + 50)
	$HUD.update_label("score", SceneManager.get_state("score", 0))
	SceneManager.set_state("yoshi_coins", SceneManager.get_state("yoshi_coins", 0) + 1)
	$HUD.update_label("yoshi_coins", SceneManager.get_state("yoshi_coins", 0))

func _on_block_hit(_data = null):
	_play_sound("sfx-block")

func _on_enemy_collision(_data = null):
	if isDead: return
	var normal_y = _data.get("normal_y", 0) if _data else 0
	var other = _data.get("other") if _data else null
	if normal_y < -0.5 and other and other.has_method("stomp"):
		other.stomp()
		if $mario.has_method("stomp_bounce"):
			$mario.stomp_bounce(-200)
		else:
			$mario.velocity.y = -200
		_play_sound("sfx-stomp")
	else:
		_die()

func _on_fell_in_pit(_data = null):
	_die()

func _on_level_complete(_data = null):
	_play_sound("sfx-clear")
	SceneManager.set_state("score", SceneManager.get_state("score", 0) + 1000)
	$HUD.update_label("score", SceneManager.get_state("score", 0))
	$HUD.stop_timer()
	_stop_sound("bgm-level")
	SceneManager.transition_to("world-map", "iris-out", 1.0, {})

func _on_game_over(_data = null):
	$HUD.stop_timer()
	_stop_sound("bgm-level")
	SceneManager.transition_to("title", "fade", 1.0, {})

func _on_enemy_stomped(_data = null):
	_play_sound("sfx-stomp")

func _on_mario_died(_data = null):
	_play_sound("sfx-death")

func _on_powerup_collected(_data = null):
	_play_sound("sfx-powerup")

func _on_banzai_launch(_data = null):
	_play_sound("sfx-banzai")

func _die():
	if isDead: return
	isDead = 1
	$mario.die()
	$HUD.stop_timer()
	_play_sound("sfx-death")
	_stop_sound("bgm-level")
	await get_tree().create_timer(3.0).timeout
	var lives = SceneManager.get_state("lives", 5) - 1
	SceneManager.set_state("lives", lives)
	if lives <= 0:
		QuantumEventBus.emit_event("game-over", {})
	else:
		get_tree().reload_current_scene()

func _play_sound(id: String):
	var player = get_node_or_null("Sounds/" + id)
	if player: player.play()

func _stop_sound(id: String):
	var player = get_node_or_null("Sounds/" + id)
	if player: player.stop()
