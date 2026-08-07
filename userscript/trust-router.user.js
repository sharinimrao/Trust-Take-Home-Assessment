// ==UserScript==
// @name         Trust Router — prompt classifier overlay
// @namespace    trust-take-home
// @version      0.1.0
// @description  Captures the prompt being drafted on claude.ai / chatgpt.com, sends it to a locally-running Trust Router instance, and surfaces the routing decision inline.
// @match        https://claude.ai/*
// @match        https://chatgpt.com/*
// @connect      127.0.0.1
// @grant        GM_xmlhttpRequest
// @run-at       document-idle
// ==/UserScript==

/**
 * Task 3 prototype: this is a userscript rather than a packaged browser
 * extension because it needs zero install/build step for a take-home demo
 * (Tampermonkey/Violentmonkey + "add script" is enough) and can read the
 * DOM of both claude.ai and chatgpt.com without a manifest or content
 * script bundling step.
 *
 * What it does:
 *   1. Watches the prompt composer on the current site.
 *   2. On a debounce, sends the current draft to the local router
 *      (POST http://127.0.0.1:8000/v1/route).
 *   3. Renders the routing decision (selected model + scored/random mode)
 *      as a small floating badge near the composer.
 *
 * What it deliberately does NOT do (see README "What would be needed for
 * production" section):
 *   - It does not auto-switch the model picker on either site. Both sites'
 *     model selectors are unstable, undocumented DOM structures that break
 *     on redesign, and clicking through a user's account UI without an
 *     explicit action feels like it crosses from "assistive tool" into
 *     "automating someone else's product" — a production version should
 *     use each provider's real API (where available) instead of DOM
 *     automation.
 *   - It does not transmit anything anywhere except the user's own
 *     localhost router instance.
 */
(function trustRouterOverlay() {
  'use strict';

  const ROUTER_URL = 'http://127.0.0.1:8000/v1/route';
  const DEBOUNCE_MS = 700;
  const MIN_PROMPT_LENGTH = 12;

  const SITE = location.hostname.includes('claude.ai') ? 'claude.ai' : 'chatgpt.com';

  const COMPOSER_SELECTORS =
    SITE === 'claude.ai'
      ? ['div[contenteditable="true"][data-testid="composer-input"]', 'div[contenteditable="true"]']
      : ['#prompt-textarea', 'div[contenteditable="true"]#prompt-textarea', 'textarea'];

  let badge = null;
  let debounceTimer = null;
  let lastClassifiedText = '';

  function findComposer() {
    for (const selector of COMPOSER_SELECTORS) {
      const el = document.querySelector(selector);
      if (el) return el;
    }
    return null;
  }

  function readComposerText(el) {
    if (!el) return '';
    if ('value' in el) return el.value || '';
    return el.innerText || el.textContent || '';
  }

  function ensureBadge() {
    if (badge) return badge;
    badge = document.createElement('div');
    badge.id = 'trust-router-badge';
    Object.assign(badge.style, {
      position: 'fixed',
      right: '16px',
      bottom: '96px',
      zIndex: 999999,
      maxWidth: '260px',
      padding: '10px 12px',
      borderRadius: '12px',
      background: '#ffffff',
      border: '1px solid #e3e6ea',
      boxShadow: '0 4px 16px rgba(16,21,28,0.12)',
      fontFamily:
        'IBM Plex Mono, ui-monospace, monospace',
      fontSize: '11px',
      color: '#5b6472',
      lineHeight: '1.5',
      display: 'none',
    });
    document.body.appendChild(badge);
    return badge;
  }

  function renderIdle() {
    const el = ensureBadge();
    el.style.display = 'none';
  }

  function renderLoading() {
    const el = ensureBadge();
    el.style.display = 'block';
    el.innerHTML = `<div style="color:#2c4a7c;font-weight:600;letter-spacing:.05em;text-transform:uppercase;font-size:10px;">TRUST ROUTER</div><div style="margin-top:4px;">Classifying prompt…</div>`;
  }

  function renderResult(result) {
    const el = ensureBadge();
    el.style.display = 'block';
    const mode = result.policy.selection_mode;
    const modeColor = mode === 'scored' ? '#2c4a7c' : '#c77d2e';
    el.innerHTML = `
      <div style="color:#2c4a7c;font-weight:600;letter-spacing:.05em;text-transform:uppercase;font-size:10px;">TRUST ROUTER</div>
      <div style="margin-top:6px;font-weight:600;color:#10151c;">${escapeHtml(result.selected_model)}</div>
      <div style="margin-top:2px;color:${modeColor};">${mode} · ${result.routing_latency_ms.toFixed(1)}ms</div>
      <div style="margin-top:6px;color:#5b6472;">Recommended for this prompt on ${SITE}.</div>
    `;
  }

  function renderError(message) {
    const el = ensureBadge();
    el.style.display = 'block';
    el.innerHTML = `<div style="color:#b3402a;font-weight:600;letter-spacing:.05em;text-transform:uppercase;font-size:10px;">TRUST ROUTER</div><div style="margin-top:4px;color:#b3402a;">${escapeHtml(
      message,
    )}</div>`;
  }

  function escapeHtml(str) {
    return String(str).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  }

  function classify(prompt) {
    renderLoading();
    const payload = JSON.stringify({ prompt, metadata: { include_explanations: false } });

    const onSuccess = (responseText, status) => {
      if (status !== 200) {
        renderError(`Router returned ${status}. Is it running on 127.0.0.1:8000?`);
        return;
      }
      try {
        renderResult(JSON.parse(responseText));
      } catch {
        renderError('Could not parse router response.');
      }
    };
    const onFailure = () => renderError('Could not reach local router. Start it with `uv run take-home-router serve`.');

    if (typeof GM_xmlhttpRequest === 'function') {
      GM_xmlhttpRequest({
        method: 'POST',
        url: ROUTER_URL,
        headers: { 'content-type': 'application/json' },
        data: payload,
        onload: (res) => onSuccess(res.responseText, res.status),
        onerror: onFailure,
      });
    } else {
      fetch(ROUTER_URL, { method: 'POST', headers: { 'content-type': 'application/json' }, body: payload })
        .then((res) => res.text().then((text) => onSuccess(text, res.status)))
        .catch(onFailure);
    }
  }

  function handleComposerChange() {
    const el = findComposer();
    const text = readComposerText(el).trim();

    if (debounceTimer) clearTimeout(debounceTimer);

    if (text.length < MIN_PROMPT_LENGTH) {
      renderIdle();
      lastClassifiedText = '';
      return;
    }
    if (text === lastClassifiedText) return;

    debounceTimer = setTimeout(() => {
      lastClassifiedText = text;
      classify(text);
    }, DEBOUNCE_MS);
  }

  function observeComposer() {
    const observer = new MutationObserver(() => handleComposerChange());
    observer.observe(document.body, { childList: true, subtree: true, characterData: true });
    document.addEventListener('input', handleComposerChange, true);
    document.addEventListener('keyup', handleComposerChange, true);
  }

  observeComposer();
})();
