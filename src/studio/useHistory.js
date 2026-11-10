import { useCallback, useRef, useState } from "react";

const LIMIT = 100;

// Undo/redo over immutable values.
// commit(next, {coalesce: key}) merges rapid edits with the same key
// (e.g. typing in one input) into one history entry, so slider drags and
// keystrokes don't flood the stack.
export default function useHistory(initial) {
  const [state, setState] = useState({ past: [], present: initial, future: [] });
  const lastKey = useRef({ key: null, at: 0 });

  const commit = useCallback((next, opts = {}) => {
    setState((s) => {
      const value = typeof next === "function" ? next(s.present) : next;
      if (value === s.present) return s;
      const now = Date.now();
      const coalesce = opts.coalesce && lastKey.current.key === opts.coalesce && now - lastKey.current.at < 1200;
      lastKey.current = { key: opts.coalesce || null, at: now };
      if (coalesce) return { ...s, present: value, future: [] };
      return { past: [...s.past, s.present].slice(-LIMIT), present: value, future: [] };
    });
  }, []);

  const reset = useCallback((value) => {
    lastKey.current = { key: null, at: 0 };
    setState({ past: [], present: value, future: [] });
  }, []);

  const undo = useCallback(() => {
    lastKey.current = { key: null, at: 0 };
    setState((s) => (s.past.length ? {
      past: s.past.slice(0, -1), present: s.past[s.past.length - 1], future: [s.present, ...s.future],
    } : s));
  }, []);

  const redo = useCallback(() => {
    lastKey.current = { key: null, at: 0 };
    setState((s) => (s.future.length ? {
      past: [...s.past, s.present], present: s.future[0], future: s.future.slice(1),
    } : s));
  }, []);

  return {
    value: state.present, commit, reset, undo, redo,
    canUndo: state.past.length > 0, canRedo: state.future.length > 0,
  };
}
