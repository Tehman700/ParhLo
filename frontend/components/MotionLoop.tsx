/** ParhLo in one shape: a silent 14-second loop (public/motion/parhlo-morph.html).
 *  Every frame is computed from time; it shows a still frame when the visitor prefers reduced motion.
 *  `bg` is the hex colour of the surface it sits on, so the loop has no visible box.
 *  `wide` crops the square stage to its 16:10 middle band (every state fits there), so the UI reads larger.
 *  `once` plays a single cycle and posts {type: "parhlo-tour", event: "start" | "end"} to this window (tour player). */
export function MotionLoop({ bg = "ffffff", wide = false, once = false, className = "" }: { bg?: string; wide?: boolean; once?: boolean; className?: string }) {
  return (
    <div className={`relative w-full overflow-hidden rounded-[18px] ${wide ? "aspect-[16/10]" : "aspect-square"} ${className}`}>
      <iframe
        src={`/motion/parhlo-morph.html?bg=${bg}${once ? "&once=1" : ""}`}
        title="ParhLo in 14 seconds"
        aria-hidden="true"
        tabIndex={-1}
        loading={once ? "eager" : "lazy"}
        className={`pointer-events-none absolute left-0 block w-full border-0 ${wide ? "top-[-30%] h-[160%]" : "top-0 h-full"}`}
      />
    </div>
  );
}
