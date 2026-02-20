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
Why we made the bold move to say “no” to traditional Construction Management Procurement Models & the questions end clients should be asking.
In Construction Management, procurement often treats the “CM Fee” as the main measure of cost.
That’s understandable, because it’s the most visible number.
But it’s also the trap.
A Construction Manager is fundamentally a service provider.  Their biggest cost isn’t materials.  It isn’t equipment.  It is people and time.  The leadership, coordination, field presence, admin, safety, estimating support, and the day-to-day problem solving required to move a project from concept to closeout.
Here’s the issue we saw repeatedly when large procurement engines ran CM RFPs:
They weren’t actually comparing total cost of delivery.
They were comparing the one line item they could see.
So the debate became: “Your fee is too high.”
When the real question should have been: “Where is the rest of the CM cost being paid.  And more importantly, by whom?”
Because if a proposed CM fee does not cover even the basic, loaded payroll required to do the job properly, the cost doesn’t disappear. It simply shows up somewhere else:
•	buried in trade pricing and contingencies
•	absorbed through change exposure and coordination drift
•	paid for through schedule inefficiency and extended general conditions
•	carried by the owner through risk, uncertainty, and decision fatigue
•	or diluted through under-resourcing (which feels “cheaper” until it isn’t)
This calculator exists to bring visibility to what is normally hidden.
Not to “win” an argument on fee.   But to make sure the owner is asking the right question:
What is the true cost of Construction Management delivery, and where is it being paid?
That realization is one of the reasons Flat Iron exited traditional CM and moved fully into progressive design build: single-point accountability, clarity of cost, and fewer places for risk (and money) to hide.





How to use the calculator (simple step-by-step)
Purpose: Estimate the real payroll cost of a properly resourced CM team for your project, then compare that to the fee proposals you’re receiving.
Step 1 — Set the team you believe is required
In the “Team” section, confirm which roles you think are actually needed for a project of your size and complexity (e.g., CM, PC, Site Manager, Site Assistant, Estimator, Safety).  
Step 2 — Allocate % of time by phase (green inputs)
For each role, enter the % of their weekly time required in:
•	Pre-Construction
•	Construction
•	Post-Construction
This forces the conversation to get real about staffing instead of vague statements like “we’ll support as required.”  Following are guidelines to use, but feel free to use your own educated guess.  Construction Managers for workplace projects => 20,000 SF typically require
•	30% time from a Construction Manager for full project cycle
•	30% time from a Project Coordinator for full project cycle
•	100% time from a Site Manager for construction and post construction and some support in pre-construction.
•	80 to 120 hours of estimating time.
•	A health and safety site visit weekly

