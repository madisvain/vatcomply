import "../styles/base.scss";

import App from "next/app";
import Router from "next/router";
import { initGA, logPageView } from "../components/analytics";

export default class VATComplyApp extends App {
  componentDidMount() {
    initGA();
    logPageView();
    Router.events.on("routeChangeComplete", logPageView);
  }

  render() {
    const { Component, pageProps } = this.props;
    return <Component {...pageProps} />;
  }
}
