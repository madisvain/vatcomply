import React, { Component } from "react";
import PropTypes from "prop-types";

import hljs from "highlight.js/lib/highlight";

const registeredLanguages = {}; // keep a record of registered languages

export class CodeHighlight extends Component {
  constructor(props) {
    super(props);
    // do not show anything until language is loaded
    this.state = { loaded: false };
    // create a ref to highlight only the rendered node and not fetch all the DOM
    this.codeNode = React.createRef();
  }

  componentDidMount() {
    const { language } = this.props;
    if (language && !registeredLanguages[language]) {
      try {
        const newLanguage = require(`highlight.js/lib/languages/${language}`);
        hljs.registerLanguage(language, newLanguage);
        registeredLanguages[language] = true;
        this.setState(
          () => {
            return { loaded: true };
          },
          () => {
            this.highlight();
          }
        );
      } catch (e) {
        console.error(e);
        throw Error(`Cannot register and higlight language ${language}`);
        // We can alternatively set loaded to true and show an error message in the
        // code block instead of children, or just show the children without highlight.
        // This would be an improvement or an optional behavior given a special prop.
      }
    } else {
      this.setState({ loaded: true });
    }
  }

  componentDidUpdate() {
    this.highlight();
  }

  highlight = () => {
    this.codeNode && this.codeNode.current && hljs.highlightBlock(this.codeNode.current);
  };

  render() {
    const { language, children } = this.props;
    const { loaded } = this.state;
    if (!loaded) return ""; // or show a loader

    return (
      <pre className="mb-0 p-4">
        <code ref={this.codeNode} className={language}>
          {children}
        </code>
      </pre>
    );
  }
}

CodeHighlight.propTypes = {
  children: PropTypes.node.isRequired,
  language: PropTypes.string,
};
// optionally set the language you think will use most as a default value
// if you don't set this, I would encourage to make language prop required,
// or at least improve the "else" statement in "componentDidMount"
CodeHighlight.defaultProps = {
  language: "javascript",
};

export default CodeHighlight;
