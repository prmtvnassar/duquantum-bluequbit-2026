# Run records: quick start

For scripts and agents, use the normalized [CSV records](csv/README.md). The six `.xlsx` files are optional human dashboards and remain unchanged; CSV and XLSX do not synchronize automatically. All six workbooks are blank templates, so no historical estimates need migration. Import the released template before recording target values.

The workbook route below remains available if you prefer manual analysis and `scripts/export_submission.py`.

Use `sample_1.xlsx` and `sample_2.xlsx` to test choices before running the four hidden circuits. Each workbook covers one circuit. Yellow cells are inputs; the initial precision settings are editable. Results are blank until you run jobs.

1. **Set up:** In **Status**, enter the official circuit ID and required qubit count. In **Qubits**, paste the official qubit IDs into column A. For samples, put known exact values in column B.
2. **Record runs:** Add one row per job in **Jobs** (including status, time, and credits). Add one row per qubit result in **Estimates**, with its method, precision setting, estimate, and job ID. Set **Accepted** to `1`; after a rerun, set the old row to `0` without deleting it.
3. **Compare:** In **Qubits**, read the signed PPS/MPS changes and trend checks. In sample **Status** tabs, compare complete candidates against exact values and enter each official kit score in **Official score**. A small change or positive backtest gain does not prove accuracy.
4. **Choose and move on:** Select the whole-circuit **CSV choice** in **Status**. For a theory or sample-based correction, fill **Calibrated estimate** in **Qubits** and name the model in **Status**. Use that choice on hidden circuits only after checking both samples. When **CSV export check** says *Ready for template check*, review the remaining credits and time, then set **Run decision** to *Move on* when another job is not worthwhile.

After the official kit arrives, run from `D:\BluQubit`, replacing the template path with the kit's actual CSV file:

```powershell
python .\scripts\export_submission.py --set sample --template "PATH_TO_SAMPLE_TEMPLATE.csv"
python .\scripts\export_submission.py --template "PATH_TO_HIDDEN_TEMPLATE.csv"
```

The exporter checks circuit/qubit IDs, completeness, and the official row order before writing to `submissions/`.
