import React, { useState } from "react";
import Link from "next/link";

import Burger from "../components/burger";

export default ({ children }) => {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <div>
      <nav id="header" className="navbar navbar-light">
        <Link href="/">
          <a id="logo">
            <h1>
              VAT
              <br />
              <small>comply</small>
            </h1>
          </a>
        </Link>
        <ul className="nav">
          <Burger menuOpen={menuOpen} setMenuOpen={setMenuOpen} />
        </ul>
      </nav>

      {children}

      <div id="menu" className={`overlay ${menuOpen ? "open" : ""}`}>
        <nav className="overlay-menu">
          <ul className="list-unstyled">
            <li>
              <Link href="/">
                <a className="link">Home</a>
              </Link>
            </li>
            <li>
              <Link href="/documentation">
                <a className="link">API</a>
              </Link>
            </li>
            {/*<li>
              <Link href="/about">
                <a className="link">About</a>
              </Link>
            </li>*/}
          </ul>
        </nav>
      </div>
    </div>
  );
};
