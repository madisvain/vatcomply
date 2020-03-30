import React, { useState, useEffect } from "react";
import { Formik } from "formik";
import { map, isBoolean, isEmpty, upperFirst } from "lodash";

import axios from "axios";

import Burger from "../components/burger";

const Home = () => {
  const [result, setResult] = useState({});

  return (
    <div>
      <nav className="navbar navbar-light">
        <h1 id="logo">
          VAT
          <br />
          <small>comply</small>
        </h1>
        <ul className="nav">
          <Burger />
        </ul>
      </nav>
      <div id="hero" className="container">
        <div className="row">
          <div className="col">
            <h2 className="text-center">
              VAT Number Validation &<br /> VAT Rates API
            </h2>
          </div>
        </div>
        <div className="row">
          <div className="col">
            <Formik
              initialValues={{ vat_number: "" }}
              onSubmit={async (values, actions) => {
                const result = await axios(`http://localhost:8000/vat?vat_number=${values.vat_number}`);
                setResult(result.data);
              }}
            >
              {props => (
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

      {!isEmpty(result) ? (
        <div id="results">
          <div className="row justify-content-center">
            <div className="col-xs-12 col-sm-10 col-md-8 col-lg-6">
              <div className="card">
                <div className="card-body">
                  {map(result, (value, key) => (
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

      {/*<div id="diagonal" className="d-none d-sm-block"></div>*/}
    </div>
  );
};

export default Home;
