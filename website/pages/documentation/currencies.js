import Highlight from "../../components/highlight";

const exampleRequest = `
GET https://api.vatcomply.com/currencies HTTP/1.1
`.trim();

const exampleResponse = `
{
  "EUR": {
    "name": "Euro",
    "symbol": "€"
  },
  "USD": {
    "name": "US Dollar",
    "symbol": "$"
  },
  "JPY": {
    "name": "Japanese Yen",
    "symbol": "¥"
  },
  "BGN": {
    "name": "Bulgarian Lev",
    "symbol": "BGN"
  },
  "CZK": {
    "name": "Czech Koruna",
    "symbol": "CZK"
  },
  "DKK": {
    "name": "Danish Krone",
    "symbol": "DKK"
  },
  "GBP": {
    "name": "British Pound",
    "symbol": "£"
  },
  "HUF": {
    "name": "Hungarian Forint",
    "symbol": "HUF"
  },
  "PLN": {
    "name": "Polish Zloty",
    "symbol": "PLN"
  },
  "RON": {
    "name": "Romanian Leu",
    "symbol": "RON"
  },
  "SEK": {
    "name": "Swedish Krona",
    "symbol": "SEK"
  },
  "CHF": {
    "name": "Swiss Franc",
    "symbol": "CHF"
  },
  "ISK": {
    "name": "Icelandic Króna",
    "symbol": "ISK"
  },
  "NOK": {
    "name": "Norwegian Krone",
    "symbol": "NOK"
  },
  "HRK": {
    "name": "Croatian Kuna",
    "symbol": "HRK"
  },
  "RUB": {
    "name": "Russian Ruble",
    "symbol": "RUB"
  },
  "TRY": {
    "name": "Turkish Lira",
    "symbol": "TRY"
  },
  "AUD": {
    "name": "Australian Dollar",
    "symbol": "A$"
  },
  "BRL": {
    "name": "Brazilian Real",
    "symbol": "R$"
  },
  "CAD": {
    "name": "Canadian Dollar",
    "symbol": "CA$"
  },
  "CNY": {
    "name": "Chinese Yuan",
    "symbol": "CN¥"
  },
  "HKD": {
    "name": "Hong Kong Dollar",
    "symbol": "HK$"
  },
  "IDR": {
    "name": "Indonesian Rupiah",
    "symbol": "IDR"
  },
  "ILS": {
    "name": "Israeli New Shekel",
    "symbol": "₪"
  },
  "INR": {
    "name": "Indian Rupee",
    "symbol": "₹"
  },
  "KRW": {
    "name": "South Korean Won",
    "symbol": "₩"
  },
  "MXN": {
    "name": "Mexican Peso",
    "symbol": "MX$"
  },
  "MYR": {
    "name": "Malaysian Ringgit",
    "symbol": "MYR"
  },
  "NZD": {
    "name": "New Zealand Dollar",
    "symbol": "NZ$"
  },
  "PHP": {
    "name": "Philippine Piso",
    "symbol": "PHP"
  },
  "SGD": {
    "name": "Singapore Dollar",
    "symbol": "SGD"
  },
  "THB": {
    "name": "Thai Baht",
    "symbol": "THB"
  },
  "ZAR": {
    "name": "South African Rand",
    "symbol": "ZAR"
  }
}
`.trim();

const Currencies = () => {
  return (
    <div id="currencies" style={{ marginTop: 100 }}>
      <h2 className="mb-4">Currencies</h2>
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

export default Currencies;
