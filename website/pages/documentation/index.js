import Head from "next/head";
import Link from "next/link";

import Layout from "../../components/layout";
import VAT from "./vat";
import Rates from "./rates";
import Geolocation from "./geolocation";
import Currencies from "./currencies";

const Documentation = () => {
  return (
    <Layout>
      <Head>
        <title>VAT validation, geolocation and exchange rates API.</title>
        <meta charSet="utf-8" />
        <meta
          name="description"
          content="VAT number validation, geolocation and exchange rates API for VAT compliance."
        />
        <meta
          name="viewport"
          content="width=device-width, initial-scale=1, shrink-to-fit=no"
        />
      </Head>
      <div className="container-fluid">
        <div className="row justify-content-between">
          <div id="sidebar" className="col-sm-3">
            <ul className="list-unstyled">
              <li>
                <Link href="#vat">VAT validation</Link>
              </li>
              <li>
                <Link href="#rates">Rates</Link>
                <ul>
                  <li>
                    <Link href="#rates-latest">Latest</Link>
                  </li>
                  <li>
                    <Link href="#rates-base">Base rate</Link>
                  </li>
                  <li>
                    <Link href="#rates-date">Date</Link>
                  </li>
                </ul>
              </li>
              <li>
                <Link href="#currencies">Currencies</Link>
              </li>
              <li>
                <Link href="#geolocation">Geolocation</Link>
              </li>
              {/*<li>
                <Link href="#countries">
                  Countries
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
