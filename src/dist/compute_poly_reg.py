import os
import json5
import pandas as pd
import numpy as np

# ---------------------
# File paths
# ---------------------
CONFIG_FILE = "apikey-crypto.json"
ASSET_FILE = "../view/output/asset.txt"
POLYREG_FILE = "../view/output/polyreg.txt"

# Create output directory if needed
os.makedirs(os.path.dirname(POLYREG_FILE), exist_ok=True)

# ---------------------
# Load configuration
# ---------------------
try:
    with open(CONFIG_FILE, 'r') as file:
        config = json5.load(file)
except FileNotFoundError:
    print(f"Configuration file {CONFIG_FILE} not found. Using defaults.")
    config = {}

# ---------------------
# Read asset data
# ---------------------
try:
    asset_data = pd.read_csv(ASSET_FILE, header=None, names=["Timestamp", "Price"])
    asset_data["Timestamp"] = pd.to_numeric(asset_data["Timestamp"])  # Ensure numeric
    asset_data = asset_data.sort_values(by="Timestamp")              # Sort by time
except FileNotFoundError:
    print(f"Asset file {ASSET_FILE} not found.")
    exit(1)

# ----------------------------------------------------------------------
# Configurable parameters (defaults can be changed or extended)
# ----------------------------------------------------------------------
use_filt = config.get("use_filt", True)   # Smooth data before curve fitting
filt_per = config.get("filt_per", 10)     # Period for Super Smoother filter
per      = config.get("per", 10)          # Regression sample length
order    = config.get("order", 2)         # Polynomial order
calc_offs= config.get("calc_offs", 0)     # Regression offset
ndev     = config.get("ndev", 2.0)        # Channel width coefficient
equ_from = config.get("equ_from", 0)      # "Forecast from X bars ago"

# ----------------------------------------------------------------------
# 1) Two-Pole Super Smoother
# ----------------------------------------------------------------------
def two_pole_super_smoother(series, length):
    """
    Applies a 2-pole super smoother filter on 'series' with period 'length'.
    Returns a smoothed numpy array.
    """
    src = series.to_numpy(dtype=float)
    out = np.zeros_like(src)

    t = float(length)
    omega = 2 * np.arctan(1) * 4 / t
    a = np.exp(-np.sqrt(2) * np.arctan(1) * 4 / t)
    b = 2 * a * np.cos((np.sqrt(2)/2) * omega)
    c2 = b
    c3 = -(a**2)
    c1 = 1 - c2 - c3

    # Initialize first values
    if len(src) > 0:
        out[0] = src[0]
    if len(src) > 1:
        out[1] = src[1]

    for i in range(2, len(src)):
        out[i] = c1 * src[i] + c2 * out[i-1] + c3 * out[i-2]

    return out

if use_filt:
    asset_data["Filtered"] = two_pole_super_smoother(asset_data["Price"], filt_per)
else:
    asset_data["Filtered"] = asset_data["Price"]

# ----------------------------------------------------------------------
# 2) Polynomial regression via LU decomposition
# ----------------------------------------------------------------------
def get_val(mat, r, c, rowlen):
    return mat[r * rowlen + c]

def set_val(mat, r, c, rowlen, val):
    mat[r * rowlen + c] = val

def lu_decompose(A, B_size):
    L = [np.nan]*(B_size**2)
    U = [np.nan]*(B_size**2)

    # First row of U, first column of L
    for c in range(B_size):
        set_val(U, 0, c, B_size, get_val(A, 0, c, B_size))
    set_val(L, 0, 0, B_size, 1.0)
    denom0 = get_val(U, 0, 0, B_size)
    for r in range(1, B_size):
        val_r0 = get_val(A, r, 0, B_size) / denom0
        set_val(L, r, 0, B_size, val_r0)

    for r in range(B_size):
        for c in range(B_size):
            if r == c:
                set_val(L, r, c, B_size, 1.0)
            if r < c:
                set_val(L, r, c, B_size, 0.0)
            if r > c:
                set_val(U, r, c, B_size, 0.0)

    for r in range(B_size):
        for c in range(B_size):
            if np.isnan(get_val(L, r, c, B_size)) and r > c:
                temp = get_val(A, r, c, B_size)
                for k in range(c):
                    temp -= get_val(U, k, c, B_size)*get_val(L, r, k, B_size)
                val_rc = temp / get_val(U, c, c, B_size)
                set_val(L, r, c, B_size, val_rc)

            if np.isnan(get_val(U, r, c, B_size)) and r <= c:
                temp = get_val(A, r, c, B_size)
                for k in range(r):
                    temp -= get_val(U, k, c, B_size)*get_val(L, r, k, B_size)
                set_val(U, r, c, B_size, temp)

    return (L, U)

def forward_substitution(L, B):
    B_size = len(B)
    Y = [0.0]*B_size
    Y[0] = B[0] / get_val(L, 0, 0, B_size)
    for r in range(1, B_size):
        temp = B[r]
        for k in range(r):
            temp -= get_val(L, r, k, B_size)*Y[k]
        denom = get_val(L, r, r, B_size)
        Y[r] = temp / denom
    return Y

def backward_substitution(U, Y):
    B_size = len(Y)
    X = [0.0]*B_size
    X[B_size-1] = Y[B_size-1] / get_val(U, B_size-1, B_size-1, B_size)
    for r in range(B_size-2, -1, -1):
        temp = Y[r]
        for k in range(r+1, B_size):
            temp -= get_val(U, r, k, B_size) * X[k]
        denom = get_val(U, r, r, B_size)
        X[r] = temp / denom
    return X

def solve_poly_reg(x_array, y_array, poly_order):
    x_powsums = [np.sum(x_array**k) for k in range(2*poly_order + 1)]
    xy_powsums = [np.sum((x_array**k)*y_array) for k in range(poly_order + 1)]

    size_mat = (poly_order+1)**2
    xp_matrix = [0.0]*size_mat

    for r in range(poly_order+1):
        for c in range(poly_order+1):
            val = x_powsums[r + c]
            set_val(xp_matrix, r, c, (poly_order+1), val)

    L, U = lu_decompose(xp_matrix, poly_order+1)
    Y_sol = forward_substitution(L, xy_powsums)
    coefs = backward_substitution(U, Y_sol)
    return coefs

def evaluate_polynomial(coefs, x):
    val = 0.0
    for i, c in enumerate(coefs):
        val += c * (x**i)
    return val

asset_data["LSMA"] = np.nan
prices_np = asset_data["Filtered"].to_numpy()
N = len(asset_data)

for i in range(N):
    if i - per + 1 - equ_from < 0:
        continue
    fit_end = i - equ_from
    fit_start = fit_end - (per - 1)
    window_prices = prices_np[fit_start : fit_end+1]
    if len(window_prices) < per:
        continue
    x_array = np.arange(1, per+1, dtype=float)
    coefs = solve_poly_reg(x_array, window_prices, order)
    # Evaluate at x = per - (calc_offs - equ_from).
    final_x = float(per) - (calc_offs - equ_from)
    lsma_val = evaluate_polynomial(coefs, final_x)
    asset_data.at[i, "LSMA"] = lsma_val

# ---------------------
# Output only Timestamp and LSMA
# ---------------------
asset_data[["Timestamp", "LSMA"]].to_csv(POLYREG_FILE, index=False)

print(f"Polynomial regression (timestamp, lsma) results written to {POLYREG_FILE}")
