/**
 * Effects System
 *
 * Provides visual effects and animations compatible with Adobe Flex.
 *
 * Features:
 * - Fade (opacity transitions)
 * - Move (position animations)
 * - Resize (size animations)
 * - Glow (drop shadow effects)
 * - Parallel (run effects simultaneously)
 * - Sequence (run effects in order)
 * - Effect events (start, update, end)
 *
 * @example
 * <mx:Fade id="fadeIn" alphaFrom="0" alphaTo="1" duration="500" />
 * <s:Button label="Click" mouseDown="fadeIn.play()" />
 */

/**
 * Base Effect Class
 */
export class Effect {
    constructor(target = null) {
        this.target = target;
        this.duration = 500; // milliseconds
        this.isPlaying = false;
        this.isPaused = false;
        this.startTime = 0;
        this.pauseTime = 0;

        // Event handlers
        this.effectStartHandler = null;
        this.effectUpdateHandler = null;
        this.effectEndHandler = null;

        // Animation frame ID
        this.animationId = null;
    }

    play(target = null) {
        if (target) this.target = target;
        if (!this.target) return;

        this.isPlaying = true;
        this.isPaused = false;
        this.startTime = Date.now();

        this.onStart();
        this.animate();
    }

    pause() {
        if (!this.isPlaying) return;
        this.isPaused = true;
        this.pauseTime = Date.now();
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
        }
    }

    resume() {
        if (!this.isPaused) return;
        this.isPaused = false;
        this.startTime += (Date.now() - this.pauseTime);
        this.animate();
    }

    stop() {
        this.isPlaying = false;
        this.isPaused = false;
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
        }
        this.onEnd();
    }

    reverse() {
        // Reverse the effect (swap from/to values)
    }

    animate() {
        if (!this.isPlaying || this.isPaused) return;

        const elapsed = Date.now() - this.startTime;
        const progress = Math.min(elapsed / this.duration, 1);

        this.onUpdate(progress);

        if (progress < 1) {
            this.animationId = requestAnimationFrame(() => this.animate());
        } else {
            this.stop();
        }
    }

    onStart() {
        if (this.effectStartHandler) {
            this.effectStartHandler({ type: 'effectStart', target: this.target });
        }
    }

    onUpdate(progress) {
        if (this.effectUpdateHandler) {
            this.effectUpdateHandler({ type: 'effectUpdate', progress: progress });
        }
    }

    onEnd() {
        if (this.effectEndHandler) {
            this.effectEndHandler({ type: 'effectEnd', target: this.target });
        }
    }

    // Easing functions
    easeLinear(t) {
        return t;
    }

    easeInQuad(t) {
        return t * t;
    }

    easeOutQuad(t) {
        return t * (2 - t);
    }

    easeInOutQuad(t) {
        return t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t;
    }
}

/**
 * Fade Effect
 */
export class Fade extends Effect {
    constructor(target = null) {
        super(target);
        this.alphaFrom = 1;
        this.alphaTo = 0;
    }

    onStart() {
        super.onStart();
        this.target.style.opacity = this.alphaFrom;
    }

    onUpdate(progress) {
        super.onUpdate(progress);
        const alpha = this.alphaFrom + (this.alphaTo - this.alphaFrom) * this.easeInOutQuad(progress);
        this.target.style.opacity = alpha;
    }
}

/**
 * Move Effect
 */
export class Move extends Effect {
    constructor(target = null) {
        super(target);
        this.xFrom = 0;
        this.yFrom = 0;
        this.xTo = 0;
        this.yTo = 0;
        this.xBy = null;
        this.yBy = null;
    }

    onStart() {
        super.onStart();

        // Get current position
        const rect = this.target.getBoundingClientRect();

        if (this.xBy !== null) {
            this.xFrom = rect.left;
            this.xTo = this.xFrom + this.xBy;
        }

        if (this.yBy !== null) {
            this.yFrom = rect.top;
            this.yTo = this.yFrom + this.yBy;
        }

        this.target.style.position = 'relative';
        this.target.style.left = '0px';
        this.target.style.top = '0px';
    }

    onUpdate(progress) {
        super.onUpdate(progress);

        const x = this.xFrom + (this.xTo - this.xFrom) * this.easeInOutQuad(progress);
        const y = this.yFrom + (this.yTo - this.yFrom) * this.easeInOutQuad(progress);

        this.target.style.transform = `translate(${x - this.xFrom}px, ${y - this.yFrom}px)`;
    }
}

/**
 * Resize Effect
 */
export class Resize extends Effect {
    constructor(target = null) {
        super(target);
        this.widthFrom = null;
        this.heightFrom = null;
        this.widthTo = null;
        this.heightTo = null;
        this.widthBy = null;
        this.heightBy = null;
    }

    onStart() {
        super.onStart();

        const computed = window.getComputedStyle(this.target);

        if (this.widthFrom === null) {
            this.widthFrom = parseFloat(computed.width);
        }
        if (this.heightFrom === null) {
            this.heightFrom = parseFloat(computed.height);
        }

        if (this.widthBy !== null) {
            this.widthTo = this.widthFrom + this.widthBy;
        }
        if (this.heightBy !== null) {
            this.heightTo = this.heightFrom + this.heightBy;
        }
    }

    onUpdate(progress) {
        super.onUpdate(progress);

        if (this.widthTo !== null) {
            const width = this.widthFrom + (this.widthTo - this.widthFrom) * this.easeInOutQuad(progress);
            this.target.style.width = width + 'px';
        }

        if (this.heightTo !== null) {
            const height = this.heightFrom + (this.heightTo - this.heightFrom) * this.easeInOutQuad(progress);
            this.target.style.height = height + 'px';
        }
    }
}

