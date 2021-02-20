import Highlighter from "../../components/highlighter";

const exampleRequest = `
GET https://api.vatcomply.com/vat?vat_number=NL810462783B01 HTTP/1.1
`.trim();

const exampleResponse = `
{
  "valid": true,
  "vat_number": "810462783B01",
  "name": "SHELL CHEMICALS EUROPE B.V.",
  "address": "WEENA 00070 3012CM ROTTERDAM",
  "country_code": "NL"
}
`.trim();

const VAT = () => {
  return (
    <div id="vat">
      <h2 className="mb-4">VAT validation</h2>
      <p>The VAT validation endpoint allows you to check whether a VAT number is valid.</p>
      <p className="mb-4">
        If the VAT number is valid, it returns information about the company with the countries VAT rates.
      </p>
      <div className="card boxed">
        <div className="card-body p-0">
          <Highlighter code={exampleRequest} language="http" />
        </div>
      </div>
      <div className="card boxed mt-4">
        <div className="card-body p-0">
          <Highlighter code={exampleResponse} language="json" />
        </div>
      </div>
    </div>
  );
};

export default VAT;
