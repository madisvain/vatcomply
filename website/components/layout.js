import React, { useState } from "react";
import Link from "next/link";

import Burger from "../components/burger";

const Layout = ({ children }) => {
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
          <li className="d-none d-sm-block">
            <a href="https://upcount.app/">
              <img src="/upcount.svg" width="72" height="19" />
              <br />
              Invoicing made easy
            </a>
          </li>
          <li>
            <a href="https://github.com/madisvain/vatcomply" target="_blank" rel="noopener noreferrer">
              <img src="/github.svg" width="32" height="32" />
            </a>
          </li>
          <li>
            <a
              href="https://status.vatcomply.com/"
              target="_blank"
              className="text-center"
              style={{ display: "block", fontSize: 18 }}
            >
              Status
            </a>
          </li>
          <li>
            <Link href="/documentation">
              <a className="text-center" style={{ display: "block", fontSize: 18, borderBottom: "2px solid #00022e" }}>
                API
              </a>
            </Link>
          </li>
          {/*<Burger menuOpen={menuOpen} setMenuOpen={setMenuOpen} />*/}
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
                <a className="link">API docs</a>
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

export default Layout;
