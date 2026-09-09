"""
UI Engine - Desktop Adapter (pywebview wrapper)

Generates interactive Python pywebview desktop applications with:
- Bidirectional Python-JS communication via pywebview's JS API
- Reactive state management (QuantumState)
- Generated API class from q:function nodes (QuantumAPI)
- Event transformation (on-click, on-submit, bind)
- Component bridge for the interactive widgets (toast, carousel/slide,
  stepper/step, calendar, date-picker): user interaction is pushed into
  QuantumState and Python can drive the widgets through QuantumAPI
"""

import json
import re
from typing import List, Dict, Any, Optional

from quantum.core.ast_nodes import QuantumNode
from quantum.core.features.state_management.src.ast_node import SetNode
from quantum.core.features.functions.src.ast_node import FunctionNode
from quantum.core.features.ui_engine.src.ast_nodes import (
    UICalendarNode, UICarouselNode, UIDatePickerNode, UISlideNode,
    UIStepNode, UIStepperNode, UIToastNode, UIToastContainerNode,
)
from quantum.runtime.ui_html_adapter import UIHtmlAdapter, completed_step_indices
from quantum.runtime.ui_desktop_templates import (
    QUANTUM_STATE_CLASS,
    QUANTUM_API_CLASS,
    JS_BRIDGE_CODE,
    DESKTOP_TEMPLATE,
)


# ==========================================================================
# UI component bridge (toast, carousel/slide, stepper/step, calendar,
# date-picker) - injected next to JS_BRIDGE_CODE in the generated page.
#
# The markup contract used here is the one published by
# quantum/runtime/ui_html_templates.py (.q-carousel-track, .q-step-item,
# .q-calendar-day, .q-date-picker-input, .q-toast-container, ...).
# When the page also ships the shared controllers (__quantumCarousel,
# __quantumStepper, __quantumCalendar, __quantumToast) the bridge drives
# those instead of touching the DOM itself, so both paths stay in sync.
#
# __QUANTUM_UI_SPEC__ is replaced with the component descriptors collected
# from the AST.
# ==========================================================================

