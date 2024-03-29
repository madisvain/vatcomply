import Highlighter from "../../components/highlighter";

const exampleRequest = `
GET https://api.vatcomply.com/geolocate HTTP/1.1
`.trim();

const exampleResponse = `
{
    "country_code": "DE",
    "ip": "85.214.132.117"
}
`.trim();

const Geolocation = () => {
  return (
    <div id="geolocation" style={{ marginTop: 100, marginBottom: 100 }}>
      <h2 className="mb-4">Geolocation</h2>
      <p>
        Returns your visitors country code by geolocating your visitor via{" "}
        <a href="https://support.cloudflare.com/hc/en-us/articles/200168236-Configuring-Cloudflare-IP-Geolocation">
          CloudFlare IP geolocation
        </a>
        .
      </p>
      <p className="mb-4">
        It's meant to be used in the frontend of your application by having the visitors browser make the request.
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

export default Geolocation;
