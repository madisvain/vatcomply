import React, { useState, useEffect } from "react";
import { Formik } from "formik";
import { map, isBoolean, isEmpty, upperFirst } from "lodash";

import axios from "axios";
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
      <div id="hero" className="container">
        <div className="row">
          <div className="col">
            <h2 className="text-center">VAT Number Validation API</h2>
          </div>
        </div>
        <div className="row">
          <div className="col">
            <Formik
              initialValues={{ vat_number: "" }}
              onSubmit={async (values, actions) => {
                const result = await axios(`https://api.vatcomply.com/vat?vat_number=${values.vat_number}`);
                setVAT(result.data);
              }}
            >
              {(props) => (
                <form className="form-inline justify-content-center" onSubmit={props.handleSubmit}>
                  <div className="form-group mx-sm-3 mb-2">
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
                  <button type="submit" className="btn btn-primary btn-lg mb-2">
                    Validate
                  </button>
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

      <div id="currency-rates" className="container">
        <div className="row">
          <div className="col">
            <h2 className="text-center">Currency rates API</h2>
            {!isEmpty(rates) ? (
              <table className="table table-borderless mt-4">
                <tbody>
                  {map(rates.rates, (value, key) => (
                    <tr key={key}>
                      <td className="text-right">{key}</td>
                      <td>{value}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : null}
          </div>
        </div>
      </div>

      <div id="geolocation" className="container">
        <div className="row">
          <div className="col">
            <h2 className="text-center">Geolocation API</h2>
            {!isEmpty(geolocation) ? (
              <p className="text-center mt-4">
                From your IP address {geolocation.ip}
                <br />
                it was determined that you are from {geolocation.country_code}
              </p>
            ) : null}
          </div>
        </div>
      </div>
    </Layout>
  );
};

export default Home;
