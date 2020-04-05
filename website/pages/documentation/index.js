import React, { useEffect, useRef } from "react";

import Link from "next/link";

import Layout from "../../components/layout";
import VAT from "./vat";
import Rates from "./rates";
import Geolocation from "./geolocation";
import Countries from "./countries";
import Currencies from "./Currencies";

const Documentation = () => {
  return (
    <Layout>
      <div className="container-fluid">
        <div className="row justify-content-between">
          <div id="sidebar" className="col-sm-3">
            <ul className="list-unstyled">
              <li>
                <Link href="#vat">
                  <a>VAT validation</a>
                </Link>
              </li>
              <li>
                <Link href="#rates">
                  <a>Rates</a>
                </Link>
                <ul>
                  <li>
                    <Link href="#rates-latest">
                      <a>Latest</a>
                    </Link>
                  </li>
                  <li>
                    <Link href="#rates-base">
                      <a>Base rate</a>
                    </Link>
                  </li>
                  <li>
                    <Link href="#rates-date">
                      <a>Date</a>
                    </Link>
                  </li>
                </ul>
              </li>
              <li>
                <Link href="#currencies">
                  <a>Currencies</a>
                </Link>
              </li>
              <li>
                <Link href="#geolocation">
                  <a>Geolocation</a>
                </Link>
              </li>
              {/*<li>
                <Link href="#countries">
                  <a>Countries</a>
                </Link>
              </li>*/}
            </ul>
          </div>
          <div id="documentation" className="col-sm-9">
            <VAT />
            <Rates />
            <Currencies />
            <Geolocation />
            {/*<Countries />*/}
          </div>
        </div>
      </div>
    </Layout>
  );
};

export default Documentation;
