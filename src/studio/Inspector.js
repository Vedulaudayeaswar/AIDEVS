import React, { useEffect, useState } from "react";
import { CONTAINER_TYPES } from "./treeOps";

const TAGS = {
  section: ["section", "header", "footer", "nav", "main", "aside", "article", "div"],
  container: ["div", "section", "article", "aside", "header", "footer", "nav", "ul", "li"],
  heading: ["h1", "h2", "h3", "h4", "h5", "h6"],
  text: ["p", "span", "small", "blockquote", "li", "strong"],
};
const TEXT_TYPES = new Set(["heading", "text", "button", "link", "icon", "input", "textarea", "select"]);
const BP_LABEL = { base: "Desktop (base styles)", tablet: "Tablet override (≤1024px)", mobile: "Mobile override (≤640px)" };
const SHADOWS = {
  "": "None", "0 1px 3px rgba(0,0,0,0.12)": "Subtle", "0 8px 24px rgba(15,23,42,0.12)": "Medium",
  "0 20px 50px rgba(15,23,42,0.22)": "Large", "0 0 0 1px rgba(15,23,42,0.08)": "Hairline",
};
const FONTS = ["", "var(--font-heading)", "var(--font-body)", "Inter", "Poppins", "Playfair Display", "Space Grotesk",
  "DM Sans", "Merriweather", "monospace"];

// Text input that commits on change but keeps local state while typing.
function Field({ label, value, placeholder, onChange, type = "text", options, title, wide }) {
  const [local, setLocal] = useState(value ?? "");
  useEffect(() => setLocal(value ?? ""), [value]);
  const id = `f-${label.replace(/\W+/g, "-")}`;
  return (
    <div className={`st-field ${wide ? "wide" : ""}`} title={title}>
      <label htmlFor={id}>{label}</label>
      {options ? (
        <select id={id} className="aid-select" value={local} onChange={(e) => { setLocal(e.target.value); onChange(e.target.value); }}>
          {options.map((o) => (Array.isArray(o)
            ? <option key={o[0]} value={o[0]}>{o[1]}</option>
            : <option key={o} value={o}>{o || "—"}</option>))}
        </select>
      ) : type === "textarea" ? (
        <textarea id={id} className="aid-textarea" rows={3} value={local} placeholder={placeholder}
          onChange={(e) => { setLocal(e.target.value); onChange(e.target.value); }} />
      ) : (
        <input id={id} className="aid-input" type={type} value={local} placeholder={placeholder}
          onChange={(e) => { setLocal(e.target.value); onChange(e.target.value); }} />
      )}
    </div>
  );
}

function ColorField({ label, value, placeholder, tokens, onChange }) {
  const hex = /^#[0-9a-f]{6}$/i.test(value || "") ? value : "#000000";
  return (
    <div className="st-field wide">
      <label>{label}</label>
      <div className="st-color">
        <input type="color" aria-label={`${label} picker`} value={hex} onChange={(e) => onChange(e.target.value)} />
        <Field label={`${label} value`} value={value} placeholder={placeholder} onChange={onChange} />
      </div>
      <div className="st-swatches">
        {Object.entries((tokens && tokens.colors) || {}).map(([k, v]) => {
          const varName = `var(--color-${k.replace(/[A-Z]/g, (m) => `-${m.toLowerCase()}`)})`;
          return <button key={k} type="button" title={`${k} token`} style={{ background: v }}
            className={value === varName ? "on" : ""} onClick={() => onChange(varName)} aria-label={`Use ${k} token`} />;
        })}
      </div>
    </div>
  );
}

function Group({ title, children, defaultOpen = true }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <section className="st-group">
      <button type="button" className="st-group-head" aria-expanded={open} onClick={() => setOpen(!open)}>
        <span>{title}</span><span>{open ? "−" : "+"}</span>
      </button>
      {open && <div className="st-group-body">{children}</div>}
    </section>
  );
}

