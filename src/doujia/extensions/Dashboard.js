let loaded = false;

function loadScript(src) {
    if (loaded) {
        return Promise.resolve();
    }

    return new Promise(resolve => {
        var script = document.createElement('script')
        script.type = 'text/javascript'
        script.src = src
        script.onload = () => {
            loaded = true;
            resolve()
        }
        document.body.appendChild(script)
    });
}

function formatCurrency(value, currency) {
    const amount = value.toFixed(2);
    const parts = amount.toString().split('.');
    parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ",");
    return parts.join('.') + ' ' + currency;
}

function expenseChart(elem, data) {
    const chart = echarts.init(elem)

    chart.setOption({
        title: {
            show: true,
            text: data.title
        },
        xAxis: {
            type: "time",
        },
        yAxis: [{}, {}],
        tooltip: {
            trigger: 'axis',
            formatter: (params) => {
                return params[0].data[0]
                    + '<br>Current Period Total: ' + formatCurrency(params[0].data[1], data.currency)
                    + '<br>Compare Period Total: ' + formatCurrency(params[1].data[1] + params[0].data[1], data.currency)
                    + '<br>Diff: ' + formatCurrency(params[1].data[1], data.currency)
            }
        },
        series: [
            {
                type: "line",
                step: 'start',
                data: data.expenses,
                yAxisIndex: 0,
                markLine: {
                    data: [{
                        xAxis: data.today,
                    }],
                    symbol: 'none',
                    label: {
                        show: false,
                    },
                    lineStyle: {
                        color: '#CCC'
                    },
                    animation: false,
                    silent: true
                }
            },
            {
                type: "bar",
                yAxisIndex: 1,
                data: data.expenses.map(([date, amount]) => {
                    const elapsedDiff = (new Date(date).getTime() - new Date(data.begin).getTime())
                    const elapsedDays = Math.ceil(elapsedDiff / (1000 * 60 * 60 * 24))
                    const totalDiff = (new Date(data.end).getTime() - new Date(data.begin).getTime())
                    const totalDays = Math.ceil(totalDiff / (1000 * 60 * 60 * 24)) + 1
                    const elapsedPercent = elapsedDays / totalDays
                    const elapsedAmount = data.compareTotal * elapsedPercent
                    return [date, elapsedAmount - amount];
                }),
                itemStyle: {
                    color: (params) => {
                        return params.value[1] > 0 ? '#3daf46' : '#af3d3d'
                    }
                },
            },
            {
                type: "line",
                yAxisIndex: 0,
                data: [[data.begin, 0], [data.end, data.compareTotal]],
                symbol: 'none',
                animation: false,
                silent: true,
            }
        ],
    })

    return chart
}

function getRatio(saving, income) {
    if (!income) {
        return 0
    }

    return saving / income;
}

function savingChart(elem, savingData) {
    const xAxisSeries = savingData.current_periods.map(p => {
        const d = new Date(p.end_date_exclusive)
        d.setDate(d.getDate() - 1)
        return d
    })

    const ratioSeries = savingData.current_periods.reduce((memo, curr) => {
        if (memo.length === 0) {
            return [{
                total_saving: curr.total_saving,
                total_income: curr.total_income,
                ratio: getRatio(curr.total_saving, curr.total_income)
            }]
        }

        const lastResult = memo[memo.length - 1]
        memo.push({
            total_saving: lastResult.total_saving + curr.total_saving,
            total_income: lastResult.total_income + curr.total_income,
            ratio: getRatio(lastResult.total_saving + curr.total_saving, lastResult.total_income + curr.total_income)
        })
        return memo
    }, []).map((x, idx) => [xAxisSeries[idx], x.ratio])

    const incomeSeries = savingData.current_periods.map((p, idx) => [xAxisSeries[idx], p.total_income])
    const savingSeries = savingData.current_periods.map((p, idx) => [xAxisSeries[idx], p.total_saving])

    const chart = echarts.init(elem)

    chart.setOption({
        title: {
            show: true,
            text: 'Monthly Savings'
        },
        xAxis: {
            type: 'category',
            axisLabel: {
                formatter: function (value) {
                    var date = new Date(value);
                    var month = date.getMonth() + 1;
                    return month + '月';
                }
            }
        },
        yAxis: [{
            type: 'value'
        }, {
            type: 'value',
            axisLabel: {
                formatter: function (value) {
                    return (value * 100) + '%';
                }
            }
        }],
        series: [{
            type: 'line',
            data: ratioSeries,
            yAxisIndex: 1
        }, {
            type: 'bar',
            data: incomeSeries,
        }, {
            type: 'bar',
            data: savingSeries,
        }],
        tooltip: {
            trigger: 'axis',
            formatter: (params) => {
                const year = params[0].data[0].getFullYear();
                const month = String(params[0].data[0].getMonth() + 1).padStart(2, '0');

                const formattedDate = `${year}-${month}`;

                return formattedDate
                    + '<br>Cumulative savings rate: ' + Math.round(params[0].data[1] * 10000) / 100 + '%'
                    + '<br>Income: ' + formatCurrency(params[1].data[1], 'CNY')
                    + '<br>Savings: ' + formatCurrency(params[2].data[1], 'CNY')
            }
        },
    })

    return chart
}

