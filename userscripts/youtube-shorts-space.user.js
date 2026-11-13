// ==UserScript==
// @name         YouTube Shorts Spacebar
// @namespace    https://github.com/Tjabooo
// @version      1.0.1
// @description  Toggle the visible Short with Space.
// @match        https://www.youtube.com/*
// @noframes
// @grant        none
// @downloadURL  none
// ==/UserScript==

(() => {
    'use strict';

    const controls = 'input, textarea, select, button, a[href], summary, [role="button"], [role="checkbox"], [role="combobox"], [role="link"], [role="menuitem"], [role="slider"], [role="switch"], [role="textbox"]';

    function visibleShort() {
        let currentVideo;
        let largestArea = 0;
        for (const video of document.querySelectorAll('ytd-shorts video')) {
            if (!video.currentSrc || video.readyState < HTMLMediaElement.HAVE_METADATA) continue;
            if (getComputedStyle(video).visibility !== 'visible') continue;
            const rect = video.getBoundingClientRect();
            const width = Math.min(rect.right, window.innerWidth) - Math.max(rect.left, 0);
            const height = Math.min(rect.bottom, window.innerHeight) - Math.max(rect.top, 0);
            if (width <= 0 || height <= 0 || width * height <= largestArea) continue;
            currentVideo = video;
            largestArea = width * height;
        }
        return currentVideo;
    }

    window.addEventListener('keydown', event => {
        // YouTube navigates between pages without reloading the document.
        if (!location.pathname.startsWith('/shorts/') || event.key !== ' ') return;
        if (event.defaultPrevented || event.isComposing ||
            event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return;
        if (event.composedPath().some(node =>
            node instanceof Element && (node.isContentEditable || node.matches(controls)))) return;

        const video = visibleShort();
        if (!video) return;
        event.preventDefault();
        event.stopImmediatePropagation();
        if (event.repeat) return;

        if (video.paused) {
            video.play().catch(() => {});
        } else {
            video.pause();
        }
    }, true);
})();
