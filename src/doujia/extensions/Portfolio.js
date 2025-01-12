import * as echarts from "https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.esm.min.js";
import {
  $value,
  $effect,
  $computed,
  createStore,
} from "https://esm.sh/rippling@0.0.9/core";
import { useSet } from "https://esm.sh/rippling@0.0.9/react";
import htm from "https://esm.sh/htm@3.1.1";
import React, { useLayoutEffect, useRef } from "https://esm.sh/react@18.3.1";
import { useLoadable, StoreProvider } from "https://esm.sh/rippling@0.0.9/react";
import { render } from "https://esm.sh/react-dom@18.3.1";
const html = htm.bind(React.createElement);

// ------------------------------------------------------------
// Values
// ------------------------------------------------------------

const favaApi = $value(null);

const navIndex = $computed((get) => {
  const api = get(favaApi);
  return api.get("nav_index" + window.location.search);
});

const cashFlows = $computed((get) => {
  const api = get(favaApi);
  return api.get("cash_flows" + window.location.search);
});

const investments = $computed((get) => {
  const api = get(favaApi);
  return api.get("investments" + window.location.search);
});

const pnl = $computed((get) => {
  const api = get(favaApi);
  return api.get("pnl" + window.location.search);
});

const calendarReturns = $computed((get) => {
  const api = get(favaApi);
  return api.get("calendar_returns" + window.location.search);
});

const cumulativeReturns = $computed((get) => {
  const api = get(favaApi);
  return api.get("cumulative_returns" + window.location.search);
});

const irrSummary = $computed((get) => {
  const api = get(favaApi);
  return api.get("irr_summary" + window.location.search);
});

const navIndexChartOptions = $computed(async (get) => {
  const data = await get(navIndex);

  const lastDate = data[data.length - 1][0];
  const [year, compareMonth, compareDay] = lastDate
    .split("-")
    .map((x) => parseInt(x, 10));
  const compareYear = year - 3;

  let index = 0;
  for (const [date, _] of data) {
    const [year, month, day] = date.split("-").map((x) => parseInt(x, 10));
    if (year > compareYear) {
      break;
    }

    if (year === compareYear && month > compareMonth) {
      break;
    }

    if (year === compareYear && month === compareMonth && day >= compareDay) {
      break;
    }

    index++;
  }
  const startRatio = index / data.length;

  return {
    xAxis: {
      type: "time",
    },
    yAxis: {
      type: "value",
      axisLabel: {
        formatter: function (params) {
          return params.toFixed(2);
        },
      },
      min: "dataMin",
      max: "dataMax",
    },
    tooltip: {
      trigger: "axis",
      formatter: function (params) {
        return params[0].data[0] + "<br>" + params[0].data[1].toFixed(2);
      },
    },
    series: [
      {
        type: "line",
        showSymbol: false,
        data: data,
      },
    ],
    grid: {
      x: 60,
      y: 20,
      x2: 20,
      y2: 60,
    },
    dataZoom: [
      {
        type: "inside",
        start: startRatio * 100,
        end: 100,
      },
      {
        start: startRatio * 100,
        end: 100,
      },
    ],
  }
})

const calendarReturnsChartOptions = $computed(async (get) => {
  const data = await get(calendarReturns);
  return {
    xAxis: {
      type: "category",
      axisLabel: {
        formatter: (value) => {
          return new Date(Date.parse(value) - 86400000).getFullYear();
        },
      },
    },
    yAxis: {
      type: "value",
      axisLabel: {
        formatter: function (params) {
          return (params * 100).toFixed(1) + "%";
        },
      },
    },
    tooltip: {
      trigger: "axis",
      formatter: function (params) {
        return (
          params[0].data[0] +
          "<br>" +
          (params[0].data[1] * 100).toFixed(1) +
          "%"
        );
      },
    },
    series: [
      {
        type: "bar",
        data: data[0],
        itemStyle: {
          color: (params) => {
            return params.value[1] > 0 ? "#3daf46" : "#af3d3d";
          },
        },
        label: {
          show: true,
          position: "top",
          formatter: (params) => {
            return (params.data[1] * 100).toFixed(1) + "%";
          },
        },
      },
    ],
    grid: {
      x: 60,
      y: 20,
      x2: 20,
      y2: 60,
    },
  }
})

