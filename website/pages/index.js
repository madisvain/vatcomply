import React, { useState, useEffect } from "react";
import { Formik } from "formik";
import { map, isBoolean, isEmpty, upperFirst } from "lodash";

import axios from "axios";
import Head from "next/head";
import Link from "next/link";

import Layout from "../components/layout";

const Home = () => {
  const [vat, setVAT] = useState({});
  const [geolocation, setGeolocation] = useState({});
  const [rates, setRates] = useState({});

  /* Geolocation */
  useEffect(() => {
    const fetchGeolocation = async () => {
      const result = await axios(`https://api.vatcomply.com/geolocate`);
      setGeolocation(result.data);
    };
    fetchGeolocation();
  }, []);

  /* Rates */
  useEffect(() => {
    const fetchRates = async () => {
      const result = await axios(`https://api.vatcomply.com/rates`);
      setRates(result.data);
    };
    fetchRates();
  }, []);

  return (
    <Layout>
      <Head>
        <title>VAT validation, geolocation and exchange rates API</title>
        <meta charSet="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no" />
      </Head>

      <div id="hero" className="container">
        <div className="row">
          <div className="col">
            <h2 className="text-center">VAT Number Validation API</h2>
            <p style={{ fontSize: 12, textAlign: "center" }}>
              You can verify the validity of a VAT number issued by any Member State /
              <br />
              Northern Ireland by entering the number to be validated in the form or use the{" "}
              <Link href="https://www.vatcomply.com/documentation#vat">
                <a>API</a>
              </Link>{" "}
              for automation.
            </p>
          </div>
        </div>
        <div className="row justify-content-center">
          <div className="col-4">
            <Formik
              initialValues={{ vat_number: "" }}
              onSubmit={async (values, actions) => {
                const result = await axios(`https://api.vatcomply.com/vat?vat_number=${values.vat_number}`);
                setVAT(result.data);
              }}
            >
              {(props) => (
                <form onSubmit={props.handleSubmit}>
                  <div className="row">
                    <div className="col-8">
                      <input
                        type="text"
                        className="form-control form-control-lg"
                        name="vat_number"
                        placeholder="VAT number"
                        onChange={props.handleChange}
                        onBlur={props.handleBlur}
                        value={props.values.vat_number}
                      />
                    </div>
                    <div className="col-4">
                      <button type="submit" className="btn btn-primary btn-lg mb-2">
                        Validate
                      </button>
                    </div>
                  </div>
                </form>
              )}
            </Formik>
          </div>
        </div>
      </div>

      {!isEmpty(vat) ? (
        <div id="results">
          <div className="row justify-content-center">
            <div className="col-xs-12 col-sm-10 col-md-8 col-lg-6">
              <div className="card boxed">
                <div className="card-body">
                  {map(vat, (value, key) => (
                    <dl className="row" key={key}>
                      <dt className="col-sm-3 text-right">{upperFirst(key).replace("_", " ")}</dt>
                      <dd className="col-sm-9">{isBoolean(value) ? (value ? "Yes" : "No") : value}</dd>
                    </dl>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      ) : null}

      <div id="geolocation" className="container">
        <div className="row">
          <div className="col">
            <h2 className="text-center">Geolocation API</h2>
            <p style={{ fontSize: 12, textAlign: "center" }}>
              Locate and identify website visitors by IP address. The free geocoding{" "}
              <Link href="https://www.vatcomply.com/documentation#geolocation">
                <a>API</a>
              </Link>{" "}
              uses{" "}
              <a
                href="https://support.cloudflare.com/hc/en-us/articles/200168236-Configuring-Cloudflare-IP-Geolocation"
                target="_blank"
              >
                CloudFlare
              </a>{" "}
              IP Geolocation
              <br />
              to which additional information about the geolocated country is provided.
            </p>
            {!isEmpty(geolocation) ? (
              <p className="text-center mt-4">
                From your IP address {geolocation.ip}
                <br />
                it was determined that you are from <strong>{geolocation.name}</strong> {geolocation.emoji} with
                currency <strong>{geolocation.currency}</strong>
              </p>
            ) : null}
          </div>
        </div>
      </div>

      <div id="currency-rates" className="container">
        <div className="row">
          <div className="col">
            <h2 className="text-center">Exchange rates API</h2>
            <p style={{ fontSize: 12, textAlign: "center" }}>
              <Link href="https://www.vatcomply.com/documentation#rates">
                <a>Exchange rates API</a>
              </Link>{" "}
              is a free service for current and historical
              <br />
              foreign exchange rates published by the European Central Bank.
            </p>
            <div className="d-flex justify-content-center">
              {!isEmpty(rates) ? (
                <table className="table table-striped mt-4" style={{ width: 240 }}>
                  <thead>
                    <tr>
                      <th>Currency</th>
                      <th>Rate</th>
                    </tr>
                  </thead>
                  <tbody>
                    {map(rates.rates, (value, key) => (
                      <tr key={key}>
                        <td>{key}</td>
                        <td>{value}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : null}
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
};

export default Home;
