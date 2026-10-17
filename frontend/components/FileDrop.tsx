"use client";

import { useRef, useState } from "react";

/** Drag-and-drop / click-to-pick file input. */
export function FileDrop({ onFiles, accept, multiple = true, hint, disabled }: {
  onFiles: (files: File[]) => void;
  accept?: string;
  multiple?: boolean;
  hint?: string;
  disabled?: boolean;
}) {
  const input = useRef<HTMLInputElement>(null);
  const [over, setOver] = useState(false);

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => !disabled && input.current?.click()}
      onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && input.current?.click()}
      onDragOver={(e) => {
        e.preventDefault();
        setOver(true);
      }}
      onDragLeave={() => setOver(false)}
      onDrop={(e) => {
        e.preventDefault();
        setOver(false);
        if (!disabled && e.dataTransfer.files.length) onFiles(Array.from(e.dataTransfer.files));
      }}
      className={`flex cursor-pointer flex-col items-center justify-center gap-1 rounded-[18px] border-2 border-dashed px-6 py-10 text-center transition-colors ${
        over ? "border-primary bg-[#e8f1fb]" : "border-hairline bg-pearl hover:border-primary/50"
      } ${disabled ? "pointer-events-none opacity-50" : ""}`}
    >
      <span className="text-[17px] font-semibold">Drop files here</span>
      <span className="caption text-ink-48">{hint ?? "or click to browse"}</span>
      <input
        ref={input}
        type="file"
        hidden
        accept={accept}
        multiple={multiple}
        onChange={(e) => {
          if (e.target.files?.length) onFiles(Array.from(e.target.files));
          e.target.value = "";
        }}
      />
    </div>
  );
}