Step 3 — Estimate phase durations (weeks)
Enter how many weeks you expect each phase to last. The sheet converts that into the fraction of a year.
Step 4 — Enter loaded compensation (salary + burden)
Input your best assumption for each role:
•	Salary
•	Bonus
•	Other (auto/phone/RRSP/etc.)
•	Burden (the sheet is already assuming payroll burden for EI, CPP, Etc. at 15%)
This yields a loaded annual cost per role.
Step 5 — Review “TOTAL COST OF TIME”
This is the sheet’s estimate of the true payroll cost of the CM team’s time allocated to your project across all phases.
Step 6 — Enter your total project budget 
Input your total project budget.   
Step 7 — Enter what you think the Construction Managers other % Overhead is (% of revenue)
Make an assumption on company overhead costs as a percent of revenue.  This is overhead above and beyond the direct project staff (insurance, rent, utlilities, support staff, leadership / management, professional services, etc.)  
Step 8 — Enter what you think the Construction Managers % profit is (% of revenue)
Make an assumption on the company profit as a percent of revenue.   How much do the actually make on the job to retain as profit in the business.   
Step 9 — Enter the CM fees you received from various bidders (low/mid/high)
Populate the proposal amounts you’re seeing.
Step 10 — Read the two coverage tests
The sheet calculates:
•	% of Payroll CM Team Covered in Fee
•	% of ROM CM Fee Covered in Proposals
If proposals are below 100% payroll coverage, the key question becomes unavoidable:
Where is the remaining CM cost being paid? And do you, as the client, actually know?

 
IGNORE FOR NOW Questions to ask your shortlist of CMs (or your third-party PM)
Use these exactly as written—short, direct, and hard to dodge.
A. Staffing reality (who is actually doing the work?)
1.	Name the specific roles assigned to this project (CM, PC, Site, Safety, Estimating, Closeout).
2.	For each role: what % of their time is allocated in Pre-Con / Construction / Closeout?
3.	Are these people dedicated or shared across multiple projects? How many?
4.	Who is the day-to-day decision maker when issues hit site? (Name + authority level.)
5.	Who owns trade coordination (not just meetings—actual clash, scope gaps, RFIs, sequencing)?
B. Fee integrity (does the fee cover the work?)
6.	Does your proposed fee fully cover the payroll cost of the team you just described?
7.	If not, where is the gap carried (trade pricing, contingency, allowances, change, or owner risk)?
8.	What portion of your fee is tied to actual staffing vs “OH&P”?
9.	If schedule extends, what happens to your staffing cost—is it included or extra?
C. Risk and accountability (where does risk go to hide?)
10.	In CM, who is accountable for scope gaps between consultants and trades?
11.	What are the top 5 most common causes of cost growth on your CM projects—and how are they priced?
12.	When trades miss something, what is your standard mechanism: change, contingency draw, or owner decision?
13.	Who owns the risk of late decisions / incomplete design—and what’s the cost impact mechanism?
D. Truth-in-comparison (what procurement misses)
14.	If we select you because your fee is lower, what must be true operationally for you to still deliver well?
15.	What do you stop doing (or do less of) when fees are compressed?
16.	Show us a real example where you delivered a project with minimal changes—what made it work?
E. Questions for your third-party PM advising you
17.	Are you comparing CM fee only, or total cost of delivery risk?
18.	Where in your model is the cost of coordination failure captured (scope gaps, rework, schedule drag)?
19.	If the CM fee doesn’t cover staffing, what is your belief about where the cost is landing?
20.	What’s your plan to ensure true apples-to-apples staffing across bidders?

        """
    )

# --------
# Inputs
# --------
left, right = st.columns([1.2, 1.0])

with left:
    st.subheader("1) Phase Durations (weeks)")
    c1, c2, c3 = st.columns(3)
    pre_w = c1.number_input("Pre-Construction", value=0, step=1.0)
    con_w = c2.number_input("Construction", value=0, step=1.0)
    post_w = c3.number_input("Post-Construction / Closeout", value=0, step=1.0)

    st.subheader("2) Team & Compensation")
    st.caption("Phase % can be entered as **0–100** or **0–1**. Example: 30 or 0.30 both work.")

    if "team_df" not in st.session_state:
        st.session_state.team_df = pd.DataFrame(
            {
                "Role": DEFAULT_ROLES,
                "Pre %":  [0, 0, 0,  0, 0,  0],
                "Con %":  [0, 0,0,0, 0, 0],
                "Post %": [0, 0, 0,  0,  0, 0],
                "Total compensation": [0, 0, 0, 0, 0, 0],
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

    overhead_pct = st.number_input("Overhead (% of revenue)", min_value=0.0, value=0, step=0.5) / 100.0
    profit_pct = st.number_input("Profit (% of revenue)", min_value=0.0, value=0, step=0.5) / 100.0

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

rom_cov_low = coverage(low_fee, rom_fee) if rom_fee else None
rom_cov_mid = coverage(mid_fee, rom_fee) if rom_fee else None
rom_cov_high = coverage(high_fee, rom_fee) if rom_fee else None

cA, cB = st.columns([1.2, 0.8])

with cA:
    st.subheader("Team Cost Breakdown")
    show_df = calc_df[[
        "Role", "Total compensation", # "Bonus", "Other",
        "Loaded Annual", "Project Year Fraction", "Project Cost"
    ]].copy()

    # Format fraction to %
    show_df["Project Year Fraction"] = (show_df["Project Year Fraction"] * 100).round(2).astype(str) + "%"
# Apply space formatting to currency columns
    show_df["Total compensation"] = show_df["Total compensation"].apply(money)
   # show_df["Bonus"] = show_df["Bonus"].apply(money)
  #  show_df["Other"] = show_df["Other"].apply(money)
    show_df["Loaded Annual"] = show_df["Loaded Annual"].apply(money)
    show_df["Project Cost"] = show_df["Project Cost"].apply(money)

    st.dataframe(
        show_df,
        use_container_width=True,
        hide_index=True,
    )

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

    st.table(cov_table_display)

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

st.markdown("---")

# Optional: show raw assumptions and math
with st.expander("Show calculation details", expanded=False):
    st.write("Phase fractions of year:")
    st.write({
        "Pre": pre_w / 52.0,
        "Construction": con_w / 52.0,
        "Post/Closeout": post_w / 52.0,
    })
    st.write("ROM fee formula (overhead & profit are % of revenue):")
    st.latex(r"\text{ROM Fee} = \frac{\text{Payroll Cost}}{1 - \text{Overhead} - \text{Profit}}")
    st.write({
        "Payroll Cost": total_payroll_cost,
        "Overhead %": overhead_pct,
        "Profit %": profit_pct,
        "ROM Fee": rom_fee,
    })
