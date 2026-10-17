import type { SVGProps } from "react";

/** ParhLo mark: the sun rising behind a folded morning paper. Class names let GSAP animate the parts. */
export function LogoMark({ size = 40, ...props }: { size?: number } & SVGProps<SVGSVGElement>) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" role="img" aria-label="ParhLo" {...props}>
      <defs>
        <clipPath id="parhlo-horizon">
          <rect x="0" y="0" width="64" height="37" />
        </clipPath>
        <linearGradient id="parhlo-sun" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#FFC65C" />
          <stop offset="1" stopColor="#F2A93B" />
        </linearGradient>
      </defs>
      <rect width="64" height="64" rx="15" fill="#1d1d1f" />
      <g className="logo-rays" stroke="#F2A93B" strokeWidth="2.6" strokeLinecap="round">
        <line x1="32" y1="9" x2="32" y2="13.5" />
        <line x1="17.5" y1="15" x2="20.6" y2="18.2" />
        <line x1="46.5" y1="15" x2="43.4" y2="18.2" />
        <line x1="11" y1="28" x2="15.2" y2="28.8" />
        <line x1="53" y1="28" x2="48.8" y2="28.8" />
      </g>
      <g clipPath="url(#parhlo-horizon)">
        <circle className="logo-sun" cx="32" cy="37" r="13" fill="url(#parhlo-sun)" />
      </g>
      <g className="logo-paper">
        <path d="M13 37.5h38v13.5a3 3 0 0 1-3 3H16a3 3 0 0 1-3-3z" fill="#F7F4EC" />
        <path d="M13 37.5h38l-4 3.2H17z" fill="#E4DFD2" />
        <rect className="logo-line" x="18" y="43.5" width="28" height="2.2" rx="1.1" fill="#1d1d1f" />
        <rect className="logo-line" x="18" y="47.7" width="20" height="2.2" rx="1.1" fill="#1d1d1f" opacity=".55" />
      </g>
    </svg>
  );
}

export function Wordmark({ className = "" }: { className?: string }) {
  return (
    <span className={`font-masthead tracking-tight ${className}`}>
      Parh<span className="italic text-[#C9861F]">Lo</span>
    </span>
  );
}

export function Logo({ size = 34, className = "" }: { size?: number; className?: string }) {
  return (
    <span className={`inline-flex items-center gap-2.5 ${className}`}>
      <LogoMark size={size} />
      <Wordmark className="text-[26px] leading-none" />
    </span>
  );
}