UI_COMPONENT_BRIDGE_JS = """\
<script>
// Quantum Desktop - UI component bridge
window.__quantumUI = (function() {
    'use strict';

    var SPEC = __QUANTUM_UI_SPEC__;

    var MONTHS = ['January', 'February', 'March', 'April', 'May', 'June',
                  'July', 'August', 'September', 'October', 'November', 'December'];
    var TOAST_ICONS = {
        info: '&#9432;', success: '&#10003;', warning: '&#9888;', danger: '&#10007;'
    };

    var watchers = {};
    var toastSeq = 0;
    var toastContainers = {};

    // ------------------------------------------------------------------
    // Generic helpers
    // ------------------------------------------------------------------

    function nodes(root, selector) {
        return Array.prototype.slice.call((root || document).querySelectorAll(selector));
    }

    function toInt(value, fallback) {
        var n = parseInt(value, 10);
        return isNaN(n) ? fallback : n;
    }

    function isTruthy(value) {
        return !(value === false || value === null || value === undefined ||
                 value === 0 || value === '' || value === 'false' || value === '0');
    }

    function escapeHtml(text) {
        return String(text === null || text === undefined ? '' : text)
            .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }

    function elementFor(spec, selector, excludeInside) {
        if (spec.__el && document.body.contains(spec.__el)) return spec.__el;
        var found = null;
        if (spec.element_id) found = document.getElementById(spec.element_id);
        if (!found) {
            var candidates = nodes(document, selector);
            // Alguns componentes do adapter html aparecem DUAS vezes com a
            // mesma classe: o <ui:calendar> real e o calendario dentro do
            // popup do date-picker sao ambos `.q-calendar`. Pegar por indice
            // fazia o date-picker dirigir o binding de outro calendario —
            // escrevendo no lugar errado, sem sinal nenhum. Quem passa
            // `excludeInside` esta dizendo qual container nao conta.
            if (excludeInside) {
                candidates = candidates.filter(function(el) {
                    return !el.closest || !el.closest(excludeInside);
                });
            }
            found = candidates[spec.index] || null;
        }
        spec.__el = found;
        return found;
    }

    // Returns the handle the page controller registered for this element,
    // or null when the page never initialised one.
    function pageHandle(globalName, el) {
        var api = window[globalName];
        if (!api || !el || !el.id || typeof api.get !== 'function') return null;
        return api.get(el.id) || null;
    }

    function pushState(name, value) {
        if (!name) return;
        if (window.__quantumState) window.__quantumState[name] = value;
        if (window.__quantumCall) window.__quantumCall('ui_set_state', {name: name, value: value});
    }

    function callHandler(handler, payload) {
        if (handler && window.__quantumCall) window.__quantumCall(handler, payload || {});
    }

    function watchState(name, fn) {
        if (!name) return;
        if (!watchers[name]) watchers[name] = [];
        watchers[name].push(fn);
    }

    // Chain onto the desktop bridge so Python state pushes reach the widgets.
    function installStateHook() {
        var previous = window.__quantumStateUpdate;
        window.__quantumStateUpdate = function(name, value) {
            if (previous) previous(name, value);
            var list = watchers[name] || [];
            list.forEach(function(fn) {
                try { fn(value); } catch (err) { console.warn('Quantum UI watcher failed:', err); }
            });
        };
    }

    function findSpec(list, ref) {
        if (ref === undefined || ref === null || ref === '') return list[0] || null;
        if (typeof ref === 'number') return list[ref] || null;
        for (var i = 0; i < list.length; i++) {
            if (list[i].element_id === ref || list[i].bind === ref) return list[i];
        }
        return list[toInt(ref, -1)] || null;
    }

    // ------------------------------------------------------------------
    // ui:toast-container / ui:toast
    // ------------------------------------------------------------------

    function defaultToastPosition() {
        if (SPEC.toast_containers.length) return SPEC.toast_containers[0].position;
        if (SPEC.toasts.length) return SPEC.toasts[0].position;
        return 'top-right';
    }

    function maxToastsFor(position) {
        for (var i = 0; i < SPEC.toast_containers.length; i++) {
            if (SPEC.toast_containers[i].position === position) {
                return SPEC.toast_containers[i].max_toasts;
            }
        }
        return SPEC.toast_containers.length ? SPEC.toast_containers[0].max_toasts : 0;
    }

    function toastContainer(position) {
        if (toastContainers[position] && document.body.contains(toastContainers[position])) {
            return toastContainers[position];
        }
        var el = document.querySelector('.q-toast-container.q-toast-' + position);
        if (!el) {
            el = document.createElement('div');
            el.className = 'q-toast-container q-toast-' + position;
            document.body.appendChild(el);
        }
        toastContainers[position] = el;
        return el;
    }

    function toastShow(options) {
        options = options || {};
        var position = options.position || defaultToastPosition();

        if (window.__quantumToast && window.__quantumToast.show) {
            var forwarded = {};
            for (var key in options) {
                if (Object.prototype.hasOwnProperty.call(options, key)) forwarded[key] = options[key];
            }
            forwarded.position = position;
            return window.__quantumToast.show(forwarded);
        }

        // Page has no toast controller: build the toast from the markup contract.
        var container = toastContainer(position);
        var id = 'q-desktop-toast-' + (++toastSeq);
        var toast = document.createElement('div');
        toast.id = id;
        toast.className = 'q-toast q-toast-' + (options.variant || 'info');

        var icon = options.icon || TOAST_ICONS[options.variant] || TOAST_ICONS.info;
        var html = '';
        if (options.icon !== false) html += '<span class="q-toast-icon">' + icon + '</span>';
        html += '<div class="q-toast-content">';
        if (options.title) html += '<div class="q-toast-title">' + escapeHtml(options.title) + '</div>';
        html += '<div class="q-toast-message">' + escapeHtml(options.message || '') + '</div>';
        html += '</div>';
        if (options.dismissible !== false) {
            html += '<button type="button" class="q-toast-close">&times;</button>';
        }
        toast.innerHTML = html;

        var closeBtn = toast.querySelector('.q-toast-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', function() {
                toastDismiss(id);
                callHandler(options.on_close, {id: id});
            });
        }

        container.appendChild(toast);

        var max = maxToastsFor(position);
        if (max > 0) {
            var visible = nodes(container, '.q-toast');
            while (visible.length > max) { toastDismiss(visible.shift().id); }
        }

        var duration = options.duration === undefined ? 3000 : options.duration;
        if (duration > 0) {
            setTimeout(function() {
                toastDismiss(id);
                callHandler(options.on_close, {id: id});
            }, duration);
        }
        return id;
    }

    function toastDismiss(id) {
        if (!id) return;
        if (window.__quantumToast && window.__quantumToast.dismiss &&
            String(id).indexOf('q-desktop-toast-') !== 0) {
            return window.__quantumToast.dismiss(id);
        }
        var el = document.getElementById(id);
        if (!el) return;
        el.classList.add('q-toast-out');
        setTimeout(function() { if (el.parentNode) el.parentNode.removeChild(el); }, 300);
    }

    function toastDismissAll() {
        if (window.__quantumToast && window.__quantumToast.dismissAll) {
            window.__quantumToast.dismissAll();
        }
        nodes(document, '.q-toast-container .q-toast').forEach(function(t) { toastDismiss(t.id); });
    }

    function toastOptions(spec) {
        return {
            variant: spec.variant,
            title: spec.title,
            message: spec.message,
            position: spec.position,
            duration: spec.duration,
            dismissible: spec.dismissible,
            icon: spec.icon || undefined,
            on_close: spec.on_close
        };
    }

    function toastWire(spec) {
        // An inline <ui:toast> is rendered by the HTML adapter; a bound one is
        // toggled by Python state, an unbound one auto-dismisses like a toast.
        var el = elementFor(spec, '.q-toast');

        function setVisible(visible) {
            if (spec.__visible === visible) return;
            spec.__visible = visible;
            if (el) {
                el.style.display = visible ? '' : 'none';
                if (visible) el.classList.remove('q-toast-out');
            } else if (visible) {
                spec.__floating = toastShow(toastOptions(spec));
            } else if (spec.__floating) {
                toastDismiss(spec.__floating);
                spec.__floating = null;
            }
            if (visible && spec.duration > 0) {
                setTimeout(function() {
                    if (!spec.__visible) return;
                    setVisible(false);
                    if (spec.show) pushState(spec.show, false);
                    callHandler(spec.on_close, {});
                }, spec.duration);
            }
        }

        if (el) {
            var closeBtn = el.querySelector('.q-toast-close');
            if (closeBtn) {
                closeBtn.addEventListener('click', function() {
                    setVisible(false);
                    if (spec.show) pushState(spec.show, false);
                    callHandler(spec.on_close, {});
                });
            }
        }

        if (spec.show) {
            spec.__visible = true;
            setVisible(false);
            watchState(spec.show, function(value) { setVisible(isTruthy(value)); });
        } else {
            spec.__visible = false;
            setVisible(true);
        }
    }

    // ------------------------------------------------------------------
    // ui:carousel / ui:slide
    // ------------------------------------------------------------------

    function carouselTotal(el, spec) {
        var count = nodes(el, '.q-carousel-slide').length;
        return count || spec.slides.length;
    }

    function normalizeIndex(index, total, loop) {
        if (!total) return 0;
        if (index < 0) return loop ? total - 1 : 0;
        if (index >= total) return loop ? 0 : total - 1;
        return index;
    }

    function carouselApply(el, index) {
        var slides = nodes(el, '.q-carousel-slide');
        var fade = el.classList.contains('q-carousel-fade');
        var track = el.querySelector('.q-carousel-track');
        if (fade) {
            slides.forEach(function(slide, i) { slide.classList.toggle('active', i === index); });
        } else if (track) {
            track.style.transform = 'translateX(-' + (index * 100) + '%)';
        }
        nodes(el, '.q-carousel-indicator').forEach(function(ind, i) {
            ind.classList.toggle('active', i === index);
        });
    }

    function carouselCurrent(el, spec) {
        var indicators = nodes(el, '.q-carousel-indicator');
        for (var i = 0; i < indicators.length; i++) {
            if (indicators[i].classList.contains('active')) return i;
        }
        var slides = nodes(el, '.q-carousel-slide');
        for (var k = 0; k < slides.length; k++) {
            if (slides[k].classList.contains('active')) return k;
        }
        var track = el.querySelector('.q-carousel-track');
        if (track && track.style.transform) {
            var match = /translateX\\(\\s*-?([0-9.]+)%/.exec(track.style.transform);
            if (match) return Math.round(parseFloat(match[1]) / 100);
        }
        return spec.current;
    }

    function carouselCommit(spec, index, notify) {
        var changed = spec.current !== index;
        spec.current = index;
        if (!changed && !notify) return index;
        if (changed) {
            if (spec.bind) pushState(spec.bind, index);
            callHandler(spec.on_change, {index: index});
        }
        return index;
    }

    function carouselGoTo(ref, index) {
        var spec = findSpec(SPEC.carousels, ref);
        if (!spec) return -1;
        var el = elementFor(spec, '.q-carousel');
        if (!el) return -1;
        var total = carouselTotal(el, spec);
        if (!total) return -1;

        var target = normalizeIndex(toInt(index, spec.current), total, spec.loop);
        var handle = pageHandle('__quantumCarousel', el);
        if (handle && typeof handle.goTo === 'function') {
            handle.goTo(target);
        } else {
            var indicators = nodes(el, '.q-carousel-indicator');
            // Reuse the page controller's own listeners when it owns the DOM.
            if (handle && indicators[target]) indicators[target].click();
            if (carouselCurrent(el, spec) !== target) carouselApply(el, target);
        }
        return carouselCommit(spec, target, false);
    }

    function carouselStep(ref, delta) {
        var spec = findSpec(SPEC.carousels, ref);
        if (!spec) return -1;
        return carouselGoTo(spec.element_id || spec.index, spec.current + delta);
    }

    function carouselShowSlide(slideRef) {
        for (var i = 0; i < SPEC.carousels.length; i++) {
            var slides = SPEC.carousels[i].slides;
            for (var s = 0; s < slides.length; s++) {
                if (slides[s].element_id && slides[s].element_id === slideRef) {
                    return carouselGoTo(i, s);
                }
            }
        }
        return -1;
    }

    function carouselAutoPlay(spec, el) {
        if (!spec.auto_play || spec.interval <= 0) return;
        if (pageHandle('__quantumCarousel', el)) return;  // page controller already advances it
        var timer = null;
        function start() {
            if (timer) return;
            timer = setInterval(function() { carouselStep(spec.element_id || spec.index, 1); }, spec.interval);
        }
        function stop() { if (timer) { clearInterval(timer); timer = null; } }
        el.addEventListener('mouseenter', stop);
        el.addEventListener('mouseleave', start);
        start();
    }

    function carouselWire(spec) {
        var el = elementFor(spec, '.q-carousel');
        if (!el) return;
        var driven = !!pageHandle('__quantumCarousel', el);
        var total = carouselTotal(el, spec);
        var ref = spec.element_id || spec.index;

        if (driven) {
            // The page owns the widget: watch the controls and mirror the result.
            el.addEventListener('click', function(ev) {
                var hit = ev.target && ev.target.closest
                    ? ev.target.closest('.q-carousel-indicator, .q-carousel-prev, .q-carousel-next')
                    : null;
                if (!hit) return;
                setTimeout(function() { carouselCommit(spec, carouselCurrent(el, spec), false); }, 0);
            });
        } else {
            var prevBtn = el.querySelector('.q-carousel-prev');
            var nextBtn = el.querySelector('.q-carousel-next');
            if (prevBtn) prevBtn.addEventListener('click', function() { carouselStep(ref, -1); });
            if (nextBtn) nextBtn.addEventListener('click', function() { carouselStep(ref, 1); });
            nodes(el, '.q-carousel-indicator').forEach(function(ind, i) {
                ind.addEventListener('click', function() { carouselGoTo(ref, i); });
            });
            carouselApply(el, normalizeIndex(spec.current, total, spec.loop));
        }

        if (spec.bind) {
            watchState(spec.bind, function(value) {
                var index = toInt(value, spec.current);
                if (index !== spec.current) carouselGoTo(ref, index);
            });
        }

        carouselAutoPlay(spec, el);
    }

    // ------------------------------------------------------------------
    // ui:stepper / ui:step
    // ------------------------------------------------------------------

    function stepperItems(el) {
        return nodes(el, '.q-step-item');
    }

    function stepperApply(el, index) {
        stepperItems(el).forEach(function(item, i) {
            item.classList.toggle('active', i === index);
        });
        nodes(el, '.q-step-content').forEach(function(content, i) {
            content.classList.toggle('active', i === index);
        });
    }

    function stepperCurrent(el, spec) {
        var items = stepperItems(el);
        for (var i = 0; i < items.length; i++) {
            if (items[i].classList.contains('active')) return i;
        }
        return spec.current;
    }

    function stepperCanGoTo(spec, index) {
        if (!spec.linear) return true;
        if (index <= spec.current) return true;
        return index === spec.current + 1 && spec.completed.indexOf(spec.current) !== -1;
    }

    function stepperMarkStates(el, spec) {
        // ui:step attributes that describe the initial state of each step.
        stepperItems(el).forEach(function(item, i) {
            var step = spec.steps[i];
            if (!step) return;
            if (step.completed && spec.completed.indexOf(i) === -1) spec.completed.push(i);
            item.classList.toggle('completed', spec.completed.indexOf(i) !== -1 && i !== spec.current);
            if (step.error) {
                item.classList.add('error');
                item.setAttribute('title', step.error);
            }
            if (step.optional) item.setAttribute('data-optional', 'true');
        });
    }

    function stepperCommit(spec, index, notify) {
        var changed = spec.current !== index;
        spec.current = index;
        if (changed || notify) {
            if (spec.bind) pushState(spec.bind, index);
            callHandler(spec.on_change, {index: index});
        }
        return index;
    }

    function stepperGoTo(ref, index, force) {
        var spec = findSpec(SPEC.steppers, ref);
        if (!spec) return -1;
        var el = elementFor(spec, '.q-stepper');
        if (!el) return -1;
        var total = stepperItems(el).length || spec.steps.length;
        var target = toInt(index, spec.current);
        if (!total || target < 0 || target >= total) return -1;
        if (!force && !stepperCanGoTo(spec, target)) return -1;

        var handle = pageHandle('__quantumStepper', el);
        if (handle && typeof handle.goTo === 'function') {
            handle.goTo(target);
        } else {
            stepperApply(el, target);
            stepperMarkStates(el, spec);
        }
        return stepperCommit(spec, target, false);
    }

    function stepperComplete(ref, index) {
        var spec = findSpec(SPEC.steppers, ref);
        if (!spec) return -1;
        var el = elementFor(spec, '.q-stepper');
        if (!el) return -1;
        var target = index === undefined || index === null ? spec.current : toInt(index, spec.current);
        if (spec.completed.indexOf(target) === -1) spec.completed.push(target);

        var handle = pageHandle('__quantumStepper', el);
        if (handle && typeof handle.complete === 'function') {
            handle.complete(target);
        } else {
            var item = stepperItems(el)[target];
            if (item) {
                item.classList.remove('error');
                if (target !== spec.current) item.classList.add('completed');
            }
        }

        var total = stepperItems(el).length || spec.steps.length;
        if (total && spec.completed.length >= total) callHandler(spec.on_complete, {});
        return target;
    }

    function stepperStep(ref, delta) {
        var spec = findSpec(SPEC.steppers, ref);
        if (!spec) return -1;
        return stepperGoTo(spec.element_id || spec.index, spec.current + delta, delta < 0);
    }

    function stepperShowStep(stepRef) {
        for (var i = 0; i < SPEC.steppers.length; i++) {
            var steps = SPEC.steppers[i].steps;
            for (var s = 0; s < steps.length; s++) {
                if (steps[s].element_id && steps[s].element_id === stepRef) {
                    return stepperGoTo(i, s, true);
                }
            }
        }
        return -1;
    }

    function stepperWire(spec) {
        var el = elementFor(spec, '.q-stepper');
        if (!el) return;
        var driven = !!pageHandle('__quantumStepper', el);
        var ref = spec.element_id || spec.index;

        stepperMarkStates(el, spec);
        if (!driven) stepperApply(el, spec.current);

        if (driven) {
            el.addEventListener('click', function(ev) {
                var hit = ev.target && ev.target.closest ? ev.target.closest('.q-step-item') : null;
                if (!hit) return;
                setTimeout(function() { stepperCommit(spec, stepperCurrent(el, spec), false); }, 0);
            });
        } else if (spec.clickable) {
            stepperItems(el).forEach(function(item, i) {
                item.style.cursor = 'pointer';
                item.addEventListener('click', function() { stepperGoTo(ref, i); });
            });
        }

        if (spec.bind) {
            watchState(spec.bind, function(value) {
                var index = toInt(value, spec.current);
                if (index !== spec.current) stepperGoTo(ref, index, true);
            });
        }
    }

    // ------------------------------------------------------------------
    // ui:calendar
    // ------------------------------------------------------------------

    function pad2(n) { return (n < 10 ? '0' : '') + n; }

    // True only when the page registered a calendar handle that can select and
    // repaint on its own; a bare state entry is not enough to own the widget.
    function calendarDriven(el) {
        var handle = pageHandle('__quantumCalendar', el);
        return !!(handle && typeof handle.selectDate === 'function' &&
                  typeof handle.render === 'function');
    }

    function calendarView(el) {
        // Reads the month currently rendered in the calendar header.
        var title = el.querySelector('.q-calendar-title');
        var now = new Date();
        if (!title) return {month: now.getMonth(), year: now.getFullYear()};
        var parts = String(title.textContent || '').trim().split(/\\s+/);
        var month = MONTHS.indexOf(parts[0]);
        var year = toInt(parts[1], now.getFullYear());
        return {month: month === -1 ? now.getMonth() : month, year: year};
    }

    function calendarIso(el, day) {
        var view = calendarView(el);
        return view.year + '-' + pad2(view.month + 1) + '-' + pad2(day);
    }

    function calendarValue(spec) {
        if (spec.mode === 'range') return {start: spec.range_start || '', end: spec.range_end || ''};
        if (spec.mode === 'multiple') return spec.multiple.slice();
        return spec.selected || '';
    }

    function calendarSelectIso(spec, iso) {
        if (spec.mode === 'single') {
            spec.selected = iso;
        } else if (spec.mode === 'range') {
            if (!spec.range_start || spec.range_end) {
                spec.range_start = iso;
                spec.range_end = '';
            } else if (iso < spec.range_start) {
                spec.range_end = spec.range_start;
                spec.range_start = iso;
            } else {
                spec.range_end = iso;
            }
        } else {
            var at = spec.multiple.indexOf(iso);
            if (at === -1) spec.multiple.push(iso); else spec.multiple.splice(at, 1);
        }
    }

    function calendarPaint(el, spec) {
        // Only used when the page has no calendar controller repainting itself.
        var view = calendarView(el);
        nodes(el, '.q-calendar-day').forEach(function(cell) {
            if (cell.classList.contains('other-month') || cell.classList.contains('week-number')) return;
            var day = toInt(cell.textContent, 0);
            if (!day) return;
            var iso = view.year + '-' + pad2(view.month + 1) + '-' + pad2(day);
            cell.classList.remove('selected', 'range-start', 'range-end', 'in-range');
            if (spec.mode === 'single') {
                cell.classList.toggle('selected', iso === spec.selected);
            } else if (spec.mode === 'range') {
                if (iso === spec.range_start) cell.classList.add('range-start', 'selected');
                if (iso === spec.range_end) cell.classList.add('range-end', 'selected');
                if (spec.range_start && spec.range_end && iso > spec.range_start && iso < spec.range_end) {
                    cell.classList.add('in-range');
                }
            } else if (spec.multiple.indexOf(iso) !== -1) {
                cell.classList.add('selected');
            }
        });
    }

    function calendarDayCell(el, iso) {
        var view = calendarView(el);
        var prefix = view.year + '-' + pad2(view.month + 1) + '-';
        if (iso.indexOf(prefix) !== 0) return null;
        var day = toInt(iso.slice(prefix.length), 0);
        var match = null;
        nodes(el, '.q-calendar-day').forEach(function(cell) {
            if (match || cell.classList.contains('other-month')) return;
            if (toInt(cell.textContent, -1) === day) match = cell;
        });
        return match;
    }

    function calendarNavigateTo(el, iso) {
        // Walk the header buttons until the wanted month is on screen.
        var buttons = nodes(el, '.q-calendar-nav, .q-calendar-nav button, .q-calendar-header button');
        if (buttons.length < 2) return false;
        var back = buttons[0];
        var forward = buttons[buttons.length - 1];
        var target = toInt(iso.slice(0, 4), 0) * 12 + toInt(iso.slice(5, 7), 1) - 1;
        for (var guard = 0; guard < 36; guard++) {
            var view = calendarView(el);
            var current = view.year * 12 + view.month;
            if (current === target) return true;
            (current > target ? back : forward).click();
            if (calendarView(el).year * 12 + calendarView(el).month === current) return false;
        }
        return false;
    }

    function calendarCommit(spec, el) {
        var value = calendarValue(spec);
        if (spec.bind) pushState(spec.bind, value);
        callHandler(spec.on_change, {value: value});
        if (!calendarDriven(el)) calendarPaint(el, spec);
        return value;
    }

    function calendarSelect(ref, value) {
        var spec = findSpec(SPEC.calendars, ref);
        if (!spec) return null;
        var el = elementFor(spec, '.q-calendar', '.q-date-picker-dropdown');
        if (!el) return null;
        var iso = String(value === null || value === undefined ? '' : value);
        if (!iso) {
            spec.selected = '';
            spec.range_start = '';
            spec.range_end = '';
            spec.multiple = [];
            return calendarCommit(spec, el);
        }
        calendarNavigateTo(el, iso);
        var cell = calendarDayCell(el, iso);
        if (cell && calendarDriven(el)) {
            cell.click();  // let the page controller own the selection
        }
        calendarSelectIso(spec, iso);
        return calendarCommit(spec, el);
    }

    function calendarWire(spec) {
        var el = elementFor(spec, '.q-calendar', '.q-date-picker-dropdown');
        if (!el) return;

        el.addEventListener('click', function(ev) {
            var target = ev.target;
            if (!target || !target.classList) return;

            if (target.closest && target.closest('.q-calendar-nav, .q-calendar-header button')) {
                setTimeout(function() {
                    var view = calendarView(el);
                    callHandler(spec.on_month_change, {month: view.month, year: view.year});
                    if (!calendarDriven(el)) calendarPaint(el, spec);
                }, 0);
                return;
            }

            var cell = target.classList.contains('q-calendar-day')
                ? target
                : (target.closest ? target.closest('.q-calendar-day') : null);
            if (!cell) return;
            if (cell.classList.contains('other-month') || cell.classList.contains('disabled') ||
                cell.classList.contains('week-number')) return;
            var day = toInt(cell.textContent, 0);
            if (!day) return;
            calendarSelectIso(spec, calendarIso(el, day));
            calendarCommit(spec, el);
        });

        if (spec.bind) {
            watchState(spec.bind, function(value) {
                if (value === null || value === undefined) return;
                var iso = typeof value === 'object' ? (value.start || '') : String(value);
                if (!iso) return;
                if (spec.mode === 'single' && iso === spec.selected) return;
                if (spec.mode === 'range' && iso === spec.range_start) return;
                calendarSelect(spec.element_id || spec.index, iso);
            });
        }

        if (spec.selected || spec.range_start || spec.multiple.length) {
            if (!calendarDriven(el)) calendarPaint(el, spec);
        }
    }

    // ------------------------------------------------------------------
    // ui:date-picker
    // ------------------------------------------------------------------

    // O date-picker tem DOIS campos: o visivel, formatado conforme
    // `format` (09/15/2026), e um hidden com o valor canonico ISO
    // (2026-09-15) que carrega o `name` do bind — e o que um formulario
    // submete e o que o Python espera receber.
    //
    // Esta ponte lia e escrevia o campo VISIVEL. Com format != ISO, o
    // Python recebia "09/15/2026" enquanto o campo canonico ao lado tinha
    // "2026-09-15": dado corrompido em silencio, sem erro nenhum. E
    // datePickerSet escrevia ISO cru no campo de exibicao, quebrando tambem
    // o formato que o usuario ve.
    //
    // A autoridade sobre esse par de campos e __quantumDatePicker, do
    // adapter html: setValue(id, iso) escreve os dois, getValue(id) le o
    // canonico. Delegar e o conserto; reimplementar formatacao aqui seria
    // criar uma segunda verdade.

    function datePickerDisplay(spec) {
        var el = elementFor(spec, '.q-date-picker');
        if (!el) return null;
        return el.querySelector('.q-date-picker-input') || el.querySelector('input');
    }

    // O campo canonico. `#<id>-value` e o que o adapter html emite; o
    // input[type=hidden] e a rede de seguranca se o id mudar de forma.
    function datePickerValueField(spec) {
        var el = elementFor(spec, '.q-date-picker');
        if (!el) return null;
        return (el.id && document.getElementById(el.id + '-value')) ||
               el.querySelector('input[type="hidden"]');
    }

    function datePickerIso(spec) {
        var el = elementFor(spec, '.q-date-picker');
        if (el && el.id && window.__quantumDatePicker &&
            typeof __quantumDatePicker.getValue === 'function') {
            return __quantumDatePicker.getValue(el.id);
        }
        var hidden = datePickerValueField(spec);
        if (hidden) return hidden.value;
        var display = datePickerDisplay(spec);
        return display ? display.value : '';
    }

    function datePickerSet(ref, value) {
        var spec = findSpec(SPEC.date_pickers, ref);
        if (!spec) return null;
        var iso = value === null || value === undefined ? '' : String(value);
        var el = elementFor(spec, '.q-date-picker');

        if (el && el.id && window.__quantumDatePicker &&
            typeof __quantumDatePicker.setValue === 'function') {
            // Escreve o hidden E reformata a exibicao, numa so chamada.
            __quantumDatePicker.setValue(el.id, iso);
        } else {
            var hidden = datePickerValueField(spec);
            var display = datePickerDisplay(spec);
            if (hidden) hidden.value = iso;
            if (display) display.value = iso;
        }

        spec.value = iso;
        if (spec.bind) pushState(spec.bind, iso);
        callHandler(spec.on_change, {value: iso});
        return iso;
    }

    function datePickerReport(spec) {
        var iso = datePickerIso(spec);
        if (iso === spec.value) return;
        spec.value = iso;
        if (spec.bind) pushState(spec.bind, iso);
        callHandler(spec.on_change, {value: iso});
    }

    function datePickerWire(spec) {
        var el = elementFor(spec, '.q-date-picker');
        if (!el) return;
        spec.value = datePickerIso(spec);

        var hidden = datePickerValueField(spec);
        if (hidden) hidden.addEventListener('change', function() { datePickerReport(spec); });

        var display = datePickerDisplay(spec);
        if (display) display.addEventListener('change', function() { datePickerReport(spec); });

        var clear = el.querySelector('.q-date-picker-clear');
        if (clear) {
            clear.addEventListener('click', function() {
                datePickerSet(spec.element_id || spec.index, '');
            });
        }

        // A calendar rendered inside the popup reports through the picker.
        el.addEventListener('click', function(ev) {
            var cell = ev.target && ev.target.closest ? ev.target.closest('.q-calendar-day') : null;
            if (!cell || cell.classList.contains('other-month') || cell.classList.contains('disabled')) return;
            setTimeout(function() { datePickerReport(spec); }, 0);
        });

        if (spec.bind) {
            watchState(spec.bind, function(value) {
                var iso = value === null || value === undefined ? '' : String(value);
                if (iso === spec.value) return;
                spec.value = iso;
                if (el.id && window.__quantumDatePicker &&
                    typeof __quantumDatePicker.setValue === 'function') {
                    __quantumDatePicker.setValue(el.id, iso);
                } else {
                    var h = datePickerValueField(spec);
                    var d = datePickerDisplay(spec);
                    if (h) h.value = iso;
                    if (d) d.value = iso;
                }
            });
        }
    }

    // ------------------------------------------------------------------
    // Bootstrap
    // ------------------------------------------------------------------

    function init() {
        SPEC.toasts.forEach(toastWire);
        SPEC.carousels.forEach(carouselWire);
        SPEC.steppers.forEach(stepperWire);
        SPEC.calendars.forEach(calendarWire);
        SPEC.date_pickers.forEach(datePickerWire);
    }

    installStateHook();
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        setTimeout(init, 0);
    }

    return {
        spec: SPEC,
        toast: toastShow,
        dismissToast: toastDismiss,
        dismissToasts: toastDismissAll,
        carouselGoTo: carouselGoTo,
        carouselNext: function(ref) { return carouselStep(ref, 1); },
        carouselPrev: function(ref) { return carouselStep(ref, -1); },
        showSlide: carouselShowSlide,
        stepperGoTo: function(ref, index) { return stepperGoTo(ref, index, true); },
        stepperNext: function(ref) { return stepperStep(ref, 1); },
        stepperPrev: function(ref) { return stepperStep(ref, -1); },
        stepperComplete: stepperComplete,
        showStep: stepperShowStep,
        calendarSelect: calendarSelect,
        datePickerSet: datePickerSet
    };
})();
</script>
"""


