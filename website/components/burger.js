import React, { useState } from "react";

const Burger = ({ menuOpen, setMenuOpen }) => {
  return (
    <div className={`plate ${menuOpen ? "active" : ""}`} onClick={() => setMenuOpen(!menuOpen)}>
      <svg className="burger" version="1.1" height="100" width="100" viewBox="0 0 100 100">
        <path className="line line1" d="M 30,65 H 70" />
        <path
          className="line line2"
          d="M 70,50 H 30 C 30,50 18.644068,50.320751 18.644068,36.016949 C 18.644068,21.712696 24.988973,6.5812347 38.79661,11.016949 C 52.604247,15.452663 46.423729,62.711864 46.423729,62.711864 L 50.423729,49.152542 L 50.423729,16.101695"
        />
        <path
          className="line line3"
          d="M 30,35 H 70 C 70,35 80.084746,36.737688 80.084746,25.423729 C 80.084746,19.599612 75.882239,9.3123528 64.711864,13.559322 C 53.541489,17.806291 54.423729,62.711864 54.423729,62.711864 L 50.423729,49.152542 V 16.101695"
        />
      </svg>
      <svg className="x" version="1.1" height="100" width="100" viewBox="0 0 100 100">
        <path className="line" d="M 34,32 L 66,68" />
        <path className="line" d="M 66,32 L 34,68" />
      </svg>
    </div>
  );
};

export default Burger;