function netWorthChart(elem, data) {
    const chart = echarts.init(elem)

    chart.setOption({
        title: {
            show: true,
            text: data.title
        },
        xAxis: {
            type: "time",
        },
        yAxis: {},
        tooltip: {
            trigger: 'axis',
            formatter: (params) => {
                return params[0].data[0]
                    + '<br>Net Worth: ' + formatCurrency(params[0].data[1], data.currency)
                    + '<br>Investment: ' + formatCurrency(params[1].data[1], data.currency)
                    + '<br>Stock: ' + formatCurrency(params[2].data[1], data.currency)
            }
        },
        dataZoom: [
            {
                type: 'inside',
                start: 90,
                end: 100
            },
            {
                start: 90,
                end: 100
            }
        ],
        series: [
            {
                type: "line",
                data: data.total,
                showSymbol: false
            },
            {
                type: "line",
                stack: 'investment',
                data: data.investment,
                showSymbol: false
            }
            ,
            {
                stack: 'investment',
                type: "line",
                data: data.stock,
                showSymbol: false
            }
        ],
    })

    return chart
}

const charts = []
let chartGroupA
let chartGroupB

function renderNetWorthCharts(netWorthData) {
    chartGroupA = document.getElementById('chartGroupA')

    const chartElem = document.createElement('div')
    chartElem.classList.add('chart')
    chartGroupA.insertBefore(chartElem, chartGroupA.childNodes[0])

    const chart = netWorthChart(chartElem, netWorthData)
    charts.push(chart)

    beginWatchResize()
}

function renderSavingCharts(savingData) {
    const chartElem = document.createElement('div')
    chartElem.classList.add('chart')
    document.getElementById('chartGroupA').appendChild(chartElem)

    const chart = savingChart(chartElem, savingData)
    charts.push(chart)

    beginWatchResize()
}

function renderCharts(data) {
    chartGroupB = document.getElementById('chartGroupB')

    const today = data.today;
    const chartConfigs = data.charts;

    chartConfigs.forEach(data => {
        const chartElem = document.createElement('div')
        chartElem.classList.add('chart')
        chartGroupB.appendChild(chartElem)

        const chart = expenseChart(chartElem, {
            today: today,
            title: data.title,
            currency: data.currency,
            expenses: data.summary.expenses,
            compareTotal: data.summary.compare_total,
            begin: data.summary.begin,
            end: data.summary.end,
        })
        charts.push(chart)
    })

    beginWatchResize()
}

function onResize() {
    charts.forEach(chart => {
        chart.resize()
    })
}

function beginWatchResize() {
    window.removeEventListener('resize', onResize);
    window.addEventListener('resize', onResize);
}

const observer = new MutationObserver(function (mutations) {
    if (!document.body.contains(chartGroupA)) {
        charts.length = 0
        window.removeEventListener('resize', onResize);
        observer.disconnect()
    }
});

observer.observe(document.body, { childList: true, subtree: true });

export default {
    onExtensionPageLoad(ctx) {
        const script$ = loadScript('https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.js');
        const data$ = ctx.api.get('charts');
        const netWorthData$ = ctx.api.get('net_worth_chart')
        const saving$ = ctx.api.get('saving_summary')

        Promise.all([script$, data$]).then(([_, data]) => {
            renderCharts(data)
        })

        Promise.all([script$, netWorthData$]).then(([_, netWorthData]) => {
            renderNetWorthCharts(netWorthData)
        })

        Promise.all([script$, saving$]).then(([_, saving_summary]) => {
            renderSavingCharts(saving_summary)
        })
    }
}
