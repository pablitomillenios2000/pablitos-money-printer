function setTitleWithPairName() {
    // First, fetch the pair name
    fetch('./output/pairname.txt?' + Math.random())
        .then(response => response.text())
        .then(pairName => {
            const trimmedPairName = pairName.trim();
            
            // Only proceed if pairName is not empty
            if (trimmedPairName) {
                // Now fetch the equity value
                return fetch('./output/equity.txt?' + Math.random())
                    .then(response => response.text())
                    .then(equityValue => {
                        const trimmedEquity = equityValue.trim();
                        titleContents = `PRODUCTION - ${trimmedPairName} -- Equity. $${trimmedEquity}`;
                        document.title = `${trimmedPairName} -- $${trimmedEquity}`;

                        // After updating title, call plotData.
                        const logParam = getQueryParam('log');
                        const logarithmicMode = (logParam === '1');
                        
                        plotData(logarithmicMode);
                    });
            } else {
                // If no pair name, stop here
                throw new Error('Pair name is empty');
            }
        })
        .catch(error => {
            console.error('Error:', error);
        });
}

// A small helper to read the URL parameter
function getQueryParam(param) {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get(param);
}

function plotData(logarithmic = false) {
    // Data arrays
    const timestampsAsset = [];
    const valuesAsset = [];

    // Trades
    let rawTrades = [];
    const buyTimestamps = [];
    const buyValues = [];
    const buyReasons = [];
    const sellTimestamps = [];
    const sellValues = [];
    const sellReasons = [];
    let showTrades = true;

    // InstaSpeed
    const timestampsInstaSpeed = [];
    const valuesInstaSpeed = [];

    // InstaSpeed Abs (NEW)
    const timestampsInstaSpeedAbs = [];
    const valuesInstaSpeedAbs = [];

    // (NEW) Linear Regression
    const timestampsLinreg = [];
    const valuesLinreg = [];

    // (NEW) Poly Up/Down
    const timestampsPolyup = [];
    const valuesPolyup = [];
    const timestampsPolydown = [];
    const valuesPolydown = [];

    // Use PapaParse to parse CSV files
    function parseCSV(url, callback) {
        return new Promise((resolve, reject) => {
            Papa.parse(url, {
                download: true,
                delimiter: ',',
                dynamicTyping: true,
                skipEmptyLines: true,
                complete: function (results) {
                    callback(results.data);
                    resolve();
                },
                error: function (error) {
                    console.error('Error parsing:', url, error);
                    reject(error);
                }
            });
        });
    }

    // Parse asset data
    const parseAsset = parseCSV('./output/asset.txt?' + Math.random(), (data) => {
        data.forEach(row => {
            if (row.length < 2) return;
            const [timestamp, value] = row;
            if (typeof timestamp === 'number' && value !== undefined) {
                timestampsAsset.push(timestamp);
                valuesAsset.push(value);
            }
        });
    });

    // Parse trades
    const parseTrades = parseCSV('./output/trades.txt?' + Math.random(), (data) => {
        data.forEach(row => {
            if (row.length < 3) return;
            const [timestamp, action, reason] = row;
            if (typeof timestamp === 'number' && action && reason) {
                rawTrades.push({ timestamp, action, reason });
            }
        });
    });

    // Parse instaspeed_abs (NEW)
    const parseInstaSpeedAbs = parseCSV('./output/polyacc_abs.txt?' + Math.random(), (data) => {
        data.forEach(row => {
            if (row.length < 2) return;
            const [timestamp, value] = row;
            if (typeof timestamp === 'number' && value !== undefined) {
                timestampsInstaSpeedAbs.push(timestamp);
                valuesInstaSpeedAbs.push(value);
            }
        });
    });

    // Parse linreg (NEW)
    const parseLinreg = parseCSV('./output/linreg.txt?' + Math.random(), (data) => {
        data.forEach(row => {
            if (row.length < 2) return;
            const [timestamp, value] = row;
            if (typeof timestamp === 'number' && value !== undefined) {
                timestampsLinreg.push(timestamp);
                valuesLinreg.push(value);
            }
        });
    });

    // (NEW) Parse polyup
    const parsePolyup = parseCSV('./output/polyup.txt?' + Math.random(), (data) => {
        data.forEach(row => {
            if (row.length < 2) return;
            const [timestamp, value] = row;
            if (typeof timestamp === 'number' && value !== undefined) {
                timestampsPolyup.push(timestamp);
                valuesPolyup.push(value);
            }
        });
    });

    // (NEW) Parse polydown
    const parsePolydown = parseCSV('./output/polydown.txt?' + Math.random(), (data) => {
        data.forEach(row => {
            if (row.length < 2) return;
            const [timestamp, value] = row;
            if (typeof timestamp === 'number' && value !== undefined) {
                timestampsPolydown.push(timestamp);
                valuesPolydown.push(value);
            }
        });
    });

    // Load all CSVs
    Promise.all([
        parseAsset,
        parseTrades,
        parseInstaSpeedAbs,
        parseLinreg,
        parsePolyup,
        parsePolydown
    ])
    .then(() => {
        matchTradesToAsset();
        createChart();
    })
    .catch(err => console.error('Error loading data:', err));

    function matchTradesToAsset() {
        rawTrades.forEach(trade => {
            const { timestamp, action, reason } = trade;
            // Find matching timestamp in asset data
            const idx = timestampsAsset.indexOf(timestamp);
            if (idx !== -1) {
                const value = valuesAsset[idx];
                if (action === 'buy') {
                    buyTimestamps.push(timestamp);
                    buyValues.push(value);
                    buyReasons.push(reason);
                } else if (action === 'sell') {
                    sellTimestamps.push(timestamp);
                    sellValues.push(value);
                    sellReasons.push(reason);
                }
            } else {
                console.warn(`No exact match in asset for trade at timestamp ${timestamp}`);
            }
        });

        const totalTrades = buyTimestamps.length + sellTimestamps.length;
        if (totalTrades > 1000) {
            showTrades = false;
        }
    }

    function createChart() {
        const lineStyle = {
            shape: 'spline',  // smooth lines
            smoothing: 1.3,
            width: 2
        };

        const traces = [];

        // 1) Main Asset Price trace (left y-axis)
        if (timestampsAsset.length > 0) {
            traces.push({
                x: timestampsAsset.map(ts => new Date(ts * 1000)),
                y: valuesAsset,
                mode: 'lines',
                type: 'scatter',
                name: 'Asset Price',
                line: lineStyle,
                yaxis: 'y'
            });
        }

        // 2) Second trace for the percentage scale (right y-axis),
        //    made invisible but used to scale the right axis
        if (valuesAsset.length > 0) {
            const minAssetValue = Math.min(...valuesAsset);
            const percentValues = valuesAsset.map(val => 
                ((val - minAssetValue) / minAssetValue) * 100
            );

            traces.push({
                x: timestampsAsset.map(ts => new Date(ts * 1000)),
                y: percentValues,
                mode: 'lines',
                type: 'scatter',
                showlegend: false,
                hoverinfo: 'none',
                line: { color: 'rgba(0,0,0,0)', width: 0 },
                yaxis: 'y2'
            });
        }

        // 3) Trades
        const annotations = [];
        if (showTrades && (buyTimestamps.length > 0 || sellTimestamps.length > 0)) {
            // Buy
            traces.push({
                x: buyTimestamps.map(ts => new Date(ts * 1000)),
                y: buyValues,
                mode: 'markers',
                type: 'scatter',
                name: 'Buy Trades',
                marker: { color: 'green', size: 10 },
                yaxis: 'y'
            });
            buyTimestamps.forEach((ts, index) => {
                annotations.push({
                    x: new Date(ts * 1000),
                    y: buyValues[index],
                    xref: 'x',
                    yref: 'y',
                    text: buyReasons[index],
                    showarrow: false,
                    font: { size: 10, color: 'green' },
                    yshift: 10,
                });
            });

            // Sell
            traces.push({
                x: sellTimestamps.map(ts => new Date(ts * 1000)),
                y: sellValues,
                mode: 'markers',
                type: 'scatter',
                name: 'Sell Trades',
                marker: { color: 'red', size: 10 },
                yaxis: 'y'
            });
            sellTimestamps.forEach((ts, index) => {
                annotations.push({
                    x: new Date(ts * 1000),
                    y: sellValues[index],
                    xref: 'x',
                    yref: 'y',
                    text: sellReasons[index],
                    showarrow: false,
                    font: { size: 10, color: 'red' },
                    yshift: -10,
                });
            });
        }

        // 6) InstaSpeed Abs trace (left axis) - pink dots
        if (timestampsInstaSpeedAbs.length > 0) {
            traces.push({
                x: timestampsInstaSpeedAbs.map(ts => new Date(ts * 1000)),
                y: valuesInstaSpeedAbs,
                mode: 'markers', // points only, no lines
                type: 'scatter',
                name: 'InstaSpeed Abs',
                marker: {
                    color: 'pink',
                    size: 8
                },
                yaxis: 'y' // <-- now follows the main (left) axis
            });
        }

        // 7) Linear Regression trace (NEW)
        if (timestampsLinreg.length > 0) {
            traces.push({
                x: timestampsLinreg.map(ts => new Date(ts * 1000)),
                y: valuesLinreg,
                mode: 'lines',
                type: 'scatter',
                name: 'Linear Regression',
                line: {
                    shape: 'line', // no spline smoothing
                    width: 2,
                    color: 'gray'
                },
                yaxis: 'y'
            });
        }

        // (NEW) 8) Poly Up trace (green)
        if (timestampsPolyup.length > 0) {
            traces.push({
                x: timestampsPolyup.map(ts => new Date(ts * 1000)),
                y: valuesPolyup,
                mode: 'lines',
                type: 'scatter',
                name: 'Upwards Movements',
                line: {
                    shape: 'spline',
                    width: 2,
                    color: 'green'
                },
                yaxis: 'y'
            });
        }

        // (NEW) 9) Poly Down trace (red)
        if (timestampsPolydown.length > 0) {
            traces.push({
                x: timestampsPolydown.map(ts => new Date(ts * 1000)),
                y: valuesPolydown,
                mode: 'lines',
                type: 'scatter',
                name: 'Downwards Movements',
                line: {
                    shape: 'spline',
                    width: 2,
                    color: 'red'
                },
                yaxis: 'y'
            });
        }

        // Define Layout
        const layout = {
            title: titleContents,
            xaxis: { title: 'Time' },
            yaxis: {
                title: 'Asset Price',
                type: logarithmic ? 'log' : 'linear',
                showgrid: false,
                zeroline: false
            },
            yaxis2: {
                title: 'Change from Min (%)',
                overlaying: 'y',
                side: 'right',
                showgrid: true,
                zeroline: false
            },
            annotations: annotations
        };

        const config = {
            plotGlPixelRatio: 5
        };

        Plotly.newPlot('chart', traces, layout, config);
    }
}

// Call the function
setTitleWithPairName();
