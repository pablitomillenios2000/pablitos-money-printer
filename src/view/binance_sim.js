// A small helper to read the URL parameter
function getQueryParam(param) {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get(param);
}

function setTitleWithPairName() {
    // First, fetch the pair name
    fetch('./output/pairname.txt?' + Math.random())
        .then(response => response.text())
        .then(pairName => {
            trimmedPairName = pairName.trim();
            
            // Only proceed if pairName is not empty
            if (trimmedPairName) {
                // Now fetch the equity value
                return fetch('./output/equity.txt?' + Math.random());
            } else {
                // If no pair name, stop here
                throw new Error('Pair name is empty');
            }
        })
        .then(response => response.text())
        .then(equityValue => {
            const trimmedEquity = equityValue.trim();
            titleContents = `PRODUCTION - ${trimmedPairName} -- Equity. $${trimmedEquity}`;
            document.title = `${trimmedPairName} -- $${trimmedEquity}`;

            // After updating title, call plotData.
            const logParam = getQueryParam('log');
            const logarithmicMode = (logParam === '1');
            
            plotData(logarithmicMode);
        })
        .catch(error => {
            console.error('Error:', error);
        });
}


function plotData(logarithmic = false) {
    // Variables to skip loading certain files
    const loadEMA = true;       // Set to false to skip loading expma.txt
    const loadEMAMicro = false; // Set to false to skip loading expma_micro.txt
    const loadAsset = true;     // Set to false to skip loading asset.txt

    // Set the slope display interval
    const slopeDisplayInterval = 0; // 0 = skip slopes

    // Toggle display of margin data
    const showMargin = false; // Set to true to display margin data

    // Arrays for data
    const timestampsAsset = [];
    const valuesAsset = [];
    const timestampsPortfolio = [];
    const valuesPortfolio = [];
    const timestampsUntouchedPortfolio = [];
    const valuesUntouchedPortfolio = [];
    const timestampsEMA = [];
    const valuesEMA = [];
    const timestampsEMAMicro = [];
    const valuesEMAMicro = [];
    const timestampsSlopes = [];
    const slopes = [];
    const timestampsMargin = [];
    const valuesMargin = [];

    // Arrays for trades
    let rawTrades = [];  // Will store { timestamp, action, reason }

    // Final arrays for plotting trades
    const buyTimestamps = [];
    const buyValues = [];
    const buyReasons = [];
    const sellTimestamps = [];
    const sellValues = [];
    const sellReasons = [];
    let showTrades = true;  // Will be set to false if too many trades

    // Thresholds
    const thresholds = [
        { value: 100000, label: '100K', color: '#87CEFA' },
        { value: 1000000, label: '1M', color: '#6495ED' },
        { value: 100000000, label: '100M', color: '#4169E1' },
        { value: 4000000000, label: '4B', color: '#00008B' }
    ];
    let thresholdTraces = [];
    let shapes = [];
    let annotations = [];

    // ---------------------------
    //  Promisified parse helpers
    // ---------------------------
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

    // Decide which portfolio file to load based on &bnb=1
    const bnbParam = getQueryParam('bnb');
    const portfolioFile = (bnbParam === '1') ? 'portfolio_bnb.txt' : 'portfolio.txt';

    // Parse each file concurrently
    const parsePromises = [];

    // TRADES
    parsePromises.push(
        parseCSV('./output/trades.txt?' + Math.random(), (data) => {
            data.forEach(row => {
                if (row.length < 3) return;
                const [timestamp, action, reason] = row;
                if (typeof timestamp === 'number' && action && reason) {
                    rawTrades.push({ timestamp, action, reason });
                }
            });
        })
    );

    // PORTFOLIO (use portfolioFile determined above)
    parsePromises.push(
        parseCSV(`./output/${portfolioFile}?` + Math.random(), (data) => {
            data.forEach(row => {
                if (row.length < 2) return;
                const [timestamp, value] = row;
                if (typeof timestamp === 'number' && value !== undefined) {
                    timestampsPortfolio.push(timestamp);
                    valuesPortfolio.push(value);
                }
            });
        })
    );

    // UNTOUCHED PORTFOLIO
    parsePromises.push(
        parseCSV('./output/untouched_portfolio.txt?' + Math.random(), (data) => {
            data.forEach(row => {
                if (row.length < 2) return;
                const [timestamp, value] = row;
                if (typeof timestamp === 'number' && value !== undefined) {
                    timestampsUntouchedPortfolio.push(timestamp);
                    valuesUntouchedPortfolio.push(value);
                }
            });
        })
    );

    // EMA (conditional)
    if (loadEMA) {
        parsePromises.push(
            parseCSV('./output/expma.txt?' + Math.random(), (data) => {
                data.forEach(row => {
                    if (row.length < 2) return;
                    const [timestamp, value] = row;
                    if (typeof timestamp === 'number' && value !== undefined) {
                        timestampsEMA.push(timestamp);
                        valuesEMA.push(value);
                    }
                });
            })
        );
    }

    // EMA MICRO (conditional)
    if (loadEMAMicro) {
        parsePromises.push(
            parseCSV('./output/expma_micro.txt?' + Math.random(), (data) => {
                data.forEach(row => {
                    if (row.length < 2) return;
                    const [timestamp, value] = row;
                    if (typeof timestamp === 'number' && value !== undefined) {
                        timestampsEMAMicro.push(timestamp);
                        valuesEMAMicro.push(value);
                    }
                });
            })
        );
    }

    // SLOPES (conditional)
    if (slopeDisplayInterval > 0) {
        parsePromises.push(
            parseCSV('./output/ema_slopes.txt?' + Math.random(), (data) => {
                data.forEach(row => {
                    if (row.length < 2) return;
                    const [timestamp, slopeValue] = row;
                    if (typeof timestamp === 'number' && slopeValue !== undefined) {
                        timestampsSlopes.push(timestamp);
                        slopes.push(slopeValue);
                    }
                });
            })
        );
    }

    // ASSET (conditional)
    if (loadAsset) {
        parsePromises.push(
            parseCSV('./output/asset.txt?' + Math.random(), (data) => {
                data.forEach(row => {
                    if (row.length < 2) return;
                    const [timestamp, value] = row;
                    if (typeof timestamp === 'number' && value !== undefined) {
                        timestampsAsset.push(timestamp);
                        valuesAsset.push(value);
                    }
                });
            })
        );
    }

    // MARGIN (conditional)
    if (showMargin) {
        parsePromises.push(
            parseCSV('./output/margin.txt?' + Math.random(), (data) => {
                data.forEach(row => {
                    if (row.length < 2) return;
                    const [timestamp, value] = row;
                    if (typeof timestamp === 'number' && value !== undefined) {
                        timestampsMargin.push(timestamp);
                        valuesMargin.push(value);
                    }
                });
            })
        );
    }

    // ---------------------------
    //  Fetch all files concurrently
    // ---------------------------
    Promise.all(parsePromises)
        .then(() => {
            applyThresholdChecks();
            matchTradesToPortfolio();
            createChart();
        })
        .catch(err => console.error('Error loading data:', err));

    function applyThresholdChecks() {
        thresholds.forEach(threshold => {
            let thresholdTimestamp = null;
            let thresholdValue = threshold.value;

            for (let i = 0; i < valuesPortfolio.length; i++) {
                if (valuesPortfolio[i] >= thresholdValue) {
                    thresholdTimestamp = timestampsPortfolio[i];
                    break;
                }
            }

            if (thresholdTimestamp !== null) {
                thresholdTraces.push({
                    x: [new Date(thresholdTimestamp * 1000)],
                    y: [thresholdValue],
                    mode: 'markers',
                    type: 'scattergl',
                    name: threshold.label,
                    yaxis: 'y2',
                    marker: {
                        symbol: 'x',
                        size: 20,
                        color: threshold.color
                    },
                    hoverinfo: 'text',
                    hovertext: `Portfolio reached ${threshold.label} (${thresholdValue.toLocaleString()})`
                });
            }
        });
    }

    function matchTradesToPortfolio() {
        rawTrades.forEach(trade => {
            const { timestamp, action, reason } = trade;
            const idx = timestampsPortfolio.indexOf(timestamp);
            if (idx !== -1) {
                const value = valuesPortfolio[idx];
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
                console.warn(`No exact match in portfolio for trade at timestamp ${timestamp}`);
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

        // Asset trace
        if (loadAsset && timestampsAsset.length > 0) {
            traces.push({
                x: timestampsAsset.map(ts => new Date(ts * 1000)),
                y: valuesAsset,
                mode: 'lines',
                type: 'scatter',
                name: 'Asset Price',
                yaxis: 'y1',
                line: lineStyle,
            });
        }

        // Portfolio trace
        traces.push({
            x: timestampsPortfolio.map(ts => new Date(ts * 1000)),
            y: valuesPortfolio,
            mode: 'lines',
            type: 'scatter',
            name: 'Portfolio Value',
            yaxis: 'y2',
            line: Object.assign({ color: 'orange' }, lineStyle),
        });

        // Untouched portfolio
        traces.push({
            x: timestampsUntouchedPortfolio.map(ts => new Date(ts * 1000)),
            y: valuesUntouchedPortfolio,
            mode: 'lines',
            type: 'scattergl',
            name: 'Untouched Portfolio',
            yaxis: 'y2',
            line: Object.assign({ color: 'darkblue' }, lineStyle),
        });

        // EMA trace
        if (loadEMA && timestampsEMA.length > 0) {
            traces.push({
                x: timestampsEMA.map(ts => new Date(ts * 1000)),
                y: valuesEMA,
                mode: 'lines',
                type: 'scattergl',
                name: 'EMA',
                yaxis: 'y1',
                line: Object.assign({ color: 'black' }, lineStyle),
            });
        }

        // EMA Micro
        if (loadEMAMicro && timestampsEMAMicro.length > 0) {
            traces.push({
                x: timestampsEMAMicro.map(ts => new Date(ts * 1000)),
                y: valuesEMAMicro,
                mode: 'lines',
                type: 'scattergl',
                name: 'EMA Micro',
                yaxis: 'y1',
                line: Object.assign({ color: 'purple' }, lineStyle),
            });
        }

        // Margin trace
        if (showMargin && timestampsMargin.length > 0) {
            traces.push({
                x: timestampsMargin.map(ts => new Date(ts * 1000)),
                y: valuesMargin,
                mode: 'lines',
                type: 'scattergl',
                name: 'Margin',
                yaxis: 'y2',
                line: Object.assign({ color: 'red' }, lineStyle),
            });
        }

        // Trades
        if (showTrades && (buyTimestamps.length > 0 || sellTimestamps.length > 0)) {
            const buyTrace = {
                x: buyTimestamps.map(ts => new Date(ts * 1000)),
                y: buyValues,
                mode: 'markers',
                type: 'scattergl',
                name: 'Buy Trades',
                marker: { color: 'green', size: 10 },
                yaxis: 'y2',
            };
            const sellTrace = {
                x: sellTimestamps.map(ts => new Date(ts * 1000)),
                y: sellValues,
                mode: 'markers',
                type: 'scattergl',
                name: 'Sell Trades',
                marker: { color: 'red', size: 10 },
                yaxis: 'y2',
            };
            traces.push(buyTrace, sellTrace);

            buyTimestamps.forEach((ts, index) => {
                annotations.push({
                    x: new Date(ts * 1000),
                    y: buyValues[index],
                    xref: 'x',
                    yref: 'y2',
                    text: buyReasons[index],
                    showarrow: false,
                    font: { size: 10, color: 'green' },
                    yshift: 10,
                });
            });

            sellTimestamps.forEach((ts, index) => {
                annotations.push({
                    x: new Date(ts * 1000),
                    y: sellValues[index],
                    xref: 'x',
                    yref: 'y2',
                    text: sellReasons[index],
                    showarrow: false,
                    font: { size: 10, color: 'red' },
                    yshift: -10,
                });
            });
        }

        // Threshold traces last
        if (thresholdTraces.length > 0) {
            traces.push(...thresholdTraces);
        }

        const layout = {
            title: titleContents,
            xaxis: { title: 'Time' },
            yaxis: {
                title: 'Asset Price',
                side: 'left',
                showgrid: true,
                type: 'linear'
            },
            yaxis2: {
                title: 'Portfolio Value',
                side: 'right',
                overlaying: 'y',
                showgrid: false,
                type: logarithmic ? 'log' : 'linear',
            },
            legend: {
                x: 0,
                y: 1,
                xanchor: 'left',
                yanchor: 'top',
            },
            annotations: annotations,
            shapes: shapes,
        };

        const config = {
            plotGlPixelRatio: 5
        };

        Plotly.newPlot('chart', traces, layout, config);
    }
}

// Call the function
setTitleWithPairName();
