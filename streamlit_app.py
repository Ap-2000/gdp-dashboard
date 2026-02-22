import streamlit as st
import pandas as pd

# ----------------------------
# CM True Cost Calculator App
# ----------------------------

DEFAULT_ROLES = [
    "CM",
    "Project Coordinator",
    "Site Manager",
    "Site Assistant",
    "Estimator",
    "Safety",
]

def percent_to_decimal(x) -> float:
    """Accepts either 0-1 or 0-100 and returns 0-1."""
    try:
        v = float(x)
    except Exception:
        return 0.0
    if v > 1.0:
        return v / 100.0
    return v

def money(x) -> str:
    try:
        return f"${float(x):,.0f}".replace(",", " ")
    except Exception:
        return "$0"

def validate_rows(df: pd.DataFrame):
    warnings = []
    for i, row in df.iterrows():
        pre = percent_to_decimal(row.get("Pre %", 0))
        con = percent_to_decimal(row.get("Con %", 0))
        post = percent_to_decimal(row.get("Post %", 0))
        total = pre + con + post
        if total > 1.0001:
            warnings.append(
                f"Row {i+1} ({row.get('Role','(role)')}): Pre+Con+Post = {total*100:.1f}% (should be ≤ 100%)."
            )
    return warnings

def compute_costs(df: pd.DataFrame, pre_w: float, con_w: float, post_w: float, burden_pct: float):
    # Fractions of a year
    pre_f = pre_w / 52.0
    con_f = con_w / 52.0
    post_f = post_w / 52.0

    out = df.copy()

    # Clean numeric columns
    for col in ["Pre %", "Con %", "Post %", "Total compensation"]:
        if col not in out.columns:
            out[col] = 0.0
        out[col] = pd.to_numeric(out[col], errors="coerce").fillna(0.0)

    # Convert % columns to decimals (0-1)
    out["Pre_dec"] = out["Pre %"].apply(percent_to_decimal)
    out["Con_dec"] = out["Con %"].apply(percent_to_decimal)
    out["Post_dec"] = out["Post %"].apply(percent_to_decimal)

    out["Base Annual"] = out["Total compensation"] #+ out["Bonus"] + out["Other"]
    out["Loaded Annual"] = out["Base Annual"] * (1.0 + burden_pct)

    # Portion of year each role is allocated to this project
    out["Project Year Fraction"] = (
        out["Pre_dec"] * pre_f
        + out["Con_dec"] * con_f
        + out["Post_dec"] * post_f
    )

    out["Project Cost"] = out["Loaded Annual"] * out["Project Year Fraction"]

    total_payroll_cost = float(out["Project Cost"].sum())
    return out, total_payroll_cost

def required_fee_from_overhead_profit(total_payroll_cost: float, overhead_pct: float, profit_pct: float):
    """
    Overhead and profit expressed as % of revenue (fee).
    required_fee = payroll / (1 - overhead - profit)
    """
    denom = 1.0 - overhead_pct - profit_pct
    if denom <= 0:
        return None
    return total_payroll_cost / denom

# ----------------------------
# UI
# ----------------------------
st.set_page_config(page_title="CM True Cost Calculator", layout="wide")
st.title("CM True Cost Calculator")
st.caption("Estimate the loaded CM team cost across project phases and compare to fee proposals.")

with st.expander("How to use", expanded=False):
    st.markdown(
        """
1. Enter **phase durations (weeks)**.
2. Fill the **team table** (roles, phase % time, and compensation).
3. Set **burden**, **overhead**, and **profit** assumptions.
4. Enter **fee proposals** (low/mid/high).
5. Review **TOTAL COST OF TIME**, and coverage vs payroll and ROM fee.
        """
    )

