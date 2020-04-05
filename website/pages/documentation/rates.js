import Highlight from "../../components/highlight";

const exampleRequestLatest = `
GET https://api.vatcomply.com/rates HTTP/1.1
`.trim();

const exampleResponseLates = `
{
  "date": "2020-04-03",
  "base": "EUR",
  "rates": {
    "EUR": 1,
    "USD": 1.0785,
    "JPY": 117.1,
    "BGN": 1.9558,
    "CZK": 27.539,
    "DKK": 7.4689,
    "GBP": 0.8785,
    "HUF": 365.15,
    "PLN": 4.5765,
    "RON": 4.8307,
    "SEK": 10.952,
    "CHF": 1.0547,
    "ISK": 155.7,
    "NOK": 11.2628,
    "HRK": 7.63,
    "RUB": 82.8075,
    "TRY": 7.2296,
    "AUD": 1.8004,
    "BRL": 5.6893,
    "CAD": 1.5299,
    "CNY": 7.6476,
    "HKD": 8.3625,
    "IDR": 17918.68,
    "ILS": 3.9267,
    "INR": 82.216,
    "KRW": 1332.82,
    "MXN": 26.547,
    "MYR": 4.7006,
    "NZD": 1.8423,
    "PHP": 54.805,
    "SGD": 1.5489,
    "THB": 35.601,
    "ZAR": 20.2642
  }
}
`.trim();

const exampleRequestBase = `
GET https://api.vatcomply.com/rates?base=USD HTTP/1.1
`.trim();

const exampleResponseBase = `
{
  "date": "2020-04-03",
  "base": "USD",
  "rates": {
    "EUR": 0.9272137227630969,
    "USD": 1,
    "JPY": 108.57672693555864,
    "BGN": 1.813444598980065,
    "CZK": 25.534538711172928,
    "DKK": 6.925266573945294,
    "GBP": 0.8145572554473806,
    "HUF": 338.5720908669448,
    "PLN": 4.243393602225313,
    "RON": 4.479091330551692,
    "SEK": 10.154844691701436,
    "CHF": 0.9779323133982383,
    "ISK": 144.36717663421416,
    "NOK": 10.443022716736207,
    "HRK": 7.074640704682429,
    "RUB": 76.78025034770515,
    "TRY": 6.703384330088085,
    "AUD": 1.6693555864626797,
    "BRL": 5.275197032916087,
    "CAD": 1.4185442744552619,
    "CNY": 7.09095966620306,
    "HKD": 7.753824756606399,
    "IDR": 16614.44598980065,
    "ILS": 3.6408901251738524,
    "INR": 76.23180343069076,
    "KRW": 1235.8089939731108,
    "MXN": 24.614742698191932,
    "MYR": 4.358460825220213,
    "NZD": 1.7082058414464534,
    "PHP": 50.815948076031525,
    "SGD": 1.4361613351877607,
    "THB": 33.009735744089014,
    "ZAR": 18.789244320815946
  }
}
`.trim();

const exampleRequestDate = `
GET https://api.vatcomply.com/rates?date=2000-04-05 HTTP/1.1
`.trim();

const exampleResponseDate = `
{
  "date": "2000-04-05",
  "base": "EUR",
  "rates": {
    "EUR": 1,
    "USD": 0.9673,
    "JPY": 101.71,
    "CYP": 0.57521,
    "CZK": 36.283,
    "DKK": 7.4483,
    "EEK": 15.6466,
    "GBP": 0.6088,
    "HUF": 258.91,
    "LTL": 3.8665,
    "LVL": 0.5714,
    "MTL": 0.4091,
    "PLN": 4.0707,
    "ROL": 18887,
    "SEK": 8.329,
    "SIT": 203.3895,
    "SKK": 41.665,
    "CHF": 1.5732,
    "ISK": 70.75,
    "NOK": 8.157,
    "TRL": 567142,
    "AUD": 1.5954,
    "CAD": 1.4078,
    "HKD": 7.5251,
    "KRW": 1077.54,
    "NZD": 1.9321,
    "SGD": 1.6586,
    "ZAR": 6.3808
  }
}
`.trim();

const Currencies = () => {
  return (
    <div id="rates" style={{ marginTop: 100 }}>
      <h2 className="mb-4">Rates</h2>
      <p>Currency rates tracks foreign exchange references rates published by the European Central Bank.</p>
      <p className="mb-4">The data refreshes around 16:00 CET every working day.</p>
      <h3 id="rates-latest">Latest rates</h3>
      <div className="card boxed">
        <div className="card-body p-0">
          <Highlight>{exampleRequestLatest}</Highlight>
        </div>
      </div>
      <div className="card boxed mt-4">
        <div className="card-body p-0">
          <Highlight language="json">{exampleResponseLates}</Highlight>
        </div>
      </div>
      <br />
      <br />
      <h3 id="rates-base">Base rate</h3>
      <p>Rates quote against the EUR by default. You can quote against other currencies using the base parameter.</p>
      <div className="card boxed">
        <div className="card-body p-0">
          <Highlight>{exampleRequestBase}</Highlight>
        </div>
      </div>
      <div className="card boxed mt-4">
        <div className="card-body p-0">
          <Highlight language="json">{exampleResponseBase}</Highlight>
        </div>
      </div>
      <h3 id="rates-date">Date</h3>
      <p>A date parameter returns historical rates data for any date since 04.01.1999.</p>
      <div className="card boxed">
        <div className="card-body p-0">
          <Highlight>{exampleRequestDate}</Highlight>
        </div>
      </div>
      <div className="card boxed mt-4">
        <div className="card-body p-0">
          <Highlight language="json">{exampleResponseDate}</Highlight>
        </div>
      </div>
    </div>
  );
};

export default Currencies;
