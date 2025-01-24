# JSON Config file

without this file the system won't run

it specifies the subfolder of which exchange we are using

and many other vital parameters

Here is an example

{
    "key": "",
    "secret": "",
    "pair":"SUIUSDC",
    "exchange": "binance", // IMPORTANT, is a subfolder
    "margin_annual_interest_percentage": 6.12,
    "trade_fee_percentage": 0.1,
    "investment": 4600,
    "margin": 4, //4x margin
    "sl_percentage": 1.5,
    "input_file": "../assets/suiusdc-realtime.csv",
    "start_date":"1900-01-01",   //"1900-01-01", //"2021-01-01",
    "end_date":"2040-01-01",    //"2040-01-01", //"2021-08-20",
    "ema_days": 1800,
    "ema_days_micro": 200,
    "min_positive_slope": -99
}