class UIDesktopAdapter:
    """Generates Python pywebview app with JS bridge from UI AST nodes."""

    def __init__(self):
        self._functions: Dict[str, FunctionNode] = {}
        self._state_vars: Dict[str, Any] = {}
        self._persist_config: Dict[str, Dict] = {}  # name -> {scope, key, ttl, encrypt}

        # Interactive component descriptors, in document order (the same order
        # the HTML adapter renders them, so index-based lookup matches the DOM)
        self._carousels: List[Dict[str, Any]] = []
        self._steppers: List[Dict[str, Any]] = []
        self._calendars: List[Dict[str, Any]] = []
        self._date_pickers: List[Dict[str, Any]] = []
        self._toasts: List[Dict[str, Any]] = []
        self._toast_containers: List[Dict[str, Any]] = []

    def generate(
        self,
        windows: List[QuantumNode],
        ui_children: List[QuantumNode],
        title: str = "Quantum UI",
        functions: Optional[Dict[str, FunctionNode]] = None,
        state_vars: Optional[Dict[str, Any]] = None,
        persist_config: Optional[Dict[str, Dict]] = None,
        width: int = 1024,
        height: int = 768,
    ) -> str:
        """Generate Python pywebview app with JS bridge from UI AST.

        Args:
            windows: List of UIWindowNode elements.
            ui_children: List of top-level UI nodes (outside windows).
            title: Window title.
            functions: Dict of function name -> FunctionNode from q:function.
            state_vars: Dict of variable name -> initial value from q:set.
            persist_config: Dict of variable name -> persistence config.
            width: Window width in pixels.
            height: Window height in pixels.

        Returns:
            Generated Python source code as string.
        """
        self._functions = functions or {}
        self._state_vars = dict(state_vars or {})
        self._persist_config = persist_config or {}

        # Collect the interactive components so the bridge can wire them and
        # seed the state variables they are bound to
        self._reset_components()
        self._collect_nodes(windows)
        self._collect_nodes(ui_children)
        self._seed_component_state()

        # Generate HTML with desktop_mode=True for event transformation
        html_adapter = UIHtmlAdapter(desktop_mode=True)
        html = html_adapter.generate(windows, ui_children, title)

        # Inject JS bridge before </body>
        binding_script = html_adapter._generate_binding_script()
        js_injection = JS_BRIDGE_CODE
        if binding_script:
            js_injection += '\n' + binding_script
        component_script = self._generate_component_script()
        if component_script:
            js_injection += '\n' + component_script

        html = html.replace('</body>', f'{js_injection}\n</body>')

        # Generate state initialization code
        state_init = self._generate_state_init()

        # Generate function methods
        function_methods = self._generate_functions()

        # Generate persistence config as Python dict literal
        persist_config_str = self._generate_persist_config()

        # Build the final Python code
        return DESKTOP_TEMPLATE.format(
            quantum_state_class=QUANTUM_STATE_CLASS,
            quantum_api_class=QUANTUM_API_CLASS.format(
                state_init=state_init,
                function_methods=function_methods,
                persist_config=persist_config_str,
            ),
            title=repr(title),
            width=width,
            height=height,
            html_content=repr(html),
        )

    def _generate_persist_config(self) -> str:
        """Generate Python dict literal for persistence configuration.

        Returns:
            String representation of the persistence config dict.
        """
        if not self._persist_config:
            return '{}'

        parts = []
        for name, config in self._persist_config.items():
            scope = config.get('scope', 'local')
            key = config.get('key', name)
            ttl = config.get('ttl')
            encrypt = config.get('encrypt', False)

            config_parts = [
                f"'scope': '{scope}'",
                f"'key': '{key}'",
                f"'encrypt': {encrypt}",
            ]
            if ttl:
                config_parts.append(f"'ttl': {ttl}")

            parts.append(f"'{name}': {{{', '.join(config_parts)}}}")

        return '{' + ', '.join(parts) + '}'

    def _generate_state_init(self) -> str:
        """Generate Python code to initialize state variables.

        Returns:
            Indented Python code for state initialization.
        """
        if not self._state_vars:
            return '        pass  # No state variables'

        lines = []
        for name, value in self._state_vars.items():
            # Convert value to Python representation
            py_value = self._convert_value(value)
            lines.append(f"        self.state.set('{name}', {py_value})")

        return '\n'.join(lines)

    def _generate_functions(self) -> str:
        """Generate Python methods from q:function nodes.

        Also appends the component API methods (toast, carousel, stepper,
        calendar, date-picker) when the app uses those components.

        Returns:
            Python code for all function methods.
        """
        methods = []
        for func_name, func_node in self._functions.items():
            method_code = self._generate_function_method(func_name, func_node)
            methods.append(method_code)

        component_methods = self._generate_component_methods()
        if component_methods:
            methods.append(component_methods)

        if not methods:
            return '    pass  # No functions defined'

        return '\n\n'.join(methods)

    def _generate_function_method(self, func_name: str, func_node: FunctionNode) -> str:
        """Generate a Python method from a q:function node.

        Args:
            func_name: Name of the function.
            func_node: FunctionNode AST node.

        Returns:
            Python method code as string.
        """
        lines = [f"    def {func_name}(self, args=None):"]
        lines.append(f'        """Generated from q:function {func_name}"""')

        # Generate body from function statements
        if func_node.body:
            for stmt in func_node.body:
                stmt_code = self._generate_statement(stmt, func_name=func_name)
                if stmt_code:
                    lines.append(stmt_code)
        else:
            lines.append("        pass")

        return '\n'.join(lines)

    def _generate_statement(self, stmt: QuantumNode, indent: int = 8,
                            func_name: str = '?') -> str:
        """Generate Python code from a statement node.

        Args:
            stmt: A statement node (SetNode, etc.).
            indent: Number of spaces for indentation.
            func_name: q:function being generated, for the error message.

        Returns:
            Python code line.
        """
        pad = ' ' * indent

        if isinstance(stmt, SetNode):
            # Handle q:set statements
            value_expr = self._convert_expression(stmt.value)
            return f"{pad}self.state.set('{stmt.name}', {value_expr})"

        # O que este backend nao sabe traduzir vira um ERRO, nao um `pass`.
        #
        # So SetNode e tratado, e todo o resto virava
        # `pass  # Unsupported statement type: ...`. O caso comum e um
        # <q:script> (que o parser entrega como HTMLNode, com JavaScript
        # dentro): a funcao inteira do usuario virava um no-op. O botao
        # chamava, a API respondia sem erro nenhum, e nada acontecia — nem
        # na tela, nem no log, nem no console.
        #
        # Levantar na CHAMADA, e nao na geracao, e de proposito: o resto do
        # aplicativo continua sendo gerado e rodando, e so a funcao que
        # depende do que falta reclama — dizendo o que falta e onde.
        rotulo = self._describe_unsupported(stmt)
        mensagem = (
            f"q:function {func_name!r}: the desktop backend cannot translate "
            f"{rotulo} — it only supports q:set. Rewrite the body with q:set, "
            f"or run this component on the web target."
        )
        return f"{pad}raise NotImplementedError({mensagem!r})"

    @staticmethod
    def _describe_unsupported(stmt: QuantumNode) -> str:
        """Nome legivel do que nao pode ser traduzido."""
        tag = getattr(stmt, 'tag', None) or getattr(stmt, 'name', None)
        tipo = type(stmt).__name__
        if tag:
            return f"<{tag}> ({tipo})"
        return tipo

    def _convert_expression(self, expr: str) -> str:
        """Convert a Quantum expression {var + 1} to Python.

        Args:
            expr: Expression string, possibly with {brackets}.

        Returns:
            Python expression string.
        """
        if expr is None:
            return 'None'

        # Remove surrounding braces if present
        expr = expr.strip()
        if expr.startswith('{') and expr.endswith('}'):
            expr = expr[1:-1].strip()

        # Replace variable references with self.state.get('var')
        # Pattern: word that's not a Python keyword or number
        def replace_var(match):
            var = match.group(0)
            # Skip Python keywords and built-ins
            if var in ('True', 'False', 'None', 'and', 'or', 'not', 'if', 'else', 'for', 'in', 'is'):
                return var
            # Skip if it looks like a number
            if var.isdigit():
                return var
            # Skip if it's a method call (followed by parenthesis)
            return f"self.state.get('{var}')"

        # Match word boundaries for variable names
        result = re.sub(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b', replace_var, expr)

        return result

    def _convert_value(self, value: Any) -> str:
        """Convert a value to Python literal representation.

        Args:
            value: Value to convert (can be string, number, bool, etc.).

        Returns:
            Python literal string.
        """
        if value is None:
            return 'None'

        # Check if it's a string representation of a number
        if isinstance(value, str):
            # Try to parse as number
            if value.isdigit():
                return value
            try:
                float(value)
                return value
            except ValueError:
                pass

            # Boolean strings
            if value.lower() == 'true':
                return 'True'
            if value.lower() == 'false':
                return 'False'

            # Regular string
            return repr(value)

        # Already a Python value
        return repr(value)

    # ------------------------------------------------------------------
    # Interactive components: collection
    # ------------------------------------------------------------------

    def _reset_components(self):
        """Clear the collected component descriptors (generate() may re-run)."""
        self._carousels = []
        self._steppers = []
        self._calendars = []
        self._date_pickers = []
        self._toasts = []
        self._toast_containers = []

    def _has_components(self) -> bool:
        """True when the app uses at least one bridged component."""
        return bool(self._carousels or self._steppers or self._calendars or
                    self._date_pickers or self._toasts or self._toast_containers)

    def _collect_nodes(self, nodes: Optional[List[QuantumNode]]):
        """Walk a list of nodes collecting component descriptors."""
        for node in nodes or []:
            self._collect_node(node)

    def _collect_node(self, node: QuantumNode):
        """Collect a single node (depth-first, document order)."""
        if isinstance(node, UICarouselNode):
            self._collect_carousel(node)
        elif isinstance(node, UISlideNode):
            self._collect_slide(node)
        elif isinstance(node, UIStepperNode):
            self._collect_stepper(node)
        elif isinstance(node, UIStepNode):
            self._collect_step(node)
        elif isinstance(node, UICalendarNode):
            self._collect_calendar(node)
        elif isinstance(node, UIDatePickerNode):
            self._collect_date_picker(node)
        elif isinstance(node, UIToastNode):
            self._collect_toast(node)
        elif isinstance(node, UIToastContainerNode):
            self._collect_toast_container(node)
        else:
            self._collect_nodes(getattr(node, 'children', None))

    def _collect_carousel(self, node: UICarouselNode):
        """Descriptor for <ui:carousel> plus the ids of its <ui:slide> children."""
        slides = [
            {'element_id': self._node_id(child)}
            for child in (node.children or [])
            if isinstance(child, UISlideNode)
        ]
        self._carousels.append({
            'index': len(self._carousels),
            'element_id': self._node_id(node),
            'bind': self._bind_name(node.bind),
            'current': self._as_int(node.current, 0),
            'auto_play': self._as_bool(node.auto_play, False),
            'interval': self._as_int(node.interval, 5000),
            'loop': self._as_bool(node.loop, True),
            'animation': node.animation or 'slide',
            'show_arrows': self._as_bool(node.show_arrows, True),
            'show_indicators': self._as_bool(node.show_indicators, True),
            'on_change': node.on_change,
            'slides': slides,
        })
        self._collect_nodes(node.children)

    def _collect_slide(self, node: UISlideNode):
        """<ui:slide> carries no state of its own; its content may."""
        self._collect_nodes(node.children)

    def _collect_stepper(self, node: UIStepperNode):
        """Descriptor for <ui:stepper> plus the state of each <ui:step>."""
        step_nodes = [c for c in (node.children or []) if isinstance(c, UIStepNode)]
        current = self._as_int(node.current, 0)

        # A MESMA funcao que o adapter html usa para decidir isso. Aqui havia
        # uma segunda regra — `list(range(current)) if linear else []` — que
        # discordava dela de dois jeitos, e como esta ponte roda DEPOIS do
        # markup estatico, quem ganhava era a versao errada:
        #
        #  - num stepper nao-linear ela emitia lista vazia e apagava, no boot,
        #    as marcas que o html tinha desenhado certo;
        #  - `_as_bool(child.completed, False)` colapsava "nao setado" e
        #    "setado como false", entao um passo com completed="false" antes
        #    do atual ganhava a marca de volta.
        concluidos = completed_step_indices(step_nodes, current)

        steps = []
        for i, child in enumerate(step_nodes):
            steps.append({
                'element_id': self._node_id(child),
                'title': child.title,
                'description': child.description,
                'optional': self._as_bool(child.optional, False),
                'completed': i in concluidos,
                'error': child.error,
            })
        self._steppers.append({
            'index': len(self._steppers),
            'element_id': self._node_id(node),
            'bind': self._bind_name(node.bind),
            'current': current,
            'orientation': node.orientation or 'horizontal',
            'linear': self._as_bool(node.linear, True),
            'clickable': self._as_bool(node.clickable, False),
            'show_labels': self._as_bool(node.show_labels, True),
            'on_change': node.on_change,
            'on_complete': node.on_complete,
            'steps': steps,
            'completed': concluidos,
        })
        self._collect_nodes(node.children)

    def _collect_step(self, node: UIStepNode):
        """<ui:step> state is recorded by its stepper; recurse into content."""
        self._collect_nodes(node.children)

    def _collect_calendar(self, node: UICalendarNode):
        """Descriptor for <ui:calendar>."""
        mode = node.mode if node.mode in UICalendarNode.VALID_MODES else 'single'
        value = node.value or ''
        parts = [p.strip() for p in value.split(',') if p.strip()]
        self._calendars.append({
            'index': len(self._calendars),
            'element_id': self._node_id(node),
            'bind': self._bind_name(node.bind),
            'mode': mode,
            'selected': parts[0] if mode == 'single' and parts else '',
            'range_start': parts[0] if mode == 'range' and parts else '',
            'range_end': parts[1] if mode == 'range' and len(parts) > 1 else '',
            'multiple': parts if mode == 'multiple' else [],
            'min_date': node.min_date,
            'max_date': node.max_date,
            'first_day_of_week': self._as_int(node.first_day_of_week, 0),
            'on_change': node.on_change,
            'on_month_change': node.on_month_change,
        })

    def _collect_date_picker(self, node: UIDatePickerNode):
        """Descriptor for <ui:date-picker>."""
        self._date_pickers.append({
            'index': len(self._date_pickers),
            'element_id': self._node_id(node),
            'bind': self._bind_name(node.bind),
            'value': node.value or '',
            'placeholder': node.placeholder,
            'format': node.format,
            'min_date': node.min_date,
            'max_date': node.max_date,
            'clearable': self._as_bool(node.clearable, True),
            'on_change': node.on_change,
        })

    def _collect_toast(self, node: UIToastNode):
        """Descriptor for an inline <ui:toast>."""
        self._toasts.append({
            'index': len(self._toasts),
            'element_id': self._node_id(node),
            'variant': node.variant or 'info',
            'position': node.position or 'top-right',
            'duration': self._as_int(node.duration, 3000),
            'dismissible': self._as_bool(node.dismissible, True),
            'icon': node.icon,
            'title': node.title,
            'message': node.message or '',
            'show': self._bind_name(node.show),
            'on_close': node.on_close,
        })

    def _collect_toast_container(self, node: UIToastContainerNode):
        """Descriptor for <ui:toast-container> (defaults for raised toasts)."""
        self._toast_containers.append({
            'index': len(self._toast_containers),
            'element_id': self._node_id(node),
            'position': node.position or 'top-right',
            'max_toasts': self._as_int(node.max_toasts, 5),
        })

    def _seed_component_state(self):
        """Declare the state variables the components are bound to.

        A binding that has no matching q:set would otherwise never exist on the
        Python side, so the first value pushed from the UI would be the only
        thing the app ever knows about it.
        """
        for spec in self._carousels:
            if spec['bind'] and spec['bind'] not in self._state_vars:
                self._state_vars[spec['bind']] = spec['current']

        for spec in self._steppers:
            if spec['bind'] and spec['bind'] not in self._state_vars:
                self._state_vars[spec['bind']] = spec['current']

        for spec in self._calendars:
            if not spec['bind'] or spec['bind'] in self._state_vars:
                continue
            if spec['mode'] == 'multiple':
                self._state_vars[spec['bind']] = list(spec['multiple'])
            elif spec['mode'] == 'range':
                self._state_vars[spec['bind']] = {
                    'start': spec['range_start'], 'end': spec['range_end'],
                }
            else:
                self._state_vars[spec['bind']] = spec['selected']

        for spec in self._date_pickers:
            if spec['bind'] and spec['bind'] not in self._state_vars:
                self._state_vars[spec['bind']] = spec['value']

        for spec in self._toasts:
            if spec['show'] and spec['show'] not in self._state_vars:
                self._state_vars[spec['show']] = False

    # ------------------------------------------------------------------
    # Interactive components: code generation
    # ------------------------------------------------------------------

    def _generate_component_script(self) -> str:
        """Generate the JS bridge for the interactive components.

        Returns:
            A <script> block wiring toast/carousel/stepper/calendar/date-picker
            to QuantumState, or '' when the app uses none of them.
        """
        if not self._has_components():
            return ''

        spec = {
            'carousels': self._carousels,
            'steppers': self._steppers,
            'calendars': self._calendars,
            'date_pickers': self._date_pickers,
            'toasts': self._toasts,
            'toast_containers': self._toast_containers,
        }
        return UI_COMPONENT_BRIDGE_JS.replace(
            '__QUANTUM_UI_SPEC__', json.dumps(spec, sort_keys=True)
        )

    def _generate_component_methods(self) -> str:
        """Generate the QuantumAPI methods that drive the components.

        Returns:
            Python method code (4-space indented) or '' when the app uses none
            of the bridged components.
        """
        if not self._has_components():
            return ''

        blocks = ["""\
    def _ui_eval(self, expression):
        \"\"\"Evaluate a JS expression in the webview (UI component bridge).\"\"\"
        if not self._window:
            return None
        try:
            return self._window.evaluate_js(expression)
        except Exception as exc:
            print('Quantum UI bridge error: ' + str(exc))
            return None

    def _ui_call(self, method, *args):
        \"\"\"Call window.__quantumUI.<method> with JSON encoded arguments.\"\"\"
        import json
        payload = ', '.join(json.dumps(arg) for arg in args)
        return self._ui_eval(
            'window.__quantumUI && window.__quantumUI.' + method + '(' + payload + ')'
        )

    def ui_set_state(self, args=None):
        \"\"\"Store a value reported by the UI component bridge.\"\"\"
        args = args or {}
        name = args.get('name')
        if not name:
            return False
        self.state.set(name, args.get('value'))
        return True"""]

        if self._toasts or self._toast_containers:
            blocks.append(self._generate_toast_methods())
        if self._carousels:
            blocks.append(self._generate_carousel_methods())
        if self._steppers:
            blocks.append(self._generate_stepper_methods())
        if self._calendars:
            blocks.append(self._generate_calendar_methods())
        if self._date_pickers:
            blocks.append(self._generate_date_picker_methods())

        return '\n\n'.join(blocks)

    def _generate_toast_methods(self) -> str:
        """QuantumAPI methods for ui:toast / ui:toast-container."""
        if self._toast_containers:
            position = self._toast_containers[0]['position']
        else:
            position = self._toasts[0]['position']
        duration = self._toasts[0]['duration'] if self._toasts else 3000

        return f"""\
    def ui_toast(self, args=None):
        \"\"\"Show a toast notification (ui:toast / ui:toast-container).\"\"\"
        args = args or {{}}
        options = {{
            'variant': args.get('variant', 'info'),
            'title': args.get('title'),
            'message': args.get('message', ''),
            'position': args.get('position', {position!r}),
            'duration': args.get('duration', {duration}),
            'dismissible': args.get('dismissible', True),
        }}
        if args.get('icon') is not None:
            options['icon'] = args.get('icon')
        return self._ui_call('toast', options)

    def ui_toast_dismiss_all(self, args=None):
        \"\"\"Dismiss every toast currently on screen.\"\"\"
        return self._ui_call('dismissToasts')"""

    def _generate_carousel_methods(self) -> str:
        """QuantumAPI methods for ui:carousel (and ui:slide when it has an id)."""
        code = """\
    def ui_carousel_goto(self, args=None):
        \"\"\"Show a slide of a ui:carousel: {'carousel': ref, 'index': n}.\"\"\"
        args = args or {}
        try:
            index = int(args.get('index', 0))
        except (TypeError, ValueError):
            index = 0
        return self._ui_call('carouselGoTo', args.get('carousel', 0), index)

    def ui_carousel_next(self, args=None):
        \"\"\"Advance a ui:carousel to the next slide.\"\"\"
        args = args or {}
        return self._ui_call('carouselNext', args.get('carousel', 0))

    def ui_carousel_prev(self, args=None):
        \"\"\"Move a ui:carousel back to the previous slide.\"\"\"
        args = args or {}
        return self._ui_call('carouselPrev', args.get('carousel', 0))"""

        has_slide_ids = any(
            slide['element_id'] for spec in self._carousels for slide in spec['slides']
        )
        if has_slide_ids:
            code += """

    def ui_slide_show(self, args=None):
        \"\"\"Show the ui:slide with the given id: {'slide': 'slide-id'}.\"\"\"
        args = args or {}
        return self._ui_call('showSlide', args.get('slide'))"""
        return code

    def _generate_stepper_methods(self) -> str:
        """QuantumAPI methods for ui:stepper (and ui:step when it has an id)."""
        code = """\
    def ui_stepper_goto(self, args=None):
        \"\"\"Jump a ui:stepper to a step: {'stepper': ref, 'index': n}.\"\"\"
        args = args or {}
        try:
            index = int(args.get('index', 0))
        except (TypeError, ValueError):
            index = 0
        return self._ui_call('stepperGoTo', args.get('stepper', 0), index)

    def ui_stepper_next(self, args=None):
        \"\"\"Advance a ui:stepper to the next step (honours linear mode).\"\"\"
        args = args or {}
        return self._ui_call('stepperNext', args.get('stepper', 0))

    def ui_stepper_prev(self, args=None):
        \"\"\"Move a ui:stepper back to the previous step.\"\"\"
        args = args or {}
        return self._ui_call('stepperPrev', args.get('stepper', 0))

    def ui_stepper_complete(self, args=None):
        \"\"\"Mark a ui:step as completed: {'stepper': ref, 'index': n}.\"\"\"
        args = args or {}
        index = args.get('index')
        if index is not None:
            try:
                index = int(index)
            except (TypeError, ValueError):
                index = None
        return self._ui_call('stepperComplete', args.get('stepper', 0), index)"""

        has_step_ids = any(
            step['element_id'] for spec in self._steppers for step in spec['steps']
        )
        if has_step_ids:
            code += """

    def ui_step_show(self, args=None):
        \"\"\"Show the ui:step with the given id: {'step': 'step-id'}.\"\"\"
        args = args or {}
        return self._ui_call('showStep', args.get('step'))"""
        return code

    def _generate_calendar_methods(self) -> str:
        """QuantumAPI methods for ui:calendar."""
        return """\
    def ui_calendar_select(self, args=None):
        \"\"\"Select a date in a ui:calendar: {'calendar': ref, 'value': ISO date}.

        Passing an empty value clears the current selection.
        \"\"\"
        args = args or {}
        return self._ui_call('calendarSelect', args.get('calendar', 0), args.get('value'))"""

    def _generate_date_picker_methods(self) -> str:
        """QuantumAPI methods for ui:date-picker."""
        return """\
    def ui_date_picker_set(self, args=None):
        \"\"\"Set a ui:date-picker value: {'picker': ref, 'value': ISO date}.\"\"\"
        args = args or {}
        return self._ui_call('datePickerSet', args.get('picker', 0), args.get('value'))"""

    # ------------------------------------------------------------------
    # Attribute helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _node_id(node: QuantumNode) -> Optional[str]:
        """Return the explicit id of a UI node (ui_id), if any."""
        return getattr(node, 'ui_id', None) or None

    @staticmethod
    def _bind_name(bind: Optional[str]) -> Optional[str]:
        """Normalize a binding reference ('{name}' and 'name' are the same)."""
        if not bind:
            return None
        name = str(bind).strip()
        if name.startswith('{') and name.endswith('}'):
            name = name[1:-1].strip()
        return name or None

    @staticmethod
    def _as_int(value: Any, default: int) -> int:
        """Coerce an attribute to int, falling back to a default."""
        if value is None or isinstance(value, bool):
            return default
        try:
            return int(str(value).strip())
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _as_bool(value: Any, default: bool) -> bool:
        """Coerce an attribute to bool, falling back to a default."""
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        text = str(value).strip().lower()
        if text in ('true', '1', 'yes', 'on'):
            return True
        if text in ('false', '0', 'no', 'off', ''):
            return False
        return default
