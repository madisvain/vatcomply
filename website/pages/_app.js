import "../styles/base.scss";

import App from "next/app";

export default class VATComplyApp extends App {
  render() {
    const { Component, pageProps } = this.props;
    return (
      <>
        <Component {...pageProps} />
        <script defer data-domain="vatcomply.com" src="https://plausible.io/js/script.js"></script>
      </>
    );
  }
}