/**
 * Glow Effect
 */
export class Glow extends Effect {
    constructor(target = null) {
        super(target);
        this.color = '#0000FF';
        this.alphaFrom = 0;
        this.alphaTo = 1;
        this.blurXFrom = 0;
        this.blurXTo = 10;
        this.blurYFrom = 0;
        this.blurYTo = 10;
        this.strength = 2;
    }

    onUpdate(progress) {
        super.onUpdate(progress);

        const alpha = this.alphaFrom + (this.alphaTo - this.alphaFrom) * this.easeInOutQuad(progress);
        const blurX = this.blurXFrom + (this.blurXTo - this.blurXFrom) * this.easeInOutQuad(progress);
        const blurY = this.blurYFrom + (this.blurYTo - this.blurYFrom) * this.easeInOutQuad(progress);

        this.target.style.filter = `drop-shadow(0 0 ${blurX}px ${this.color})`;
        this.target.style.opacity = alpha;
    }

    onEnd() {
        super.onEnd();
        this.target.style.filter = 'none';
    }
}

/**
 * Parallel Effect (run multiple effects simultaneously)
 */
export class Parallel extends Effect {
    constructor(target = null) {
        super(target);
        this.children = [];
    }

    addChild(effect) {
        this.children.push(effect);
    }

    play(target = null) {
        if (target) this.target = target;

        this.isPlaying = true;
        this.onStart();

        // Start all child effects
        this.children.forEach(effect => {
            effect.target = this.target;
            effect.play();
        });

        // Wait for all to complete
        const maxDuration = Math.max(...this.children.map(e => e.duration));
        setTimeout(() => {
            this.stop();
        }, maxDuration);
    }
}

/**
 * Sequence Effect (run effects in order)
 */
export class Sequence extends Effect {
    constructor(target = null) {
        super(target);
        this.children = [];
        this.currentIndex = 0;
    }

    addChild(effect) {
        this.children.push(effect);
    }

    play(target = null) {
        if (target) this.target = target;

        this.isPlaying = true;
        this.currentIndex = 0;
        this.onStart();
        this.playNext();
    }

    playNext() {
        if (this.currentIndex >= this.children.length) {
            this.stop();
            return;
        }

        const effect = this.children[this.currentIndex];
        effect.target = this.target;

        // Store original end handler
        const originalEnd = effect.effectEndHandler;

        // Override end handler to play next
        effect.effectEndHandler = () => {
            if (originalEnd) originalEnd();
            this.currentIndex++;
            this.playNext();
        };

        effect.play();
    }
}

/**
 * Render effects as non-visual components
 */
export function renderFade(runtime, node) {
    const effect = new Fade();
    effect.alphaFrom = parseFloat(node.props.alphaFrom || '1');
    effect.alphaTo = parseFloat(node.props.alphaTo || '0');
    effect.duration = parseInt(node.props.duration || '500');

    // Store in runtime if has ID
    if (node.props.id) {
        runtime.app[node.props.id] = effect;
    }

    return document.createComment(`Fade Effect: ${node.props.id}`);
}

export function renderMove(runtime, node) {
    const effect = new Move();
    if (node.props.xFrom) effect.xFrom = parseFloat(node.props.xFrom);
    if (node.props.yFrom) effect.yFrom = parseFloat(node.props.yFrom);
    if (node.props.xTo) effect.xTo = parseFloat(node.props.xTo);
    if (node.props.yTo) effect.yTo = parseFloat(node.props.yTo);
    if (node.props.xBy) effect.xBy = parseFloat(node.props.xBy);
    if (node.props.yBy) effect.yBy = parseFloat(node.props.yBy);
    effect.duration = parseInt(node.props.duration || '500');

    if (node.props.id) {
        runtime.app[node.props.id] = effect;
    }

    return document.createComment(`Move Effect: ${node.props.id}`);
}

export function renderResize(runtime, node) {
    const effect = new Resize();
    if (node.props.widthFrom) effect.widthFrom = parseFloat(node.props.widthFrom);
    if (node.props.heightFrom) effect.heightFrom = parseFloat(node.props.heightFrom);
    if (node.props.widthTo) effect.widthTo = parseFloat(node.props.widthTo);
    if (node.props.heightTo) effect.heightTo = parseFloat(node.props.heightTo);
    if (node.props.widthBy) effect.widthBy = parseFloat(node.props.widthBy);
    if (node.props.heightBy) effect.heightBy = parseFloat(node.props.heightBy);
    effect.duration = parseInt(node.props.duration || '500');

    if (node.props.id) {
        runtime.app[node.props.id] = effect;
    }

    return document.createComment(`Resize Effect: ${node.props.id}`);
}

export function renderGlow(runtime, node) {
    const effect = new Glow();
    if (node.props.color) effect.color = node.props.color;
    effect.alphaFrom = parseFloat(node.props.alphaFrom || '0');
    effect.alphaTo = parseFloat(node.props.alphaTo || '1');
    effect.blurXFrom = parseFloat(node.props.blurXFrom || '0');
    effect.blurXTo = parseFloat(node.props.blurXTo || '10');
    effect.duration = parseInt(node.props.duration || '500');

    if (node.props.id) {
        runtime.app[node.props.id] = effect;
    }

    return document.createComment(`Glow Effect: ${node.props.id}`);
}