with st.expander("What is the real cost of construction management", expanded=False):
    st.markdown(
        """
Why This Calculator Exists

A Construction Manager is a service provider.

Their primary cost is not materials.

It is people and time.  Leadership, coordination, oversight, and daily problem solving.

Yet in most CM RFPs, the conversation focuses almost entirely on one number:

The fee.

That’s the most visible line item.

But it’s rarely the full cost of delivery.

If a proposed CM fee does not realistically cover the payroll required to properly staff your project or factor in a reasonable overhead and profit, the cost does not disappear. It simply moves:

- into trade pricing
- into contingencies
- into change exposure
- into schedule inefficiencies
- into owner-carried risk
- into hidden fees

Procurement may know exactly what they are paying the CM.

They often do not know what they are paying elsewhere to cover for an artificially low CM fee.

This calculator brings visibility to that gap.

It estimates the true staffing cost required to properly deliver your project, allows you to pick a reasonable overhead and profit percent and compares it to the fees proposed.

Because the real question is not:

“Who has the lowest fee?”

It is:

“Does the fee realistically support proper delivery - or is part of the cost going to be hidden somewhere else?”

A successful project is about partnership.  It requires trust and honesty at its foundation.  If you can't simply see what are are paying - the foundation is rocky from the start.  Clarity upfront protects cost, schedule, head aches and outcome at the end.  


        """
    )

# --------
# Inputs
# --------
left, right = st.columns([1.2, 1.0])

with left:
    st.subheader("1) Phase Durations (weeks)")
    c1, c2, c3 = st.columns(3)
    pre_w = c1.number_input("Pre-Construction", min_value=0.0, value=0.0, step=1.0)
    con_w = c2.number_input("Construction", min_value=0.0, value=0.0, step=1.0)
    post_w = c3.number_input("Post-Construction / Closeout", min_value=0.0, value=0.0, step=1.0)

    st.subheader("2) Team & Compensation")
    st.caption("Phase % can be entered as **0–100** or **0–1**. Example: 30 or 0.30 both work.")

    if "team_df" not in st.session_state:
        st.session_state.team_df = pd.DataFrame(
            {
                "Role": DEFAULT_ROLES,
                "Total compensation": [0, 0, 0, 0, 0, 0],
                "Pre %":  [30, 30, 10,  0, 15,  0],
                "Con %":  [30, 30, 100, 50, 0, 10],
                "Post %": [30, 30, 100, 50,  0, 10],
              #  "Bonus":  [0,   0,   0,  0,  0,  0],
              #  "Other":  [ 0,   0,   0,  0,  0,  0],
            }
        )

    team_df = st.data_editor(
    st.session_state.team_df,
    use_container_width=True,
    num_rows="dynamic",
    column_config={
        "Role": st.column_config.TextColumn(required=True),
        "Pre %": st.column_config.NumberColumn(min_value=0.0),
        "Con %": st.column_config.NumberColumn(min_value=0.0),
        "Post %": st.column_config.NumberColumn(min_value=0.0),
        "Total compensation": st.column_config.NumberColumn(min_value=0.0, format="%.0f"),
      #  "Bonus": st.column_config.NumberColumn(min_value=0.0, format="%.0f"),
      #  "Other": st.column_config.NumberColumn(min_value=0.0, format="%.0f"),
    },
    key="team_editor",
)

   
  #  row_warnings = validate_rows(team_df)
  #  if row_warnings:
  #      st.warning("Check phase allocations:\n\n- " + "\n- ".join(row_warnings))

with right:
    st.subheader("3) Assumptions")
    burden_pct = st.number_input("Payroll burden (%)", min_value=0.0, value=15.0, step=0.5) / 100.0

    st.markdown("---")
    st.subheader("4) Project & Fee Inputs")
    budget_input = st.text_input(
    "Total project budget ($)",
    value="0"
    )

    project_budget = float(budget_input.replace(" ", "")) if budget_input else 0.0

    overhead_pct = st.number_input("Overhead (% of revenue)", min_value=0.0, value=0.0, step=0.5) / 100.0
    profit_pct = st.number_input("Profit (% of revenue)", min_value=0.0, value=0.0, step=0.5) / 100.0

    if overhead_pct + profit_pct >= 1.0:
        st.error("Overhead% + Profit% must be less than 100% to compute ROM fee.")

    st.markdown("---")
    st.subheader("5) Fee Proposals")
    low_fee_input = st.text_input("Low fee proposal ($)", value="0")
    mid_fee_input = st.text_input("Mid fee proposal ($)", value="0")
    high_fee_input = st.text_input("High fee proposal ($)", value="0")

    low_fee = float(low_fee_input.replace(" ", "")) if low_fee_input else 0.0
    mid_fee = float(mid_fee_input.replace(" ", "")) if mid_fee_input else 0.0
    high_fee = float(high_fee_input.replace(" ", "")) if high_fee_input else 0.0

# -------------
# Calculations
# -------------
calc_df, total_payroll_cost = compute_costs(team_df, pre_w, con_w, post_w, burden_pct)
rom_fee = required_fee_from_overhead_profit(total_payroll_cost, overhead_pct, profit_pct)

