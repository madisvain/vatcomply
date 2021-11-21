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
        <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no" />
      </Head>
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
