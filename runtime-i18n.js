/**
 * Antigravity.app 渲染进程实时汉化引擎
 * 由 patch.py 在打包时与 zh-CN.json 一起注入到 dist/preload.js
 */
(function initAntigravityI18n(dict) {
  if (!dict || typeof window === 'undefined') {
    return;
  }

  const exactMap = dict.exact || {};
  const compiledPatterns = (dict.patterns || []).map((item) => ({
    regex: new RegExp(item.regex),
    replace: item.replace,
  }));

  // 忽略代码编辑器、代码块、终端、公式等不应翻译的容器
  const SKIP_TAGS = new Set([
    'SCRIPT',
    'STYLE',
    'NOSCRIPT',
    'CODE',
    'PRE',
    'TEXTAREA',
    'INPUT',
    'SVG',
    'MATH',
    'KBD',
  ]);

  const SKIP_SELECTOR =
    '[contenteditable="true"], [contenteditable=""], .monaco-editor, .cm-editor, .xterm, .prism-code, .katex, [data-no-i18n]';

  function translateText(raw) {
    if (!raw || typeof raw !== 'string') {
      return raw;
    }
    const trimmed = raw.trim();
    if (!trimmed) {
      return raw;
    }
    // 已经包含中文字符且不在精确词典中时直接跳过，避免重复替换
    const direct = exactMap[trimmed];
    if (direct !== undefined) {
      const lead = raw.slice(0, raw.indexOf(trimmed));
      const tail = raw.slice(raw.indexOf(trimmed) + trimmed.length);
      return lead + direct + tail;
    }
    if (/[\u4e00-\u9fa5]/.test(trimmed)) {
      return raw;
    }
    for (let i = 0; i < compiledPatterns.length; i++) {
      const { regex, replace } = compiledPatterns[i];
      if (regex.test(trimmed)) {
        const replaced = trimmed.replace(regex, replace);
        const lead = raw.slice(0, raw.indexOf(trimmed));
        const tail = raw.slice(raw.indexOf(trimmed) + trimmed.length);
        return lead + replaced + tail;
      }
    }
    return raw;
  }

  function shouldSkipNode(node) {
    const el = node.nodeType === 1 ? node : node.parentElement;
    if (!el) {
      return true;
    }
    if (SKIP_TAGS.has(el.tagName)) {
      return true;
    }
    if (typeof el.closest === 'function' && el.closest(SKIP_SELECTOR)) {
      return true;
    }
    return false;
  }

  const ATTRS_TO_TRANSLATE = ['placeholder', 'title', 'aria-label'];

  function translateElementAttrs(el) {
    if (!el || el.nodeType !== 1) {
      return;
    }
    if ( el.tagName !== 'INPUT' && el.tagName !== 'TEXTAREA' && shouldSkipNode(el)) {
      return;
    }
    for (let i = 0; i < ATTRS_TO_TRANSLATE.length; i++) {
      const attr = ATTRS_TO_TRANSLATE[i];
      const val = el.getAttribute(attr);
      if (val) {
        const next = translateText(val);
        if (next !== val) {
          el.setAttribute(attr, next);
        }
      }
    }
  }

  function translateTextNode(textNode) {
    if (!textNode || textNode.nodeType !== 3) {
      return;
    }
    if (shouldSkipNode(textNode)) {
      return;
    }
    const val = textNode.nodeValue;
    if (!val || !val.trim()) {
      return;
    }
    const next = translateText(val);
    if (next !== val) {
      textNode.nodeValue = next;
    }
  }

  function walkAndTranslate(root) {
    if (!root) {
      return;
    }
    if (root.nodeType === 3) {
      translateTextNode(root);
      return;
    }
    if (root.nodeType !== 1 && root.nodeType !== 9 && root.nodeType !== 11) {
      return;
    }
    if (root.nodeType === 1) {
      translateElementAttrs(root);
      if (SKIP_TAGS.has(root.tagName)) {
        return;
      }
    }
    const walker = document.createTreeWalker(
      root,
      NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT,
      null
    );
    let current = walker.nextNode();
    while (current) {
      if (current.nodeType === 3) {
        translateTextNode(current);
      } else if (current.nodeType === 1) {
        translateElementAttrs(current);
      }
      current = walker.nextNode();
    }
  }

  // 递归汉化右键菜单项
  function translateMenuItems(items) {
    if (!Array.isArray(items)) {
      return items;
    }
    return items.map((item) => {
      if (!item || typeof item !== 'object') {
        return item;
      }
      const next = { ...item };
      if (typeof next.label === 'string') {
        next.label = translateText(next.label);
      }
      if (Array.isArray(next.submenu)) {
        next.submenu = translateMenuItems(next.submenu);
      }
      return next;
    });
  }

  window.__ANTIGRAVITY_I18N__ = {
    translateText,
    translateMenuItems,
    walkAndTranslate,
  };

  function startObserver() {
    if (!document.body) {
      return;
    }
    walkAndTranslate(document.body);

    const observer = new MutationObserver((mutations) => {
      for (let i = 0; i < mutations.length; i++) {
        const m = mutations[i];
        if (m.type === 'characterData') {
          translateTextNode(m.target);
        } else if (m.type === 'attributes') {
          translateElementAttrs(m.target);
        } else if (m.type === 'childList') {
          for (let j = 0; j < m.addedNodes.length; j++) {
            walkAndTranslate(m.addedNodes[j]);
          }
        }
      }
    });

    observer.observe(document.body, {
      childList: true,
      subtree: true,
      characterData: true,
      attributes: true,
      attributeFilter: ATTRS_TO_TRANSLATE,
    });
  }

  if (document.readyState === 'loading') {
    window.addEventListener('DOMContentLoaded', startObserver, { once: true });
  } else {
    startObserver();
  }
})(__ANTIGRAVITY_ZH_DICT__);
