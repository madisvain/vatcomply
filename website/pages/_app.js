import "../styles/base.scss";

import App from "next/app";

export default class VATComplyApp extends App {
  render() {
    const { Component, pageProps } = this.props;
    return (
      <>
        <Component {...pageProps} />
        <script src="https://analytics.ahrefs.com/analytics.js" data-key="HY2osB4vMi3oY1qFklkQ7A" async></script>
      </>
    );
  }
}
