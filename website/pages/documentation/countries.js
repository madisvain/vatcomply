import Highlight from "../../components/highlight";

const exampleRequest = `
GET https://api.vatcomply.com/rates HTTP/1.1
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

const Countries = () => {
  return (
    <div id="countries" style={{ marginTop: 100, marginBottom: 100 }}>
      <h2 className="mb-4">Countries</h2>
      <p>The VAT validation endpoint allows you to check whether a VAT number is valid.</p>
      <p className="mb-4">
        If the VAT number is valid, it returns information about the company with the countries VAT rates.
      </p>
      <div className="card boxed">
        <div className="card-body p-0">
          <Highlight>{exampleRequest}</Highlight>
        </div>
      </div>
      <div className="card boxed mt-4">
        <div className="card-body p-0">
          <Highlight language="json">{exampleResponse}</Highlight>
        </div>
      </div>
    </div>
  );
};

export default Countries;
