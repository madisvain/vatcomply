import { Light as SyntaxHighlighter } from "react-syntax-highlighter";
import { github } from "react-syntax-highlighter/dist/cjs/styles/hljs";

const Highlighter = ({ code, language }) => {
  return (
    <SyntaxHighlighter
      language={language}
      style={github}
      customStyle={{
        background: "#ffffff",
        margin: 16,
      }}
    >
      {code}
    </SyntaxHighlighter>
  );
};

export default Highlighter;
