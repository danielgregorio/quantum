
function toggleSource() {
  var modal = document.getElementById('qg-source-modal');
  modal.classList.toggle('visible');
}
document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') {
    document.getElementById('qg-source-modal').classList.remove('visible');
  }
});
(async function() {

  // === PIXI APP ===
  const app = new PIXI.Application();
  await app.init({ width: 256, height: 144, background: "#5C94FC" });
  document.body.appendChild(app.canvas);
  // World size: 256x144, Viewport: 256x144

  // === MATTER.JS ENGINE ===
  const mEngine = Matter.Engine.create();
  mEngine.gravity.x = 0;
  mEngine.gravity.y = 0.8;
  // Increase solver iterations for tighter collision resolution
  mEngine.positionIterations = 10;
  mEngine.velocityIterations = 8;
  const mWorld = mEngine.world;

  // === EVENT BUS ===
  // Event Bus
  const _gameEvents = { _listeners: {} };
  _gameEvents.on = function(event, cb) {
    if (!this._listeners[event]) {
      this._listeners[event] = [];
    }
    this._listeners[event].push(cb);
  };
  _gameEvents.off = function(event, cb) {
    if (this._listeners[event]) {
      this._listeners[event] = this._listeners[event].filter(fn => fn !== cb);
    }
  };
  _gameEvents.emit = function(event, data) {
    if (this._listeners[event]) {
      for (const cb of this._listeners[event]) {
        cb(data);
      }
    }
  };

  // === GAME STATE ===
  let coins = 0;
  let isBig = 0;

  // === ASSET LOADING ===
  await PIXI.Assets.load(["assets/smw/sprites/coin_animated.png", "assets/smw/sprites/mario_big.png", "assets/smw/sprites/mario_small.png", "assets/smw/sprites/mushroom.png", "assets/smw/sprites/qblock_animated.png", "assets/smw/sprites/qblock_used.png", "assets/smw/sprites/stage1_unique.png"]);

  // === ANIMATION SYSTEM ===
  // Animation System
  const _animatedSprites = {};

  function _parseFrames(spec) {
    if (spec.includes('-')) {
      const parts = spec.split('-').map(Number);
      const result = [];
      for (let i = parts[0]; i <= parts[1]; i += 1) {
        result.push(i);
      }
      return result;
    }
    return spec.split(',').map(s => parseInt(s.trim(), 10));
  }

  function _registerAnimation(spriteId, texture, frameW, frameH, anims) {
    if (!texture || !frameW || !frameH) {
      return;
    }
    // PIXI v8: get texture source and dimensions
    const baseTexture = texture.source || texture.baseTexture || texture;
    const texW = texture.width || baseTexture.width || (texture.frame && texture.frame.width) || 0;
    const texH = texture.height || baseTexture.height || (texture.frame && texture.frame.height) || 0;
    if (!texW || !texH) {
      console.warn('Animation failed for', spriteId, '- texture dimensions not found');
      return;
    }
    const cols = Math.floor(texW / frameW);
    const rows = Math.floor(texH / frameH);
    const totalFrames = cols * rows;

    // Build frame textures
    const frameTextures = [];
    for (let i = 0; i <= totalFrames - 1; i += 1) {
      const fx = i % cols;
      const fy = Math.floor(i / cols);
      const rect = new PIXI.Rectangle(fx * frameW, fy * frameH, frameW, frameH);
      const frameTex = new PIXI.Texture({ source: baseTexture, frame: rect });
      frameTextures.push(frameTex);
    }

    // Parse named animations
    const animDefs = {};
    let defaultAnim = null;
    for (const [name, cfg] of Object.entries(anims)) {
      const frames = _parseFrames(cfg.frames);
      const textures = frames.filter(f => f < frameTextures.length).map(f => frameTextures[f]);
      if (textures.length > 0) {
        animDefs[name] = { textures: textures, speed: cfg.speed || 0.1, loop: cfg.loop !== false };
        if (cfg.autoPlay) {
          defaultAnim = name;
        }
      }
    }

    if (Object.keys(animDefs).length === 0) {
      return;
    }

    if (!defaultAnim) {
      defaultAnim = Object.keys(animDefs)[0];
    }

    // Create animated sprite
    const firstAnim = animDefs[defaultAnim];
    const animSprite = new PIXI.AnimatedSprite(firstAnim.textures);
    animSprite.animationSpeed = firstAnim.speed;
    if (firstAnim.loop !== false) {
      animSprite.loop = true;
    }
    animSprite.play();

    // Copy transform from static sprite
    const info = _sprites[spriteId];
    if (info) {
      const oldSprite = info.sprite;
      animSprite.x = oldSprite.x;
      animSprite.y = oldSprite.y;
      animSprite.anchor.x = oldSprite.anchor ? oldSprite.anchor.x : 0.5;
      animSprite.anchor.y = oldSprite.anchor ? oldSprite.anchor.y : 0.5;
      animSprite.alpha = oldSprite.alpha;
      animSprite.visible = oldSprite.visible;

      // Replace in container
      const parent = oldSprite.parent;
      if (parent) {
        const idx = parent.getChildIndex(oldSprite);
        parent.removeChild(oldSprite);
        parent.addChildAt(animSprite, idx);
      }
      info.sprite = animSprite;
      _animatedSprites[spriteId] = { anims: animDefs, current: defaultAnim, sprite: animSprite };
    }
  }

  function _switchAnimation(spriteId, animName) {
    const entry = _animatedSprites[spriteId];
    if (!entry || entry.current === animName || !entry.anims[animName]) {
      return;
    }
    const anim = entry.anims[animName];
    entry.sprite.textures = anim.textures;
    entry.sprite.animationSpeed = anim.speed;
    entry.sprite.loop = anim.loop !== false;
    entry.sprite.gotoAndPlay(0);
    entry.current = animName;
  }

  function _updateAnimatedSprites(ticker) {
    for (const [spriteId, entry] of Object.entries(_animatedSprites)) {
      if (entry.sprite && entry.sprite.playing) {
        // PIXI v8: manually update animation using deltaMS
        entry.sprite.update(ticker);
      }
    }
  }

  function _updateControlAnimations() {
    for (const [spriteId, ctrl] of Object.entries(_controlledSprites)) {
      const entry = _animatedSprites[spriteId];
      if (!entry) {
        continue;
      }
      const info = _sprites[spriteId];
      if (!info || !info.body) {
        continue;
      }
      const vx = Math.abs(info.body.velocity.x);
      const vy = info.body.velocity.y;

      // Priority: jump > walk > idle
      if (Math.abs(vy) > 5 && entry.anims['jump']) {
        _switchAnimation(spriteId, 'jump');
      } else if (vx > 0.1 && _keys[ctrl.right] && entry.anims['walk-right']) {
        _switchAnimation(spriteId, 'walk-right');
      } else if (vx > 0.1 && _keys[ctrl.left] && entry.anims['walk-left']) {
        _switchAnimation(spriteId, 'walk-left');
      } else if (vx > 0.1 && (entry.anims['walk'] || entry.anims['walk-right'])) {
        _switchAnimation(spriteId, entry.anims['walk'] ? 'walk' : 'walk-right');
      } else if (entry.anims['idle']) {
        _switchAnimation(spriteId, 'idle');
      }
    }
  }

  // === BEHAVIORS ===
  // no behaviors

  // === CAMERA ===
  const _cameraContainer = new PIXI.Container();
  app.stage.addChild(_cameraContainer);
  function updateCamera() {
  }

  // === VISUAL TILEMAPS ===
  const _tileData_level_terrain = [[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],[9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9],[14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14],[14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14]];
  const _tileset_level = PIXI.Assets.get("assets/smw/sprites/stage1_unique.png");
  const _tsSource_level = _tileset_level.source || _tileset_level.baseTexture || _tileset_level;
  const _tsCols_level = Math.floor((_tsSource_level.width || _tileset_level.width || 256) / 16);
  // Create tiles for layer terrain
  function _getTileTex_level(tileId) {
    const col = tileId % _tsCols_level;
    const row = Math.floor(tileId / _tsCols_level);
    const rect = new PIXI.Rectangle(col * 16, row * 16, 16, 16);
    return new PIXI.Texture({ source: _tsSource_level, frame: rect });
  }
  for (let _ty = 0; _ty <= _tileData_level_terrain.length - 1; _ty += 1) {
    for (let _tx = 0; _tx <= _tileData_level_terrain[_ty].length - 1; _tx += 1) {
      const _tileId = _tileData_level_terrain[_ty][_tx];
      if (_tileId > 0) {
        const _tileSpr = new PIXI.Sprite(_getTileTex_level(_tileId));
        _tileSpr.x = _tx * 16;
        _tileSpr.y = _ty * 16;
        _cameraContainer.addChild(_tileSpr);
      }
    }
  }


  // === SPRITES & BODIES ===
  const _sprites = {};
  const _bodyToSprite = {};
  const _spr__preload_used = PIXI.Sprite.from("assets/smw/sprites/qblock_used.png");
  _spr__preload_used.x = -100;
  _spr__preload_used.y = -100;
  _spr__preload_used.anchor.set(0.5, 0.5);
  _spr__preload_used.width = 16;
  _spr__preload_used.height = 16;
  _spr__preload_used.visible = false;
  _cameraContainer.addChild(_spr__preload_used);
  _sprites["_preload_used"] = { id: "_preload_used", sprite: _spr__preload_used, body: null, tag: null, collisionHandlers: [], behaviors: [] };

  const _spr__preload_mushroom = PIXI.Sprite.from("assets/smw/sprites/mushroom.png");
  _spr__preload_mushroom.x = -100;
  _spr__preload_mushroom.y = -100;
  _spr__preload_mushroom.anchor.set(0.5, 0.5);
  _spr__preload_mushroom.width = 16;
  _spr__preload_mushroom.height = 16;
  _spr__preload_mushroom.visible = false;
  _cameraContainer.addChild(_spr__preload_mushroom);
  _sprites["_preload_mushroom"] = { id: "_preload_mushroom", sprite: _spr__preload_mushroom, body: null, tag: null, collisionHandlers: [], behaviors: [] };

  const _spr__preload_big = PIXI.Sprite.from("assets/smw/sprites/mario_big.png");
  _spr__preload_big.x = -100;
  _spr__preload_big.y = -100;
  _spr__preload_big.anchor.set(0.5, 0.5);
  _spr__preload_big.width = 16;
  _spr__preload_big.height = 32;
  _spr__preload_big.visible = false;
  _cameraContainer.addChild(_spr__preload_big);
  _sprites["_preload_big"] = { id: "_preload_big", sprite: _spr__preload_big, body: null, tag: null, collisionHandlers: [], behaviors: [] };

  const _spr_tile_level_6_0 = new PIXI.Graphics();
  _spr_tile_level_6_0.rect(-128.0, -8.0, 256, 16);
  _spr_tile_level_6_0.fill({ color: 0x4a9eff });
  _spr_tile_level_6_0.x = 128;
  _spr_tile_level_6_0.y = 104;
  _spr_tile_level_6_0.alpha = 0;
  _spr_tile_level_6_0.visible = false;
  _cameraContainer.addChild(_spr_tile_level_6_0);
  const _body_tile_level_6_0 = Matter.Bodies.rectangle(128, 104, 256, 16, { isStatic: true, restitution: 0, friction: 1, slop: 0.01 });
  _bodyToSprite[_body_tile_level_6_0.id] = "tile_level_6_0";
  _sprites["tile_level_6_0"] = { id: "tile_level_6_0", sprite: _spr_tile_level_6_0, body: _body_tile_level_6_0, tag: "tilemap-collision", collisionHandlers: [], behaviors: [] };

  const _spr_tile_level_7_0 = new PIXI.Graphics();
  _spr_tile_level_7_0.rect(-128.0, -8.0, 256, 16);
  _spr_tile_level_7_0.fill({ color: 0x4a9eff });
  _spr_tile_level_7_0.x = 128;
  _spr_tile_level_7_0.y = 120;
  _spr_tile_level_7_0.alpha = 0;
  _spr_tile_level_7_0.visible = false;
  _cameraContainer.addChild(_spr_tile_level_7_0);
  const _body_tile_level_7_0 = Matter.Bodies.rectangle(128, 120, 256, 16, { isStatic: true, restitution: 0, friction: 1, slop: 0.01 });
  _bodyToSprite[_body_tile_level_7_0.id] = "tile_level_7_0";
  _sprites["tile_level_7_0"] = { id: "tile_level_7_0", sprite: _spr_tile_level_7_0, body: _body_tile_level_7_0, tag: "tilemap-collision", collisionHandlers: [], behaviors: [] };

  const _spr_tile_level_8_0 = new PIXI.Graphics();
  _spr_tile_level_8_0.rect(-128.0, -8.0, 256, 16);
  _spr_tile_level_8_0.fill({ color: 0x4a9eff });
  _spr_tile_level_8_0.x = 128;
  _spr_tile_level_8_0.y = 136;
  _spr_tile_level_8_0.alpha = 0;
  _spr_tile_level_8_0.visible = false;
  _cameraContainer.addChild(_spr_tile_level_8_0);
  const _body_tile_level_8_0 = Matter.Bodies.rectangle(128, 136, 256, 16, { isStatic: true, restitution: 0, friction: 1, slop: 0.01 });
  _bodyToSprite[_body_tile_level_8_0.id] = "tile_level_8_0";
  _sprites["tile_level_8_0"] = { id: "tile_level_8_0", sprite: _spr_tile_level_8_0, body: _body_tile_level_8_0, tag: "tilemap-collision", collisionHandlers: [], behaviors: [] };

  const _qblock1_baseTex = PIXI.Assets.get("assets/smw/sprites/qblock_animated.png");
  const _qblock1_src = _qblock1_baseTex.source || _qblock1_baseTex.baseTexture || _qblock1_baseTex;
  const _qblock1_rect = new PIXI.Rectangle(0, 0, 16, 16);
  const _qblock1_frameTex = new PIXI.Texture({ source: _qblock1_src, frame: _qblock1_rect });
  const _spr_qblock1 = new PIXI.Sprite(_qblock1_frameTex);
  _spr_qblock1.x = 128;
  _spr_qblock1.y = 48;
  _spr_qblock1.anchor.set(0.5, 0.5);
  _cameraContainer.addChild(_spr_qblock1);
  const _body_qblock1 = Matter.Bodies.rectangle(128, 48, 16, 16, { isStatic: true, restitution: 0.1, friction: 0.1, slop: 0.01 });
  _bodyToSprite[_body_qblock1.id] = "qblock1";
  _sprites["qblock1"] = { id: "qblock1", sprite: _spr_qblock1, body: _body_qblock1, tag: "qblock", collisionHandlers: [], behaviors: [] };

  const _coin_1_baseTex = PIXI.Assets.get("assets/smw/sprites/coin_animated.png");
  const _coin_1_src = _coin_1_baseTex.source || _coin_1_baseTex.baseTexture || _coin_1_baseTex;
  const _coin_1_rect = new PIXI.Rectangle(0, 0, 16, 16);
  const _coin_1_frameTex = new PIXI.Texture({ source: _coin_1_src, frame: _coin_1_rect });
  const _spr_coin_1 = new PIXI.Sprite(_coin_1_frameTex);
  _spr_coin_1.x = 64;
  _spr_coin_1.y = 56;
  _spr_coin_1.anchor.set(0.5, 0.5);
  _cameraContainer.addChild(_spr_coin_1);
  const _body_coin_1 = Matter.Bodies.rectangle(64, 56, 16, 16, { isStatic: true, restitution: 0.1, friction: 0.1, slop: 0.01, isSensor: true });
  _bodyToSprite[_body_coin_1.id] = "coin_1";
  _sprites["coin_1"] = { id: "coin_1", sprite: _spr_coin_1, body: _body_coin_1, tag: "coin", collisionHandlers: [], behaviors: [] };

  const _coin_2_baseTex = PIXI.Assets.get("assets/smw/sprites/coin_animated.png");
  const _coin_2_src = _coin_2_baseTex.source || _coin_2_baseTex.baseTexture || _coin_2_baseTex;
  const _coin_2_rect = new PIXI.Rectangle(0, 0, 16, 16);
  const _coin_2_frameTex = new PIXI.Texture({ source: _coin_2_src, frame: _coin_2_rect });
  const _spr_coin_2 = new PIXI.Sprite(_coin_2_frameTex);
  _spr_coin_2.x = 192;
  _spr_coin_2.y = 56;
  _spr_coin_2.anchor.set(0.5, 0.5);
  _cameraContainer.addChild(_spr_coin_2);
  const _body_coin_2 = Matter.Bodies.rectangle(192, 56, 16, 16, { isStatic: true, restitution: 0.1, friction: 0.1, slop: 0.01, isSensor: true });
  _bodyToSprite[_body_coin_2.id] = "coin_2";
  _sprites["coin_2"] = { id: "coin_2", sprite: _spr_coin_2, body: _body_coin_2, tag: "coin", collisionHandlers: [], behaviors: [] };

  const _mario_baseTex = PIXI.Assets.get("assets/smw/sprites/mario_small.png");
  const _mario_src = _mario_baseTex.source || _mario_baseTex.baseTexture || _mario_baseTex;
  const _mario_rect = new PIXI.Rectangle(0, 0, 16, 24);
  const _mario_frameTex = new PIXI.Texture({ source: _mario_src, frame: _mario_rect });
  const _spr_mario = new PIXI.Sprite(_mario_frameTex);
  _spr_mario.x = 32;
  _spr_mario.y = 60;
  _spr_mario.anchor.set(0.5, 0.5);
  _cameraContainer.addChild(_spr_mario);
  const _body_mario = Matter.Bodies.rectangle(32, 60, 16, 24, { isStatic: false, restitution: 0.1, friction: 0, slop: 0.01, inertia: Infinity, chamfer: { radius: 3 } });
  _bodyToSprite[_body_mario.id] = "mario";
  _sprites["mario"] = { id: "mario", sprite: _spr_mario, body: _body_mario, tag: "player", collisionHandlers: [], behaviors: [] };

  Matter.Composite.add(mWorld, [_body_tile_level_6_0, _body_tile_level_7_0, _body_tile_level_8_0, _body_qblock1, _body_coin_1, _body_coin_2, _body_mario]);

  function syncPhysics() {
    for (const [id, info] of Object.entries(_sprites)) {
      if (info.body && !info.body.isStatic) {
        info.sprite.x = info.body.position.x;
        info.sprite.y = info.body.position.y;
        info.sprite.rotation = info.body.angle;
      }
    }
  }

  // === GAME API ===
  // Game API
  const game = { camera: {} };

  game.destroy = function(info) {
    if (!info) {
      return;
    }
    // Find sprite id
    let spriteId = null;
    for (const [id, entry] of Object.entries(_sprites)) {
      if (entry === info || entry.sprite === info) {
        spriteId = id;
        break;
      }
    }
    if (!spriteId) {
      return;
    }
    const entry = _sprites[spriteId];
    if (entry.sprite && entry.sprite.parent) {
      entry.sprite.parent.removeChild(entry.sprite);
    }
    if (entry.body) {
      Matter.Composite.remove(mWorld, entry.body);
    }
    delete _sprites[spriteId];
  };

  game.play = function(soundId, opts) {
    if (typeof _playSound === 'function') {
      return _playSound(soundId, opts);
    }
  };

  game.stop = function(soundId) {
    if (typeof _stopSound === 'function') {
      _stopSound(soundId);
    }
  };

  game.emit = function(info, event) {
    _gameEvents.emit(event, info);
    if (info && info.tag) {
      _gameEvents.emit(info.tag + '.' + event, info);
    }
  };

  game.loadScene = function(name) {
    if (typeof _loadScene === 'function') {
      _loadScene(name);
    }
  };

  game.respawn = function(id, x, y) {
    const info = _sprites[id];
    if (!info) {
      return;
    }
    if (info.sprite) {
      info.sprite.x = x;
      info.sprite.y = y;
      info.sprite.visible = true;
    }
    if (info.body) {
      Matter.Body.setPosition(info.body, { x: x, y: y });
      Matter.Body.setVelocity(info.body, { x: 0, y: 0 });
    }
  };

  game.destroyGroup = function(groupName) {
    const toRemove = [];
    for (const [id, info] of Object.entries(_sprites)) {
      if (info.group === groupName) {
        toRemove.push(info);
      }
    }
    for (const info of toRemove) {
      game.destroy(info);
    }
  };

  game.moveX = function(info, dx) {
    if (info && info.body) {
      Matter.Body.setVelocity(info.body, { x: dx, y: info.body.velocity.y });
    }
  };

  game.moveToward = function(info, targetId, speed) {
    if (!info || !info.body) {
      return;
    }
    const target = _sprites[targetId];
    if (!target) {
      return;
    }
    const dx = target.sprite.x - info.sprite.x;
    const dy = target.sprite.y - info.sprite.y;
    const dist = Math.sqrt(dx * dx + dy * dy);
    if (dist < 1) {
      return;
    }
    Matter.Body.setVelocity(info.body, { x: (dx / dist) * speed, y: (dy / dist) * speed });
  };

  game.patrol = function(info, speed) {
    game.moveX(info, speed);
  };

  game.camera.shake = function(intensity, duration) {
    let _shakeFrames = Math.floor((duration || 0.3) * 60);
    const _shakeIntensity = intensity || 5;
    const origX = _cameraContainer.x;
    const origY = _cameraContainer.y;
    const _shakeTick = () => {
      if (_shakeFrames <= 0) {
        _cameraContainer.x = origX;
        _cameraContainer.y = origY;
        return;
      }
      _cameraContainer.x = origX + (Math.random() - 0.5) * _shakeIntensity * 2;
      _cameraContainer.y = origY + (Math.random() - 0.5) * _shakeIntensity * 2;
      _shakeFrames--;
      requestAnimationFrame(_shakeTick);
    };
    _shakeTick();
  };

  game.spawn = function(id) {
    if (typeof _spawn === 'function') {
      _spawn(id);
    }
  };

  game.hitBlock = function(blockInfo, usedTextureSrc, coinTextureSrc, frameW, frameH) {
    if (!blockInfo || blockInfo._blockUsed) {
      return;
    }
    blockInfo._blockUsed = true;

    // Change block texture to used
    if (blockInfo.sprite && usedTextureSrc) {
      const usedTex = PIXI.Assets.get(usedTextureSrc);
      if (usedTex) {
        // Stop animation if playing
        if (blockInfo.sprite.stop) {
          blockInfo.sprite.stop();
        }
        // Get first frame of used texture
        const fw = frameW || 16;
        const fh = frameH || 16;
        const src = usedTex.source || usedTex.baseTexture || usedTex;
        const rect = new PIXI.Rectangle(0, 0, fw, fh);
        const frameTex = new PIXI.Texture({ source: src, frame: rect });
        // Replace with static sprite
        const newSprite = new PIXI.Sprite(frameTex);
        newSprite.anchor.set(0.5);
        newSprite.x = blockInfo.sprite.x;
        newSprite.y = blockInfo.sprite.y;
        const parent = blockInfo.sprite.parent;
        if (parent) {
          parent.removeChild(blockInfo.sprite);
          parent.addChild(newSprite);
        }
        blockInfo.sprite = newSprite;
      }
    }

    // Spawn coin effect above block
    if (coinTextureSrc) {
      const coinTex = PIXI.Assets.get(coinTextureSrc);
      if (coinTex) {
        const cfw = frameW || 16;
        const cfh = frameH || 16;
        const csrc = coinTex.source || coinTex.baseTexture || coinTex;
        // Create animated coin with 4 frames
        const coinFrames = [];
        for (let i = 0; i < 4; i++) {
          const crect = new PIXI.Rectangle(i * cfw, 0, cfw, cfh);
          coinFrames.push(new PIXI.Texture({ source: csrc, frame: crect }));
        }
        const coinSprite = new PIXI.AnimatedSprite(coinFrames);
        coinSprite.anchor.set(0.5);
        coinSprite.x = blockInfo.sprite.x;
        coinSprite.y = blockInfo.sprite.y - 20;
        coinSprite.animationSpeed = 0.15;
        coinSprite.play();
        _cameraContainer.addChild(coinSprite);

        // Animate coin going up and fading
        let coinY = coinSprite.y;
        let coinFrame = 0;
        const coinAnim = () => {;
          coinFrame++;
          coinY = coinY - 2;
          coinSprite.y = coinY;
          coinSprite.alpha = 1 - (coinFrame / 30);
          if (coinFrame < 30) {
            requestAnimationFrame(coinAnim);
          } else {
            coinSprite.destroy();
          }
        };
        coinAnim();
      }
    }
  };

  game.spawnPowerUp = function(blockInfo, textureSrc, moveSpeed) {
    if (!blockInfo || !blockInfo.sprite) {
      return;
    }
    const tex = PIXI.Assets.get(textureSrc);
    if (!tex) {
      console.warn('PowerUp texture not loaded:', textureSrc);
      return;
    }

    // Create mushroom sprite
    const mushSprite = new PIXI.Sprite(tex);
    mushSprite.anchor.set(0.5);
    mushSprite.x = blockInfo.sprite.x;
    mushSprite.y = blockInfo.sprite.y - 16;
    _cameraContainer.addChild(mushSprite);

    // Create physics body for mushroom
    const mushBody = Matter.Bodies.rectangle(mushSprite.x, mushSprite.y, 14, 14, { friction: 0, frictionAir: 0, restitution: 0, label: 'mushroom' });
    Matter.Composite.add(mWorld, mushBody);

    // Register mushroom in sprites
    const mushId = 'powerup_' + Date.now();
    const mushInfo = { id: mushId, sprite: mushSprite, body: mushBody, tag: "powerup", _isPowerUp: true };
    _sprites[mushId] = mushInfo;
    _bodyToSprite[mushBody.id] = mushId;

    // Start mushroom rising animation then walking
    let riseFrames = 0;
    const spd = moveSpeed || 1.5;
    const riseAnim = () => {;
      riseFrames++;
      if (riseFrames < 16) {
        // Rising from block
        mushSprite.y = mushSprite.y - 1;
        Matter.Body.setPosition(mushBody, { x: mushSprite.x, y: mushSprite.y });
        requestAnimationFrame(riseAnim);
      } else {
        // Start walking
        Matter.Body.setVelocity(mushBody, { x: spd, y: 0 });
      }
    };
    riseAnim();
  };

  game.powerUpPlayer = function(playerId, bigSpriteSrc, frameW, frameH) {
    const playerInfo = _sprites[playerId];
    if (!playerInfo || playerInfo._isBig) {
      return;
    }
    playerInfo._isBig = true;

    const bigTex = PIXI.Assets.get(bigSpriteSrc);
    if (!bigTex) {
      console.warn('Big sprite not loaded:', bigSpriteSrc);
      return;
    }

    // Create new animated sprite with big frames
    const fw = frameW || 16;
    const fh = frameH || 32;
    const src = bigTex.source || bigTex.baseTexture || bigTex;
    const frames = [];
    // Extract 5 frames: idle, walk1, walk2, walk3, jump
    for (let i = 0; i < 5; i++) {
      const rect = new PIXI.Rectangle(i * fw, 0, fw, fh);
      frames.push(new PIXI.Texture({ source: src, frame: rect }));
    }

    const bigSprite = new PIXI.AnimatedSprite(frames);
    bigSprite.anchor.set(0.5);
    bigSprite.x = playerInfo.sprite.x;
    bigSprite.y = playerInfo.sprite.y - 4;
    bigSprite.scale.x = playerInfo.sprite.scale.x;
    bigSprite.animationSpeed = 0.15;
    bigSprite.play();

    // Replace sprite
    const parent = playerInfo.sprite.parent;
    if (parent) {
      parent.removeChild(playerInfo.sprite);
      parent.addChild(bigSprite);
    }
    playerInfo.sprite = bigSprite;

    // Update physics body size
    if (playerInfo.body) {
      const pos = playerInfo.body.position;
      Matter.Composite.remove(mWorld, playerInfo.body);
      const newBody = Matter.Bodies.rectangle(pos.x, pos.y - 4, 14, 30, { friction: 0, frictionAir: 0, inertia: Infinity, label: 'player' });
      Matter.Composite.add(mWorld, newBody);
      delete _bodyToSprite[playerInfo.body.id];
      playerInfo.body = newBody;
      _bodyToSprite[newBody.id] = playerId;
    }

    // Register animations for big Mario
    playerInfo.anims = { idle: bigSprite, walk: bigSprite, jump: bigSprite };
  };

  // === BEHAVIOR ATTACHMENTS ===
  _sprites["mario"].collisionHandlers.push((self, other) => {
    if (other.tag !== "coin") return;
    _gameEvents.emit("coin-collected", { self, other });
  });
  _sprites["mario"].collisionHandlers.push((self, other) => {
    if (other.tag !== "coin") return;
    if (other._destroyed) return;
    other._destroyed = true;
    if (other.body) { delete _bodyToSprite[other.body.id]; Matter.Composite.remove(mEngine.world, other.body); }
    if (other.sprite) { if (other.sprite.stop) other.sprite.stop(); other.sprite.destroy(); }
    if (other.id) delete _sprites[other.id];
  });
  _sprites["mario"].collisionHandlers.push((self, other) => {
    if (other.tag !== "qblock") return;
    _gameEvents.emit("block-hit", { self, other });
  });
  _sprites["mario"].collisionHandlers.push((self, other) => {
    if (other.tag !== "powerup") return;
    _gameEvents.emit("powerup-collected", { self, other });
  });
  _sprites["mario"].collisionHandlers.push((self, other) => {
    if (other.tag !== "powerup") return;
    if (other._destroyed) return;
    other._destroyed = true;
    if (other.body) { delete _bodyToSprite[other.body.id]; Matter.Composite.remove(mEngine.world, other.body); }
    if (other.sprite) { if (other.sprite.stop) other.sprite.stop(); other.sprite.destroy(); }
    if (other.id) delete _sprites[other.id];
  });
  // Init state machines
  for (const [_id, _info] of Object.entries(_sprites)) {
    for (const b of _info.behaviors) {
      if (b._smInit) {
        b._smInit();
      }
    }
  }

  // === ANIMATION REGISTRATION ===
  _registerAnimation("qblock1", PIXI.Assets.get("assets/smw/sprites/qblock_animated.png"), 16, 16, { "shine": { frames: "0,1,2,3", speed: 0.15, loop: true, autoPlay: true } });
  _registerAnimation("coin_1", PIXI.Assets.get("assets/smw/sprites/coin_animated.png"), 16, 16, { "spin": { frames: "0,1,2,3,2,1", speed: 0.12, loop: true, autoPlay: true } });
  _registerAnimation("coin_2", PIXI.Assets.get("assets/smw/sprites/coin_animated.png"), 16, 16, { "spin": { frames: "0,1,2,3,2,1", speed: 0.12, loop: true, autoPlay: true } });
  _registerAnimation("mario", PIXI.Assets.get("assets/smw/sprites/mario_small.png"), 16, 24, { "idle": { frames: "0", speed: 0.1, loop: true, autoPlay: true }, "walk": { frames: "1-3", speed: 0.18, loop: true, autoPlay: false }, "jump": { frames: "4", speed: 0.1, loop: false, autoPlay: false } });

  // === INPUT ===
  const _keys = {};
  const _justPressed = {};
  window.addEventListener('keydown', (e) => {
    if (!_keys[e.key]) _justPressed[e.key] = true;
    _keys[e.key] = true;
  });
  window.addEventListener('keyup', (e) => {
    _keys[e.key] = false;
  });
  function _clearJustPressed() {
    for (const k in _justPressed) delete _justPressed[k];
  }
  const _controlledSprites = {};
  _controlledSprites["mario"] = { left: 'ArrowLeft', right: 'ArrowRight', up: 'ArrowUp', jump: 'ArrowUp', left2: 'a', right2: 'd', up2: 'w', jump2: 'w' };

  // === MOUSE ===
  // Mouse System
  let _mouseX = 0;
  let _mouseY = 0;
  let _mouseWorldX = 0;
  let _mouseWorldY = 0;
  app.canvas.addEventListener('pointermove', (e) => {
    const rect = app.canvas.getBoundingClientRect();
    _mouseX = e.clientX - rect.left;
    _mouseY = e.clientY - rect.top;
    // Convert to world coordinates (accounting for camera)
    _mouseWorldX = _mouseX - _cameraContainer.x;
    _mouseWorldY = _mouseY - _cameraContainer.y;
  });

  // === FUNCTIONS ===
  function onCoinCollected(data) {
    coins = coins + 1
    document.getElementById('coin-display').textContent = coins
  }

  function onBlockHit(data) {
    if (data.other._blockUsed) return
    game.hitBlock(data.other, 'assets/smw/sprites/qblock_used.png', null, 16, 16)
    game.spawnPowerUp(data.other, 'assets/smw/sprites/mushroom.png', 1)
  }

  function onPowerUpCollected(data) {
    if (isBig) return
    isBig = 1
    game.powerUpPlayer('mario', 'assets/smw/sprites/mario_big.png', 16, 32)
    document.getElementById('size-display').textContent = 'BIG!'
    document.getElementById('size-display').style.color = '#00FF00'
  }


  // === COLLISIONS ===
  Matter.Events.on(mEngine, 'collisionStart', (event) => {
    for (const pair of event.pairs) {
      const a = _bodyToSprite[pair.bodyA.id];
      const b = _bodyToSprite[pair.bodyB.id];
      if (a && b) {
        _handleCollision(a, b);
        _handleCollision(b, a);
      }
    }
  });

  function _handleCollision(selfId, otherId) {
    const selfInfo = _sprites[selfId];
    const otherInfo = _sprites[otherId];
    if (!selfInfo || !otherInfo) {
      return;
    }
    if (selfInfo.collisionHandlers) {
      for (const handler of selfInfo.collisionHandlers) {
        handler(selfInfo, otherInfo);
      }
    }
  }

  // === SOUNDS ===
  // No sounds

  // === PARTICLES ===
  // Particle System
  const _particleSystems = {};

  function _createParticleSystem(config) {
    const ps = {
      id: config.id,
      follow: config.follow || null,
      trigger: config.trigger || null,
      count: config.count || 20,
      emitRate: config.emitRate || 10,
      lifetime: config.lifetime || 1,
      speedMin: config.speedMin || 1,
      speedMax: config.speedMax || 3,
      angleMin: (config.angleMin || 0) * Math.PI / 180,
      angleMax: (config.angleMax || 360) * Math.PI / 180,
      alphaStart: config.alphaStart !== undefined ? config.alphaStart : 1,
      alphaEnd: config.alphaEnd !== undefined ? config.alphaEnd : 0,
      active: false,
      emitTimer: 0,
      pool: [],
      container: new PIXI.Container(),
    };

    // Pre-allocate particle pool
    for (let i = 0; i <= ps.count - 1; i += 1) {
      const p = new PIXI.Graphics();
      p.circle(0, 0, 3);
      p.fill({ color: 0xffffff });
      p.visible = false;
      p._life = 0; p._maxLife = 0; p._vx = 0; p._vy = 0;
      p._alphaStart = 1; p._alphaEnd = 0;
      ps.container.addChild(p);
      ps.pool.push(p);
    }

    _cameraContainer.addChild(ps.container);
    _particleSystems[config.id] = ps;
    return ps;
  }

  function _emitParticle(ps, x, y) {
    for (const p of ps.pool) {
      if (!p.visible) {
        p.x = x;
        p.y = y;
        const angle = ps.angleMin + Math.random() * (ps.angleMax - ps.angleMin);
        const speed = ps.speedMin + Math.random() * (ps.speedMax - ps.speedMin);
        p._vx = Math.cos(angle) * speed;
        p._vy = Math.sin(angle) * speed;
        p._life = 0;
        p._maxLife = ps.lifetime;
        p._alphaStart = ps.alphaStart;
        p._alphaEnd = ps.alphaEnd;
        p.alpha = ps.alphaStart;
        p.visible = true;
        return;
      }
    }
  }

  function _activateParticles(psId) {
    const ps = _particleSystems[psId];
    if (ps) {
      ps.active = true;
    }
  }

  function _deactivateParticles(psId) {
    const ps = _particleSystems[psId];
    if (ps) {
      ps.active = false;
    }
  }

  function _updateParticles(dt) {
    for (const [id, ps] of Object.entries(_particleSystems)) {
      // Emit new particles if active
      if (ps.active) {
        ps.emitTimer += dt / 60;
        const interval = 1 / ps.emitRate;
        while (ps.emitTimer >= interval) {
          ps.emitTimer -= interval;
          let ex = 0;
          let ey = 0;
          if (ps.follow) {
            const info = _sprites[ps.follow];
            if (info) {
              ex = info.sprite.x;
              ey = info.sprite.y;
            }
          }
          _emitParticle(ps, ex, ey);
        }
      }

      // Update living particles
      for (const p of ps.pool) {
        if (!p.visible) {
          continue;
        }
        p._life += dt / 60;
        if (p._life >= p._maxLife) {
          p.visible = false;
          continue;
        }
        const lifeT = p._life / p._maxLife;
        p.x = p.x + p._vx;
        p.y = p.y + p._vy;
        p.alpha = p._alphaStart + (p._alphaEnd - p._alphaStart) * lifeT;
      }
    }
  }
  // No particle instances

  // === TIMERS ===
  // Timer System
  const _timers = {};
  const _timerActions = {};

  function _createTimer(id, interval, repeat, autoStart, actionFn) {
    _timers[id] = { elapsed: 0, interval: interval, repeat: repeat, count: 0, active: autoStart };
    _timerActions[id] = actionFn;
  }

  function _updateTimers(dt) {
    for (const [tid, t] of Object.entries(_timers)) {
      if (!t.active) {
        continue;
      }
      t.elapsed += dt / 60;
      if (t.elapsed >= t.interval) {
        t.elapsed = 0;
        if (_timerActions[tid]) {
          _timerActions[tid]();
        }
        t.count++;
        if (t.repeat >= 0 && t.count >= t.repeat) {
          t.active = false;
        }
      }
    }
  }
  // No timer instances

  // === TWEENS ===
  // Easing Functions
  const _easing = {
    linear: t => t,
    easeIn: t => t * t,
    easeOut: t => t * (2 - t),
    easeInOut: t => t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t,
    easeInCubic: t => t * t * t,
    easeOutCubic: t => (--t) * t * t + 1,
    easeInOutCubic: t => t < 0.5 ? 4 * t * t * t : (t - 1) * (2 * t - 2) * (2 * t - 2) + 1,
    easeInQuart: t => t * t * t * t,
    easeOutQuart: t => 1 - (--t) * t * t * t,
    easeInOutQuart: t => t < 0.5 ? 8 * t * t * t * t : 1 - 8 * (--t) * t * t * t,
    easeOutBounce: t => {
      if (t < 1/2.75) return 7.5625 * t * t;
      if (t < 2/2.75) return 7.5625 * (t -= 1.5/2.75) * t + 0.75;
      if (t < 2.5/2.75) return 7.5625 * (t -= 2.25/2.75) * t + 0.9375;
      return 7.5625 * (t -= 2.625/2.75) * t + 0.984375;
    },
    easeInBounce: t => 1 - _easing.easeOutBounce(1 - t),
    easeOutElastic: t => {
      if (t === 0 || t === 1) return t;
      return Math.pow(2, -10 * t) * Math.sin((t - 0.075) * (2 * Math.PI) / 0.3) + 1;
    },
    easeInElastic: t => {
      if (t === 0 || t === 1) return t;
      return -Math.pow(2, 10 * (t - 1)) * Math.sin((t - 1.075) * (2 * Math.PI) / 0.3);
    },
  };

  const _tweens = {};
  let _tweenIdCounter = 0;

  function _createTween(config) {
    const id = config.id || ('tween_' + _tweenIdCounter++);
    _tweens[id] = {
      target: config.target,
      prop: config.prop,
      from: null,
      to: config.to,
      duration: config.duration || 1,
      easing: config.easing || 'linear',
      loop: !!config.loop,
      yoyo: !!config.yoyo,
      delay: config.delay || 0,
      elapsed: 0,
      delayElapsed: 0,
      active: config.active !== false,
      started: false,
    };
    return id;
  }

  function _updateTweens(dt) {
    for (const [tid, tw] of Object.entries(_tweens)) {
      if (!tw.active) {
        continue;
      }
      // Handle delay
      if (tw.delayElapsed < tw.delay) {
        tw.delayElapsed += dt / 60;
        continue;
      }
      // Init start value on first frame
      if (!tw.started) {
        const info = _sprites[tw.target];
        if (!info) {
          continue;
        }
        tw.from = info.sprite[tw.prop];
        tw.started = true;
      }
      tw.elapsed += dt / 60;
      const rawT = Math.min(tw.elapsed / tw.duration, 1);
      const easeFn = _easing[tw.easing] || _easing.linear;
      const t = easeFn(rawT);
      const info = _sprites[tw.target];
      if (info) {
        info.sprite[tw.prop] = tw.from + (tw.to - tw.from) * t;
      }
      if (rawT >= 1) {
        if (tw.loop) {
          tw.elapsed = 0;
          if (tw.yoyo) {
            const tmp = tw.from;
            tw.from = tw.to;
            tw.to = tmp;
          }
        } else {
          tw.active = false;
        }
      }
    }
  }
  // No tween instances

  // === SPAWNERS ===
  // No spawners

  // === HUD UPDATE ===
  const _hudElements = [];
  _hudElements.push(document.getElementById('qg-hud-0'));
  function _updateHUD() {
  }

  // === GAME LOOP ===
  app.ticker.add((ticker) => {
    const dt = ticker.deltaTime;
    // Sub-step physics with velocity clamping to prevent tunneling
    const _fixedDt = 16.67;
    const _maxSteps = 3;
    const _maxVel = 12;
    const _steps = Math.min(Math.ceil(dt), _maxSteps);
    for (let _i = 0; _i <= _steps; _i += 1) {
      // Clamp velocities BEFORE physics step
      for (const [_sid, _sinfo] of Object.entries(_sprites)) {
        if (_sinfo.body && !_sinfo.body.isStatic) {
          const _bv = _sinfo.body.velocity;
          if (Math.abs(_bv.x) > _maxVel || Math.abs(_bv.y) > _maxVel) {
            Matter.Body.setVelocity(_sinfo.body, {
              x: Math.max(-_maxVel, Math.min(_maxVel, _bv.x)),
              y: Math.max(-_maxVel, Math.min(_maxVel, _bv.y))
            });
          }
        }
      }
      Matter.Engine.update(mEngine, _fixedDt);
    }
    syncPhysics();
    // Input handling
    const _ctrl_mario = _controlledSprites["mario"];
    // Movement with dual key support (arrows + WASD)
    const _leftPressed_mario = _keys[_ctrl_mario.left] || (_keys[_ctrl_mario.left2] || false);
    const _rightPressed_mario = _keys[_ctrl_mario.right] || (_keys[_ctrl_mario.right2] || false);
    const _jumpPressed_mario = _keys[_ctrl_mario.jump] || (_keys[_ctrl_mario.jump2] || false);
    const _jumpJust_mario = _justPressed[_ctrl_mario.jump] || (_justPressed[_ctrl_mario.jump2] || false);
    if (_leftPressed_mario && _sprites["mario"].body) {
      Matter.Body.setVelocity(_sprites["mario"].body, { x: -1.5, y: _sprites["mario"].body.velocity.y });
      _sprites["mario"].sprite.scale.x = Math.abs(_sprites["mario"].sprite.scale.x);
    }
    if (_rightPressed_mario && _sprites["mario"].body) {
      Matter.Body.setVelocity(_sprites["mario"].body, { x: 1.5, y: _sprites["mario"].body.velocity.y });
      _sprites["mario"].sprite.scale.x = -Math.abs(_sprites["mario"].sprite.scale.x);
    }
    // SMW-style jump: coyote time, variable height, asymmetric gravity
    if (_sprites["mario"]._coyoteFrames === undefined) {
      _sprites["mario"]._coyoteFrames = 0;
      _sprites["mario"]._jumpHeld = false;
      _sprites["mario"]._wasGrounded = false;
    }
    const _isGrounded_mario = _sprites["mario"].body && Math.abs(_sprites["mario"].body.velocity.y) < 1.0;
    if (_isGrounded_mario) {
      _sprites["mario"]._coyoteFrames = 6;
      _sprites["mario"]._wasGrounded = true;
    } else if (_sprites["mario"]._coyoteFrames > 0) {
      _sprites["mario"]._coyoteFrames--;
    }
    const _canJump_mario = _isGrounded_mario || _sprites["mario"]._coyoteFrames > 0;
    if (_jumpJust_mario && _sprites["mario"].body && _canJump_mario) {
      Matter.Body.setVelocity(_sprites["mario"].body, { x: _sprites["mario"].body.velocity.x, y: -6 });
      _sprites["mario"]._jumpHeld = true;
      _sprites["mario"]._coyoteFrames = 0;
      _gameEvents.emit('player.jump', _sprites["mario"]);
    }
    if (_jumpPressed_mario && _sprites["mario"].body && _sprites["mario"]._jumpHeld && _sprites["mario"].body.velocity.y < 0) {
      Matter.Body.setVelocity(_sprites["mario"].body, { x: _sprites["mario"].body.velocity.x, y: _sprites["mario"].body.velocity.y - 0.4 });
    }
    if (!_jumpPressed_mario) {
      _sprites["mario"]._jumpHeld = false;
    }
    if (_sprites["mario"].body && _sprites["mario"].body.velocity.y > 15) {
      Matter.Body.setVelocity(_sprites["mario"].body, { x: _sprites["mario"].body.velocity.x, y: 15 });
    }
    if (!_leftPressed_mario && !_rightPressed_mario && _sprites["mario"].body) {
      Matter.Body.setVelocity(_sprites["mario"].body, { x: 0, y: _sprites["mario"].body.velocity.y });
      _gameEvents.emit('player.stop', _sprites["mario"]);
    } else {
      _gameEvents.emit('player.walk', _sprites["mario"]);
    }
    _clearJustPressed();
    updateCamera();
    _updateControlAnimations();
    _updateAnimatedSprites(ticker);
    // Behaviors update
    for (const [_id, _info] of Object.entries(_sprites)) {
      for (const b of _info.behaviors) {
        if (b._smUpdate) {
          b._smUpdate();
        }
        if (b.update) {
          b.update();
        }
      }
    }
    _updateHUD();
  });

  // === SCENE START ===
  // qg:event handlers
  _gameEvents.on("coin-collected", (data) => {
    if (typeof onCoinCollected === 'function') {
      onCoinCollected(data);
    }
  });
  _gameEvents.on("block-hit", (data) => {
    if (typeof onBlockHit === 'function') {
      onBlockHit(data);
    }
  });
  _gameEvents.on("powerup-collected", (data) => {
    if (typeof onPowerUpCollected === 'function') {
      onPowerUpCollected(data);
    }
  });
})();
  