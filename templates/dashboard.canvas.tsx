import { Page, Section, Metrics, Table, Bars, Segmented, Grid, Rows, Callout, Text, Properties, useState } from "grok/canvas";

// GrokBudgetTracker monthly dashboard. Grok replaces DATA each month from Supabase (see templates/DASHBOARD.md).
// This copy holds FAKE sample data only.
const DATA = {
  month: "January 2026",
  asOf: "1/14/2026",
  income: [
    { source: "Client A retainer", frequency: "monthly", expected: 3000, received: 3000 },
    { source: "Client B retainer", frequency: "monthly", expected: 1500, received: 0 },
    { source: "Part-time paycheck", frequency: "biweekly", expected: 1860, received: 620 },
  ],
  bills: [
    { name: "Mortgage", kind: "Recurring", category: "Housing", due: "1/1", amount: 1200, status: "cleared" },
    { name: "Streaming", kind: "Recurring", category: "Subscriptions", due: "1/5", amount: 16, status: "cleared" },
    { name: "Electric", kind: "Recurring", category: "Utilities", due: "1/12", amount: 140, status: "cleared" },
    { name: "Internet", kind: "Recurring", category: "Utilities", due: "1/18", amount: 70, status: "unpaid" },
    { name: "Auto insurance", kind: "Recurring", category: "Insurance", due: "1/20", amount: 110, status: "unpaid" },
    { name: "Example Dental", kind: "One-off", category: "Medical", due: "1/25", amount: 180, status: "unpaid" },
  ],
  buckets: [
    { name: "Groceries", budget: 500, spent: 310 },
    { name: "Fuel", budget: 250, spent: 120 },
    { name: "Food (eating out)", budget: 150, spent: 95 },
    { name: "Shopping", budget: 100, spent: 40 },
  ],
  review: [
    { account: "Bills checking (…1111)", items: 2, total: -162.5, skipped: 1, oldest: "1/12" },
    { account: "Spending card (…2222)", items: 3, total: -61.2, skipped: 0, oldest: "1/13" },
  ],
  debts: [
    { order: 1, name: "Store card", apr: 24.99, min: 35, balance: 900, clears: "Jun 2026" },
    { order: 2, name: "Payoff card", apr: 21.5, min: 90, balance: 4200, clears: "Aug 2027" },
    { order: 3, name: "Auto loan", apr: 6.9, min: 320, balance: 11000, clears: "Jun 2028" },
  ],
  snowball: { extra: 200, months: 29, debtFree: "Jun 2028", interest: 2061.15 },
};

const money = (n: number) => (n < 0 ? "-" : "") + "$" + Math.abs(n).toLocaleString("en-US", { minimumFractionDigits: n % 1 ? 2 : 0, maximumFractionDigits: 2 });
const sum = (xs: number[]) => xs.reduce((a, b) => a + b, 0);