# -------------
# Results
# -------------
st.markdown("## Results")

m1, m2, m3, m4 = st.columns(4)

m1.metric("TOTAL COST OF TIME (Payroll)", money(total_payroll_cost))

# ---- New metrics ----

overhead_dollars = project_budget * overhead_pct
profit_dollars = project_budget * profit_pct
total_fee = total_payroll_cost + overhead_dollars + profit_dollars

m2.metric("Overhead ($)", money(overhead_dollars))
m3.metric("Profit ($)", money(profit_dollars))
m4.metric("Total Fee ($)", money(total_fee))

st.markdown("---")

# Coverage calculations
def coverage(proposal_fee: float, denom: float):
    if denom <= 0:
        return None
    return proposal_fee / denom * 100.0

pay_cov_low = coverage(low_fee, total_payroll_cost)
pay_cov_mid = coverage(mid_fee, total_payroll_cost)
pay_cov_high = coverage(high_fee, total_payroll_cost)

rom_cov_low  = coverage(low_fee, total_fee) if total_fee else None
rom_cov_mid  = coverage(mid_fee, total_fee) if total_fee else None
rom_cov_high = coverage(high_fee, total_fee) if total_fee else None

cA, cB = st.columns([1.2, 0.8])


with cB:
    st.subheader("Coverage Tests")

    cov_table = pd.DataFrame({
        "Proposal": ["Low", "Mid", "High"],
        "Fee ($)": [low_fee, mid_fee, high_fee],
        "% Payroll Covered": [pay_cov_low, pay_cov_mid, pay_cov_high],
        "% ROM Fee Covered": [rom_cov_low, rom_cov_mid, rom_cov_high],
    })

    def fmt_pct(x):
        if x is None:
            return "—"
        return f"{x:.1f}%"

    cov_table_display = cov_table.copy()
    cov_table_display["Fee ($)"] = cov_table_display["Fee ($)"].apply(money)
    cov_table_display["% Payroll Covered"] = cov_table_display["% Payroll Covered"].apply(fmt_pct)
    cov_table_display["% ROM Fee Covered"] = cov_table_display["% ROM Fee Covered"].apply(fmt_pct)

    def highlight_coverage(val):
        try:
            # Handle dash case
            if val in ["—", "-", None]:
                return ""

            # Remove % and convert to float
            num = float(str(val).replace('%', ''))

            if num < 100:
                return "background-color: #5A1E1E; color: white;"  # red
            else:
                return "background-color: #1E5A3A; color: white;"  # green
        except:
            return ""

    styled_table = cov_table_display.style.map(
        highlight_coverage,
        subset=["% Payroll Covered", "% ROM Fee Covered"]
)

    st.dataframe(
        styled_table,
        use_container_width=True,
        hide_index=True
)

    # Simple interpretation
    st.markdown("### Interpretation")
    if total_payroll_cost <= 0:
        st.info("Enter team and durations to compute payroll cost.")
    else:
        if pay_cov_mid is not None and pay_cov_mid < 100:
            st.warning("Mid proposal does **not** cover payroll cost (below 100%).")
        else:
            st.success("Mid proposal covers payroll cost (≥ 100%).")

        if rom_fee is not None:
            if rom_cov_mid is not None and rom_cov_mid < 100:
                st.warning("Mid proposal is **below** ROM required fee (overhead/profit not fully covered).")
            else:
                st.success("Mid proposal meets/exceeds ROM required fee (covers payroll + overhead + profit).")

# st.markdown("---")

# Optional: show raw assumptions and math
#with st.expander("Show calculation details", expanded=False):
 #   st.write("Phase fractions of year:")
 #   st.write({
#        "Pre": pre_w / 52.0,
#     "Construction": con_w / 52.0,
 #     "Post/Closeout": post_w / 52.0,
#    })
#    st.write("ROM fee formula (overhead & profit are % of revenue):")
 #   st.latex(r"\text{ROM Fee} = \frac{\text{Payroll Cost}}{1 - \text{Overhead} - \text{Profit}}")
  #  st.write({
   #     "Payroll Cost": total_payroll_cost,
    #    "Overhead %": overhead_pct,
     #   "Profit %": profit_pct,
      #  "ROM Fee": rom_fee,
  #  })
