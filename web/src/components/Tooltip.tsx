"use client";

import React from "react";

type TooltipProps = {
  label: string;
  children: React.ReactElement<any>;
  side?: "top" | "bottom" | "left" | "right";
};

export default function Tooltip({ label, children, side = "top" }: TooltipProps) {
  return (
    <span className="tooltip-wrap" data-tooltip-side={side}>
      {React.cloneElement(children, { title: label, "aria-label": label })}
      <span className="tooltip-bubble" role="tooltip">{label}</span>
    </span>
  );
}
