// Positions a fixed-position chart tooltip next to the cursor, flipping it to
// the other side of the cursor (and clamping it) so it never runs off-screen.
//
// Expects the tooltip to be position: fixed (coordinates are viewport-based,
// matching event.clientX / event.clientY).
export function positionTooltip(tooltipEl, event, { offset = 12, margin = 8 } = {}) {
  if (!tooltipEl) return;

  // Reset to the origin before measuring. A fixed element near the right edge
  // gets squeezed by the available space (text wraps), which would give us a
  // wrong width. At 0,0 it has the whole viewport to lay out in.
  tooltipEl.style.left = "0px";
  tooltipEl.style.top = "0px";
  const { width, height } = tooltipEl.getBoundingClientRect();

  const vw = document.documentElement.clientWidth;
  const vh = window.innerHeight;

  let left = event.clientX + offset;
  let top = event.clientY + offset;

  // Flip to the left of / above the cursor if it would overflow
  if (left + width > vw - margin) left = event.clientX - offset - width;
  if (top + height > vh - margin) top = event.clientY - offset - height;

  // Final clamp, in case it doesn't fit either way (tiny screens)
  left = Math.max(margin, Math.min(left, vw - width - margin));
  top = Math.max(margin, Math.min(top, vh - height - margin));

  tooltipEl.style.left = `${left}px`;
  tooltipEl.style.top = `${top}px`;
}
