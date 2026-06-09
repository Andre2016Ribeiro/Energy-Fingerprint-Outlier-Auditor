
# ⚡ Energy Fingerprint & Outlier Auditor

An advanced energy auditing tool written in Python to analyze electrical load profiles (15-minute interval data) extracted from grid operators (e.g., E-Redes in Portugal). 

The program automatically establishes the facility's baseline consumption pattern, isolates production line shutdowns (partial load profiles), detects micro-anomalies, and quantifies photovoltaic (PV) integration metrics.

---

## 🚀 Key Features

* **Smart Data Preprocessing**: Automates metadata filtering (skips grid headers), normalizes raw active power into accurate kW scales, and programmatically strips out weekends and official holidays (Portugal registry).
* **Baseline Fingerprint (Median 1)**: Isolates the central **90% of standard business days** via macro-quantiles ($q_{0.05}$ to $q_{0.95}$) to draw a clean, unpolluted baseline profile accompanied by a dynamic statistical tolerance band (shaded zone).
* **Reduced Activity Fingerprint (Median 2)**: Dynamically isolates days where daytime production energy dropped by >10%. The algorithm segregates these days to build a standalone, continuous **Secondary Median**, defining the facility's exact electrical footprint when a specific unit or section is turned off.
* **Micro-Anomaly Tracking ($X$ Markers)**: Employs a custom tightened standard deviation threshold ($0.3\sigma$) during active production hours (06:00 - 18:00) to pin-point the exact 15-minute blocks where equipment shortfalls occurred.
* **Rigorous Energy Accounting**: Displays synchronized physical dimensions ($\text{Energy [kWh]} = \text{Average Power [kW]} \times \text{Duration [h]}$) directly on the legend, ordered from the highest energy deficit to the lowest.
* **Solar Potential Assessment**: Highlights the optimal solar radiation window (**09:00 - 17:00**) with a transparent background mask, computing the continuous average base load (kW) and energy weight (%) to support right-sized PV sizing.

---

## 🧮 Statistical & Mathematical Logic

### 1. Macro Filtering (Daily Level)
The script calculates the cumulative energy consumption for every day and calculates boundaries using:
$$q_{\text{inf}} = \text{Quantile}(0.05) \quad \text{and} \quad q_{\text{sup}} = \text{Quantile}(0.95)$$
Days sitting inside this bounds are categorized as **Typical Days** and are the only ones used to calculate the ideal baseline.

### 2. Micro Boundary Construction (15-Min Level)
The grey tolerance band is calculated using the Median and Standard Deviation ($\sigma$) of the selected typical days:
* **Upper Limit**: $\text{Median} + 1.5\sigma$ (Catches unusual peaks)
* **Lower Limit (06:00 - 18:00)**: $\text{Median} - 0.3\sigma$ (Tightened margin to instantly catch minor machine shutdowns)
* **Lower Limit (Nighttime)**: $\text{Median} - 1.5\sigma$ (Loosened margin to account for normal end-of-shift washdowns)

---

## 🛠️ Installation & Setup

1. Clone this repository:
   ```bash
   git clone https://github.com
   cd energy-fingerprint-auditor
   ```

2. Install required standard libraries:
   ```bash
   pip install pandas openpyxl holidays matplotlib numpy
   ```

3. Ensure your source file is an E-Redes exported Excel file located in the script directory. The script expects:
   * **Cell B3**: CPE Code (automatically read into chart title)
   * **Cell B7**: Audit Month/Year (automatically read into chart title)
   * **Row 10**: Real active power readings column structure (`Data`, `Hora`, `Potência Ativa`).

---

## 📈 Usage

Simply execute the script via terminal. It forces a stable graphical window rendering via native operating system UI (`TkAgg` backend):

```bash
python "analise dos consumos.py"
```

### Reading the Outputs:
* **Black Solid Line**: Your perfect facility baseline.
* **Grey Shaded Area**: Stable operations boundaries.
* **Green Shaded Zone / Line**: Your facility's "Activity Reduced Profile". The legend will tell you exactly how many kW that section consumes when active, alongside the shutdown duration in hours.
* **Gold Column Mask**: Your 09:00 - 17:00 solar potential window, complete with baseline demand in kW to avoid net-metering injection overheads.

---

## 📄 License
This project is licensed under the MIT License - feel free to use it for industrial engineering audits and energy optimization workflows.