export default function Inspector({ node, parent, breakpoint, tokens, entities, assets, onProps, onStyles, onNode }) {
  if (!node) return <div className="st-empty">Select an element on the canvas or in the layers panel to edit it.</div>;
  const t = node.type;
  const p = node.props || {};
  const styles = node.styles || {};
  const own = styles[breakpoint] || {};
  const base = styles.base || {};
  // Value shown = this breakpoint's override, placeholder = inherited value.
  const sv = (prop) => own[prop] ?? "";
  const ph = (prop) => (breakpoint !== "base" && base[prop] ? `${base[prop]} (inherited)` : "");
  const set = (prop) => (value) => onStyles({ [prop]: value }, prop);
  const S = (label, prop, extra = {}) => (
    <Field key={prop} label={label} value={sv(prop)} placeholder={ph(prop) || extra.placeholder} onChange={set(prop)}
      options={extra.options} />
  );
  const isContainer = CONTAINER_TYPES.has(t);
  const display = own.display || base.display || "";
  const entity = (entities || []).find((e) => e.name === (t === "form" || t === "collection" ? p.entity : parent && parent.props && parent.props.entity));
  const formEntity = (entities || []).find((e) => e.name === (parent && parent.type === "form" ? parent.props.entity : null));
  const overrides = breakpoint !== "base" ? Object.keys(own) : [];

  return (
    <div className="st-inspector">
      <div className="st-insp-head">
        <div className="st-insp-type">{t}{node.shared ? " · shared on every page" : ""}</div>
        <Field label="Layer name" value={node.name} onChange={(v) => onNode({ name: v }, "name")} wide />
        {TAGS[t] && <Field label="HTML tag" value={node.tag} options={TAGS[t]} onChange={(v) => onNode({ tag: v }, "tag")} />}
        <div className="st-bp">{BP_LABEL[breakpoint]}{overrides.length > 0 && (
          <button type="button" className="st-link" onClick={() => onStyles(Object.fromEntries(overrides.map((k) => [k, ""])), "reset")}>
            reset {overrides.length} override(s)</button>)}</div>
      </div>

      <Group title="Content">
        {["heading", "text", "button", "link", "icon"].includes(t) && (
          <Field label="Text" type="textarea" value={p.text} onChange={(v) => onProps({ text: v }, "text")} wide />
        )}
        {["button", "link"].includes(t) && (
          <Field label="Link (URL, /page or #anchor)" value={p.href} placeholder={t === "button" ? "empty = form submit button" : ""}
            onChange={(v) => onProps({ href: v }, "href")} wide />
        )}
        {t === "button" && <Field label="Variant" value={p.variant || "primary"} options={["primary", "secondary", "ghost"]} onChange={(v) => onProps({ variant: v })} />}
        {t === "icon" && <Field label="Accessible label" value={p.label} onChange={(v) => onProps({ label: v }, "label")} />}
        {t === "image" && (
          <>
            <Field label="Image URL" value={p.src} placeholder="https://… or pick an asset" onChange={(v) => onProps({ src: v }, "src")} wide />
            {assets && assets.length > 0 && (
              <div className="st-asset-pick">
                {assets.slice(0, 12).map((a) => (
                  <button key={a.id} type="button" title={a.filename} onClick={() => onProps({ src: a.url })}>
                    <img src={a.absUrl} alt="" />
                  </button>
                ))}
              </div>
            )}
            <Field label="Alt text" value={p.alt} placeholder="Describe the image" onChange={(v) => onProps({ alt: v }, "alt")} wide />
          </>
        )}
        {(t === "section" || t === "container") && (
          <Field label="Anchor id (for #links)" value={p.anchor} placeholder="e.g. pricing" onChange={(v) => onProps({ anchor: v.toLowerCase().replace(/[^a-z0-9-]/g, "") }, "anchor")} />
        )}
        {(t === "form" || t === "collection") && (
          <Field label="Data model" value={p.entity || ""} options={[["", "—"], ...(entities || []).map((e) => [e.name, e.label])]}
            onChange={(v) => onProps({ entity: v })} wide />
        )}
        {t === "form" && <Field label="Success message" value={p.successMessage} onChange={(v) => onProps({ successMessage: v }, "succ")} wide />}
        {t === "collection" && (
          <>
            <Field label="Max items" type="number" value={p.limit} onChange={(v) => onProps({ limit: Number(v) || 12 }, "limit")} />
            <Field label="Empty text" value={p.emptyText} onChange={(v) => onProps({ emptyText: v }, "empty")} />
            {entity && <p className="st-note">Use {"{{field}}"} in child text/images: {entity.fields.map((f) => f.name).join(", ")}</p>}
          </>
        )}
        {["input", "textarea", "select"].includes(t) && (
          <>
            <Field label="Label" value={p.label} onChange={(v) => onProps({ label: v }, "label")} />
            <Field label="Field" value={p.name || ""}
              options={formEntity ? [["", "—"], ...formEntity.fields.map((f) => [f.name, `${f.name} (${f.type})`])] : undefined}
              onChange={(v) => onProps({ name: v }, "name")} />
            {t === "input" && <Field label="Input type" value={p.inputType || "text"} options={["text", "email", "tel", "number", "password", "url", "date"]} onChange={(v) => onProps({ inputType: v })} />}
            {t !== "select" && <Field label="Placeholder" value={p.placeholder} onChange={(v) => onProps({ placeholder: v }, "ph")} />}
            {t === "textarea" && <Field label="Rows" type="number" value={p.rows} onChange={(v) => onProps({ rows: Number(v) || 4 }, "rows")} />}
            {t === "select" && <Field label="Options (comma separated)" value={(p.options || []).join(", ")} onChange={(v) => onProps({ options: v.split(",").map((s) => s.trim()).filter(Boolean) }, "opts")} wide />}
            <label className="st-check"><input type="checkbox" checked={Boolean(p.required)} onChange={(e) => onProps({ required: e.target.checked })} /> Required</label>
          </>
        )}
        {t === "page" && <p className="st-note">The page root. Select a section to edit it, or add sections from the Add tab.</p>}
      </Group>

      <Group title="Layout">
        {isContainer && S("Display", "display", { options: ["", "block", "flex", "grid", "none"] })}
        {!isContainer && S("Display", "display", { options: ["", "block", "inline-block", "inline-flex", "flex", "none"] })}
        {display.includes("flex") && (
          <>
            {S("Direction", "flexDirection", { options: ["", "row", "column", "row-reverse", "column-reverse"] })}
            {S("Wrap", "flexWrap", { options: ["", "nowrap", "wrap"] })}
            {S("Justify", "justifyContent", { options: ["", "flex-start", "center", "flex-end", "space-between", "space-around", "space-evenly"] })}
            {S("Align", "alignItems", { options: ["", "stretch", "flex-start", "center", "flex-end", "baseline"] })}
          </>
        )}
        {display === "grid" && (
          <>
            {S("Columns", "gridTemplateColumns", { placeholder: "repeat(3, 1fr)" })}
            {S("Align items", "alignItems", { options: ["", "stretch", "start", "center", "end"] })}
          </>
        )}
        {(display.includes("flex") || display === "grid") && S("Gap", "gap", { placeholder: "24px" })}
        {S("Width", "width", { placeholder: "auto" })}
        {S("Height", "height", { placeholder: "auto" })}
        {S("Min height", "minHeight")}
        {S("Max width", "maxWidth")}
        {S("Position", "position", { options: ["", "static", "relative", "sticky", "absolute"] })}
        {(own.position || base.position) === "sticky" && S("Top", "top", { placeholder: "0" })}
        {S("Align self", "alignSelf", { options: ["", "auto", "flex-start", "center", "flex-end", "stretch"] })}
        {S("Order", "order")}
      </Group>

      <Group title="Spacing">
        {S("Margin", "margin", { placeholder: "0 auto" })}
        {S("Padding", "padding", { placeholder: "24px" })}
        <div className="st-quad">
          {["Top", "Right", "Bottom", "Left"].map((side) => S(`Pad ${side.toLowerCase()}`, `padding${side}`))}
        </div>
        <div className="st-quad">
          {["Top", "Right", "Bottom", "Left"].map((side) => S(`Margin ${side.toLowerCase()}`, `margin${side}`))}
        </div>
      </Group>

      {TEXT_TYPES.has(t) || isContainer ? (
        <Group title="Typography" defaultOpen={TEXT_TYPES.has(t)}>
          {S("Font", "fontFamily", { options: FONTS })}
          {S("Size", "fontSize", { placeholder: "16px" })}
          {S("Weight", "fontWeight", { options: ["", "300", "400", "500", "600", "700", "800", "900"] })}
          {S("Line height", "lineHeight", { placeholder: "1.5" })}
          {S("Letter spacing", "letterSpacing", { placeholder: "0.02em" })}
          {S("Align", "textAlign", { options: ["", "left", "center", "right", "justify"] })}
          {S("Transform", "textTransform", { options: ["", "none", "uppercase", "lowercase", "capitalize"] })}
          {S("Decoration", "textDecoration", { options: ["", "none", "underline"] })}
          <ColorField label="Text colour" value={sv("color")} placeholder={ph("color")} tokens={tokens} onChange={set("color")} />
        </Group>
      ) : null}

      <Group title="Appearance">
        <ColorField label="Background" value={sv("background")} placeholder={ph("background") || "color or gradient"} tokens={tokens} onChange={set("background")} />
        {S("Border", "border", { placeholder: "1px solid #e5e7eb" })}
        {S("Radius", "borderRadius", { placeholder: "var(--radius)" })}
        {S("Shadow", "boxShadow", { options: Object.entries(SHADOWS) })}
        <div className="st-field wide">
          <label htmlFor="f-opacity">Opacity {sv("opacity") || "1"}</label>
          <input id="f-opacity" type="range" min="0" max="1" step="0.05" value={sv("opacity") || base.opacity || 1}
            onChange={(e) => onStyles({ opacity: e.target.value === "1" ? "" : e.target.value }, "opacity")} />
        </div>
        {t === "image" && S("Object fit", "objectFit", { options: ["", "cover", "contain", "fill"] })}
        {t === "image" && S("Aspect ratio", "aspectRatio", { placeholder: "16 / 9" })}
        {S("Overflow", "overflow", { options: ["", "visible", "hidden", "auto"] })}
      </Group>
    </div>
  );
}
