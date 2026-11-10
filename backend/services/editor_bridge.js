/* AIDevs editor bridge — runs inside the sandboxed canvas iframe (opaque origin).
 * It never touches app data; it only reports user interactions to the parent
 * studio via postMessage and draws selection / drag overlays.
 * Protocol: messages carry {source: "aidevs-canvas"|"aidevs-studio", type, ...}.
 */
(function () {
  "use strict";
  var MODE = window.__AID_MODE__ || "edit";
  var parentWin = window.parent;
  var selectedId = null;
  var hoverId = null;
  var editingEl = null;

  function send(type, payload) {
    var msg = payload || {};
    msg.source = "aidevs-canvas";
    msg.type = type;
    parentWin.postMessage(msg, "*");
  }

  // ---------- console + error forwarding (bottom panel "Console") ----------
  ["log", "warn", "error", "info"].forEach(function (level) {
    var orig = console[level];
    console[level] = function () {
      try {
        send("console", { level: level, message: Array.prototype.map.call(arguments, String).join(" ").slice(0, 2000) });
      } catch (e) { /* ignore */ }
      return orig.apply(console, arguments);
    };
  });
  window.addEventListener("error", function (e) {
    send("console", { level: "error", message: String(e.message || "Error").slice(0, 2000) });
  });

  // ---------- overlay elements ----------
  var style = document.createElement("style");
  style.textContent =
    ".aid-ov{position:fixed;pointer-events:none;z-index:2147483640;box-sizing:border-box}" +
    ".aid-hover{border:1px dashed #6366f1}" +
    ".aid-sel{border:2px solid #6366f1}" +
    ".aid-label{position:absolute;top:-22px;left:-2px;background:#6366f1;color:#fff;font:600 11px/20px system-ui,sans-serif;padding:0 6px;border-radius:4px 4px 0 0;white-space:nowrap}" +
    ".aid-h{position:absolute;width:10px;height:10px;background:#fff;border:2px solid #6366f1;border-radius:2px;pointer-events:auto}" +
    ".aid-h-e{right:-6px;top:50%;margin-top:-5px;cursor:ew-resize}" +
    ".aid-h-s{bottom:-6px;left:50%;margin-left:-5px;cursor:ns-resize}" +
    ".aid-h-se{right:-6px;bottom:-6px;cursor:nwse-resize}" +
    ".aid-drop{position:fixed;background:#f59e0b;z-index:2147483641;pointer-events:none;border-radius:2px}" +
    ".aid-drop-inside{position:fixed;border:2px dashed #f59e0b;background:rgba(245,158,11,.08);z-index:2147483641;pointer-events:none}" +
    "[data-aid][contenteditable=true]{outline:2px solid #f59e0b!important;cursor:text}" +
    (MODE === "edit" ? "a,button{cursor:default}" : "");
  document.head.appendChild(style);

  function mk(cls) {
    var d = document.createElement("div");
    d.className = cls;
    d.style.display = "none";
    document.body.appendChild(d);
    return d;
  }
  var hoverBox = mk("aid-ov aid-hover");
  var selBox = mk("aid-ov aid-sel");
  var selLabel = document.createElement("div");
  selLabel.className = "aid-label";
  selBox.appendChild(selLabel);
  ["e", "s", "se"].forEach(function (dir) {
    var h = document.createElement("div");
    h.className = "aid-h aid-h-" + dir;
    h.setAttribute("data-handle", dir);
    selBox.appendChild(h);
  });
  var dropLine = mk("aid-drop");
  var dropInside = mk("aid-drop-inside");

  function byId(id) {
    if (!id || !/^[A-Za-z0-9_-]{1,40}$/.test(id)) return null;
    return document.querySelector('[data-aid="' + id + '"]');
  }
  function nodeEl(target) {
    while (target && target !== document.body) {
      if (target.nodeType === 1) {
        if (target.hasAttribute("data-aid")) return target;
        if (target.hasAttribute("data-aclone")) return byId(target.getAttribute("data-aclone"));
      }
      target = target.parentNode;
    }
    return null;
  }
  function place(box, el) {
    if (!el) { box.style.display = "none"; return; }
    var r = el.getBoundingClientRect();
    box.style.display = "block";
    box.style.left = r.left + "px";
    box.style.top = r.top + "px";
    box.style.width = r.width + "px";
    box.style.height = r.height + "px";
  }
  function describe(el) {
    var r = el.getBoundingClientRect();
    var cs = window.getComputedStyle(el);
    var parent = el.parentElement ? nodeEl(el.parentElement) : null;
    return {
      id: el.getAttribute("data-aid"),
      name: el.getAttribute("data-aname"),
      nodeType: el.getAttribute("data-atype"),
      tag: el.tagName.toLowerCase(),
      parentId: parent ? parent.getAttribute("data-aid") : null,
      rect: { x: r.left, y: r.top, width: r.width, height: r.height },
      computed: {
        display: cs.display, width: cs.width, height: cs.height, color: cs.color,
        backgroundColor: cs.backgroundColor, fontSize: cs.fontSize, fontFamily: cs.fontFamily,
        fontWeight: cs.fontWeight, padding: cs.padding, margin: cs.margin, flexDirection: cs.flexDirection
      }
    };
  }
  function refresh() {
    var sel = byId(selectedId);
    place(selBox, sel);
    if (sel) {
      selLabel.textContent = (sel.getAttribute("data-aname") || "") + " · " + sel.tagName.toLowerCase();
      var top = sel.getBoundingClientRect().top;
      selLabel.style.top = top < 24 ? "2px" : "-22px";
      var root = sel.getAttribute("data-atype") === "page";
      selBox.querySelectorAll(".aid-h").forEach(function (h) { h.style.display = root ? "none" : "block"; });
    }
    var hov = hoverId && hoverId !== selectedId ? byId(hoverId) : null;
    place(hoverBox, hov);
  }
  var scrollTimer = null;
  window.addEventListener("scroll", function () {
    refresh();
    clearTimeout(scrollTimer);
    scrollTimer = setTimeout(function () { send("scrolled", { y: window.scrollY }); }, 120);
  }, true);
  window.addEventListener("resize", refresh);

  function select(id, notify) {
    selectedId = id;
    refresh();
    var el = byId(id);
    if (el && notify) send("select", describe(el));
  }

  // ---------- inline text editing ----------
  var TEXT_TYPES = { heading: 1, text: 1, button: 1, link: 1 };
  function startInlineEdit(el) {
    if (!TEXT_TYPES[el.getAttribute("data-atype")]) return;
    if (el.closest("[data-acollection]")) return; // bound templates are edited in the inspector
    editingEl = el;
    el.setAttribute("contenteditable", "true");
    el.focus();
    var range = document.createRange();
    range.selectNodeContents(el);
    var s = window.getSelection();
    s.removeAllRanges();
    s.addRange(range);
  }
  function finishInlineEdit(commit) {
    if (!editingEl) return;
    var el = editingEl;
    editingEl = null;
    el.removeAttribute("contenteditable");
    if (commit) send("text-edit", { id: el.getAttribute("data-aid"), text: el.innerText.replace(/\n+$/, "") });
  }

  // ---------- pointer interactions ----------
  var drag = null; // {kind:'move'|'resize', ...}

  document.addEventListener("mousemove", function (e) {
    if (MODE !== "edit") return;
    if (drag) { onDragMove(e); return; }
    var el = nodeEl(e.target);
    var id = el ? el.getAttribute("data-aid") : null;
    if (id !== hoverId) {
      hoverId = id;
      refresh();
      send("hover", { id: id });
    }
  }, true);

  document.addEventListener("mousedown", function (e) {
    if (MODE !== "edit" || e.button !== 0) return;
    if (editingEl && editingEl.contains(e.target)) return;
    finishInlineEdit(true);
    var handle = e.target.getAttribute && e.target.getAttribute("data-handle");
    if (handle && selectedId) {
      var el = byId(selectedId);
      var r = el.getBoundingClientRect();
      drag = { kind: "resize", dir: handle, el: el, x: e.clientX, y: e.clientY, w: r.width, h: r.height,
               prevW: el.style.width, prevH: el.style.height };
      e.preventDefault();
      return;
    }
    var target = nodeEl(e.target);
    if (!target) return;
    e.preventDefault();
    var id = target.getAttribute("data-aid");
    if (id !== selectedId) select(id, true);
    if (target.getAttribute("data-atype") !== "page" && !target.hasAttribute("data-ashared")) {
      drag = { kind: "pending", el: target, x: e.clientX, y: e.clientY };
    }
  }, true);

  function onDragMove(e) {
    if (drag.kind === "pending") {
      if (Math.abs(e.clientX - drag.x) + Math.abs(e.clientY - drag.y) < 6) return;
      drag.kind = "move";
      drag.el.style.opacity = "0.45";
    }
    if (drag.kind === "resize") {
      var dw = e.clientX - drag.x, dh = e.clientY - drag.y;
      if (drag.dir === "e" || drag.dir === "se") drag.el.style.width = Math.max(16, Math.round(drag.w + dw)) + "px";
      if (drag.dir === "s" || drag.dir === "se") drag.el.style.height = Math.max(8, Math.round(drag.h + dh)) + "px";
      refresh();
      return;
    }
    if (drag.kind === "move") {
      dropLine.style.display = "none";
      dropInside.style.display = "none";
      var under = document.elementFromPoint(e.clientX, e.clientY);
      var t = nodeEl(under);
      drag.drop = null;
      if (!t || t === drag.el || drag.el.contains(t)) return;
      var r = t.getBoundingClientRect();
      var isContainer = t.hasAttribute("data-acontainer");
      var parent = t.parentElement ? nodeEl(t.parentElement) : null;
      var innerZone = isContainer && (t.children.length === 0 ||
        (e.clientY > r.top + r.height * 0.25 && e.clientY < r.bottom - r.height * 0.25 &&
         e.clientX > r.left + r.width * 0.25 && e.clientX < r.right - r.width * 0.25));
      if (t.getAttribute("data-atype") === "page" || (innerZone && !t.hasAttribute("data-acollection"))) {
        drag.drop = { targetId: t.getAttribute("data-aid"), position: "inside" };
        place(dropInside, t);
        return;
      }
      if (!parent || t.hasAttribute("data-ashared")) return;
      var pcs = window.getComputedStyle(parent);
      var horizontal = pcs.display.indexOf("flex") !== -1 && pcs.flexDirection.indexOf("row") === 0 ||
                       pcs.display.indexOf("grid") !== -1 && r.width < parent.getBoundingClientRect().width * 0.8;
      var before = horizontal ? e.clientX < r.left + r.width / 2 : e.clientY < r.top + r.height / 2;
      drag.drop = { targetId: t.getAttribute("data-aid"), position: before ? "before" : "after" };
      dropLine.style.display = "block";
      if (horizontal) {
        dropLine.style.left = (before ? r.left - 2 : r.right - 2) + "px";
        dropLine.style.top = r.top + "px"; dropLine.style.width = "4px"; dropLine.style.height = r.height + "px";
      } else {
        dropLine.style.left = r.left + "px"; dropLine.style.width = r.width + "px";
        dropLine.style.top = (before ? r.top - 2 : r.bottom - 2) + "px"; dropLine.style.height = "4px";
      }
    }
  }

  document.addEventListener("mouseup", function () {
    if (!drag) return;
    var d = drag;
    drag = null;
    dropLine.style.display = "none";
    dropInside.style.display = "none";
    if (d.kind === "resize") {
      var payload = { id: d.el.getAttribute("data-aid") };
      if (d.dir === "e" || d.dir === "se") payload.width = d.el.style.width;
      if (d.dir === "s" || d.dir === "se") payload.height = d.el.style.height;
      // Reset inline preview; the studio re-renders from the real styles.
      d.el.style.width = d.prevW; d.el.style.height = d.prevH;
      send("resize", payload);
    } else if (d.kind === "move") {
      d.el.style.opacity = "";
      if (d.drop) send("move", { id: d.el.getAttribute("data-aid"), targetId: d.drop.targetId, position: d.drop.position });
    }
    refresh();
  }, true);

  document.addEventListener("dblclick", function (e) {
    if (MODE !== "edit") return;
    var el = nodeEl(e.target);
    if (el) { e.preventDefault(); startInlineEdit(el); }
  }, true);

  document.addEventListener("click", function (e) {
    var link = e.target.closest ? e.target.closest("a[href]") : null;
    if (MODE === "edit") {
      if (!editingEl) e.preventDefault();
      return;
    }
    if (link) {
      var href = link.getAttribute("href") || "";
      if (href.charAt(0) === "#") return; // in-page anchors work natively
      e.preventDefault();
      send("navigate", { href: href.slice(0, 2048) });
    }
  }, true);

  document.addEventListener("keydown", function (e) {
    if (editingEl) {
      if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); finishInlineEdit(true); }
      if (e.key === "Escape") { e.preventDefault(); finishInlineEdit(false); send("rerender", {}); }
      return;
    }
    if (MODE !== "edit") return;
    var tag = (e.target.tagName || "").toLowerCase();
    if (tag === "input" || tag === "textarea" || tag === "select") return;
    send("key", { key: e.key, ctrl: e.ctrlKey || e.metaKey, shift: e.shiftKey });
    if (e.key === "Delete" || e.key === "Backspace" || ((e.ctrlKey || e.metaKey) && /^[zyd]$/i.test(e.key))) {
      e.preventDefault();
    }
  }, true);

  // ---------- forms (interact mode) -> parent performs the real API call ----------
  // The sandbox has no allow-forms, so native submission never happens; we
  // capture submit buttons / Enter ourselves and hand the data to the studio.
  var formSeq = 0;
  document.addEventListener("submit", function (e) { e.preventDefault(); }, true);
  document.addEventListener("click", function (e) {
    if (MODE === "edit") return;
    var btn = e.target.closest ? e.target.closest("button[type=submit]") : null;
    var form = btn ? btn.closest("form[data-aform]") : null;
    if (form) { e.preventDefault(); submitForm(form); }
  }, true);
  document.addEventListener("keydown", function (e) {
    if (MODE === "edit" || e.key !== "Enter") return;
    var tag = (e.target.tagName || "").toLowerCase();
    var form = e.target.closest ? e.target.closest("form[data-aform]") : null;
    if (form && tag === "input") { e.preventDefault(); submitForm(form); }
  }, true);

  function submitForm(form) {
    var status = form.querySelector(".aid-form-status");
    if (!form.checkValidity()) { form.reportValidity(); return; }
    var data = {};
    Array.prototype.forEach.call(form.elements, function (el) {
      if (el.name) data[el.name] = el.type === "checkbox" ? el.checked : el.value;
    });
    formSeq += 1;
    form.setAttribute("data-aform-seq", String(formSeq));
    if (status) { status.removeAttribute("data-state"); status.textContent = "Sending…"; }
    send("submit", { formSeq: formSeq, entity: form.getAttribute("data-aform"), data: data });
  }

  // ---------- messages from the studio ----------
  window.addEventListener("message", function (e) {
    if (e.source !== parentWin) return;
    var m = e.data;
    if (!m || m.source !== "aidevs-studio" || typeof m.type !== "string") return;
    if (m.type === "select") { select(m.id, false); var el = byId(m.id);
      if (el && m.scroll) el.scrollIntoView({ block: "nearest", behavior: "smooth" }); }
    else if (m.type === "hover") { hoverId = m.id; refresh(); }
    else if (m.type === "scroll") { window.scrollTo(0, Number(m.y) || 0); }
    else if (m.type === "form-result") {
      var f = document.querySelector('[data-aform-seq="' + Number(m.formSeq) + '"]');
      if (f) {
        var st = f.querySelector(".aid-form-status");
        if (st) { st.setAttribute("data-state", m.ok ? "ok" : "error");
          st.textContent = String(m.message || (m.ok ? f.getAttribute("data-success") || "Saved." : "Something went wrong.")); }
        if (m.ok) f.reset();
      }
    }
  });

  send("ready", { mode: MODE, scrollHeight: document.documentElement.scrollHeight });
})();