// ------------------------------------------------------------
// Effects
// ------------------------------------------------------------

const renderNavIndex = $effect(async (get, set, elem) => {
  const options = await get(navIndexChartOptions);
  echarts.init(elem).setOption(options);
});

const renderCalendarReturns = $effect(async (get, set, elem) => {
  const options = await get(calendarReturnsChartOptions);
  echarts.init(elem).setOption(options);
});

// ------------------------------------------------------------
// Bootstrap
// ------------------------------------------------------------

export default {
  onExtensionPageLoad(ctx) {
    const store = createStore();
    store.set(favaApi, ctx.api);

    render(
      html`<${StoreProvider} value=${store}><${InvestmentGroup} /></${StoreProvider}>`,
      document.getElementById("investment-group")
    );
  },
};
// ------------------------------------------------------------
// Components
// ------------------------------------------------------------

function AmountTD({ number, currency }) {
  return html`
    <td style=${{ display: "flex", justifyContent: "space-between", gap: "10px" }}>
      <span>${currency}</span
      ><span
        >${number.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}
      </span>
    </td>
  `;
}

function CumulativeReturns() {
  const loadableData = useLoadable(cumulativeReturns);
  if (loadableData.state !== 'hasData') {
    return html`<div>Loading...</div>`;
  }
  const data = loadableData.data;

  return html`
    <h3>Internal Rate of Returns</h3>
    <table>
      <thead>
        <tr>
          ${data.header.map((x) => html`<th>${x}</th>`)}
        </tr>
      </thead>
      <tbody>
        ${data.rows.map((row) => html`
          <tr>
            <td>${row[0]}</td>
            ${row.slice(1).map((x) => html`<td style=${{ textAlign: "right" }}>${(x * 100).toFixed(2)}%</td>`)}
          </tr>
        `)}
      </tbody>
    </table>
  `;
}

function CashFlows() {
  const loadableData = useLoadable(cashFlows);
  if (loadableData.state !== 'hasData') {
    return html`<div>Loading...</div>`;
  }
  const data = loadableData.data;

  return html`
    <h3>Cash Flows</h3>
    <table>
      <thead>
        <tr>
          <th>Date</th>
          <th>Amount</th>
          <th>D</th>
          <th>Investment</th>
        </tr>
      </thead>
      <tbody>
        ${data.map(
    (x) => html`<tr>
            <td>${x.date}</td>
            <${AmountTD} number=${x.amount.number} currency=${x.amount.currency} />
            <td>${x.is_dividend ? "X" : ""}</td>
            <td>${x.account}</td>
          </tr>`
  )}
      </tbody>
    </table>
  `;
}

function Investments() {
  const loadableData = useLoadable(investments);
  if (loadableData.state !== 'hasData') {
    return html`<div>Loading...</div>`;
  }
  const data = loadableData.data;

  return html`
    <div style=${{ display: "flex", justifyContent: "space-between", gap: "20px" }}>
      <div style=${{ flex: "1" }}>
        <h3>Profitable Investments</h3>
        <table>
          <thead>
            <tr>
              <th>Investment</th>
              <th>PnL</th>
            </tr>
          </thead>
          <tbody>
            ${data.profitable.map(
    (row) => html`
                <tr>
                  <td>${row.name}</td>
                  <${AmountTD} number=${row.pnl} currency=${row.currency} />
                </tr>
              `
  )}
          </tbody>
        </table>
      </div>
      <div style=${{ flex: "1" }}>
        <h3>Unprofitable Investments</h3>
        <table>
          <thead>
            <tr>
              <th>Investment</th>
              <th>PnL</th>
            </tr>
          </thead>
          <tbody>
            ${data.unprofitable.map(
    (row) => html`
                <tr>
                  <td>${row.name}</td>
                  <${AmountTD} number=${row.pnl} currency=${row.currency} />
                </tr>
              `
  )}
          </tbody>
        </table>
      </div>
    </div>
  `;
}