export default function BudgetDashboard() {
  const [billView, setBillView] = useState<"all" | "unpaid" | "paid">("all");
  const [spendView, setSpendView] = useState<"buckets" | "income">("buckets");

  const incExp = sum(DATA.income.map((i) => i.expected));
  const incRec = sum(DATA.income.map((i) => i.received));
  const paid = DATA.bills.filter((b) => b.status !== "unpaid");
  const unpaid = DATA.bills.filter((b) => b.status === "unpaid");
  const billsTotal = sum(DATA.bills.map((b) => b.amount));
  const budget = sum(DATA.buckets.map((b) => b.budget));
  const spent = sum(DATA.buckets.map((b) => b.spent));
  const leftOver = incRec - billsTotal - budget;
  const reviewCount = sum(DATA.review.map((r) => r.items));
  const shownBills = billView === "all" ? DATA.bills : billView === "paid" ? paid : unpaid;

  return (
    <Page
      title={`Budget Dashboard — Sample (${DATA.month})`}
      summary={`Sample data only. Status as of ${DATA.asOf}. Grok refreshes this Page each month; the PDFs are the printable version.`}
      width="wide"
    >
      <Text>{leftOver < 0 ? `Planned spending is ${money(-leftOver)} more than the income received so far.` : `After bills and bucket budgets, ${money(leftOver)} of the income received so far is left over.`}</Text>
      <Metrics
        metrics={[
          { value: money(incRec), label: "Income received", detail: `of ${money(incExp)} expected` },
          { value: `${paid.length} paid · ${unpaid.length} unpaid`, label: "Bills", detail: `${money(sum(unpaid.map((b) => b.amount)))} still due`, tone: unpaid.length ? "warning" : "success" },
          { value: money(spent), label: "Bucket spending", detail: `of ${money(budget)} budgeted`, tone: spent > budget ? "danger" : undefined },
          { value: money(leftOver), label: "Left over (planned)", detail: "received − bills − buckets", tone: leftOver < 0 ? "danger" : "success" },
        ]}
      />

      <Grid columns={2}>
        <Section heading="Bills" caption={`${DATA.bills.length} this month · ${money(billsTotal)} planned`} actions={
          <Segmented value={billView} onChange={setBillView} options={[
            { value: "all", label: "All", count: DATA.bills.length },
            { value: "unpaid", label: "Unpaid", count: unpaid.length },
            { value: "paid", label: "Paid", count: paid.length },
          ]} />
        }>
          <Table
            columns={["Bill", "Type", "Due", "Amount", "Status"]}
            align={["start", "start", "start", "end", "start"]}
            rows={shownBills.map((b) => [
              b.name,
              b.category ? `${b.kind}: ${b.category}` : b.kind,
              b.due,
              money(b.amount),
              b.status === "unpaid" ? { text: `Due ${b.due}`, tone: "warning" } : { text: b.status === "cleared" ? "Cleared" : "Paid", tone: "success" },
            ])}
          />
        </Section>

        <Section heading={spendView === "buckets" ? "Budget buckets" : "Income"} caption={spendView === "buckets" ? `${money(spent)} of ${money(budget)} spent` : `${money(incRec)} of ${money(incExp)} received`} actions={
          <Segmented value={spendView} onChange={setSpendView} options={[{ value: "buckets", label: "Buckets" }, { value: "income", label: "Income" }]} />
        }>
          {spendView === "buckets" ? (
            <Bars bars={DATA.buckets.map((b) => ({ label: b.name, value: b.budget > 0 ? Math.round((100 * b.spent) / b.budget) : 0, display: `${money(b.spent)} of ${money(b.budget)}`, meta: b.spent > b.budget ? `${money(b.spent - b.budget)} over` : `${money(b.budget - b.spent)} left` }))} emphasis="none" />
          ) : (
            <Table
              columns={["Source", "Frequency", "Expected", "Received", "Status"]}
              align={["start", "start", "end", "end", "start"]}
              rows={DATA.income.map((i) => [
                i.source, i.frequency, money(i.expected), money(i.received),
                i.received >= i.expected ? { text: "Received", tone: "success" } : i.received > 0 ? { text: `${money(i.expected - i.received)} to come`, tone: "warning" } : { text: "Not in yet", tone: "warning" },
              ])}
            />
          )}
        </Section>
      </Grid>

      <Grid columns={2}>
        <Section heading="Needs review" caption={`${reviewCount} transactions waiting for the Daily Transaction Review`}>
          <Rows rows={DATA.review.map((r) => ({
            title: r.account,
            detail: `${r.items} transactions · ${money(r.total)}${r.skipped ? ` · ${r.skipped} skipped earlier` : ""}`,
            meta: `oldest ${r.oldest}`,
            status: { label: `${r.items} to review`, tone: "warning" },
          }))} />
        </Section>

        <Section heading="Debt snowball" caption={`${money(sum(DATA.debts.map((d) => d.balance)))} owed · +${money(DATA.snowball.extra)}/mo extra`}>
          <Properties items={[
            { label: "Debt-free", value: `${DATA.snowball.debtFree} (${DATA.snowball.months} months)` },
            { label: "Interest along the way", value: money(DATA.snowball.interest) },
          ]} />
          <Table
            columns={["#", "Debt", "APR", "Minimum", "Balance", "Clears"]}
            align={["start", "start", "end", "end", "end", "start"]}
            emphasis={0}
            rows={DATA.debts.map((d) => [String(d.order), d.name, `${d.apr.toFixed(2)}%`, money(d.min), money(d.balance), d.clears])}
          />
        </Section>
      </Grid>

      <Callout tone="info" lead="Printable version">
        <Text>Ask Grok for this month's PDFs (Monthly Budget Plan and Where the Money Went) to print or file.</Text>
      </Callout>
    </Page>
  );
}