function InvestmentSummary() {
  const pnl_ = useLoadable(pnl);
  const irrSummary_ = useLoadable(irrSummary);
  const navIndex_ = useLoadable(navIndex);
  if (pnl_.state !== 'hasData' || irrSummary_.state !== 'hasData' || navIndex_.state !== 'hasData') {
    return html`<div>Loading...</div>`;
  }
  const pnlData = pnl_.data;
  const irrData = irrSummary_.data;
  const latestNavIndex = navIndex_.data[navIndex_.data.length - 1][1];
  const total_pnl = pnlData.realized_pnl_ex_fee + pnlData.unrealized_pnl + pnlData.dividend_ex_tax;

  return html`
    <div style=${{
      display: "grid",
      gridTemplateColumns: "1fr 1fr 1fr 1fr 1fr 1fr",
      gridTemplateRows: "auto",
      gap: "10px"
    }}>
      <${Card} title="Currency" value=${pnlData.currency} isPositive={true} />
      <${Card} title="Total PnL" value=${total_pnl.toLocaleString(undefined, { maximumFractionDigits: 0 })} isPositive=${total_pnl > 0} numberTitle="Total PnL in ${pnlData.currency}, including ${pnlData.dividend_ex_tax.toLocaleString(undefined, { maximumFractionDigits: 0 })} in dividends" />
      <${Card} title="Nav Index" value=${latestNavIndex.toFixed(2)} isPositive=${latestNavIndex > 0} numberTitle="Latest NAV Index" />
      <${Card} title="Yearly Nav" value=${(Math.pow(latestNavIndex, 1 / irrData.years) * 100 - 100).toFixed(2) + '%'} isPositive=${latestNavIndex > 0} numberTitle="Latest NAV Index" />
      <${Card} title="IRR" value=${(irrData.total_returns * 100).toFixed(2) + '%'} isPositive=${irrData.total_returns > 0} numberTitle="Total returns over ${irrData.years} years" />
      <${Card} title="Dividends" value=${(irrData.div_returns * 100).toFixed(2) + '%'} isPositive=${irrData.div_returns > 0} numberTitle="Total dividends over ${irrData.years} years" />
    </div>
  `;
}

function Card({ title, value, isPositive, numberTitle }) {
  const cardStyle = {
    borderRadius: "0.25rem",
    padding: "20px",
    ...(isPositive ? {
      background: "#c6dee0",
      color: "#013e41"
    } : {
      background: "rgb(228, 206, 206)",
      color: "#a77979"
    })
  };

  const numberStyle = {
    fontSize: "53px"
  };

  return html`
    <div style=${cardStyle}>
      <div style=${numberStyle} title=${numberTitle}>${value}</div>
      <div>${title}</div>
    </div>
  `;
}

function NavIndexChart() {
  const elemRef = useRef(null);
  const navIndex = useSet(renderNavIndex);

  useLayoutEffect(() => {
    navIndex(elemRef.current);
  }, []);

  return html`
    <div ref=${elemRef} style=${{ height: "400px" }}></div>
  `;
}

function CalendarReturnsChart() {
  const elemRef = useRef(null);
  const calendarReturns = useSet(renderCalendarReturns);

  useLayoutEffect(() => {
    calendarReturns(elemRef.current);
  }, []);

  return html`
    <div ref=${elemRef} style=${{ height: "400px" }}></div>
  `;
}

function InvestmentGroup() {
  const chartStyles = {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gridTemplateRows: "auto",
    gap: "10px",
  };

  return html`
    <${InvestmentSummary} />

    <br />

    <div style=${chartStyles}>
      <${NavIndexChart} />
      <${CalendarReturnsChart} />
    </div>

    <${CumulativeReturns} />
    <${Investments} />
    <${CashFlows} />
  `
}
