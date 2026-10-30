-- Bucket chart data for templates/bucket-chart.html (run through the Supabase connector; replace :month with 'YYYY-MM-01').
-- Planned/spent per bucket come from budget_months + spending_budgets (0001); every expense per bucket from
-- transaction_allocations (0005, target_type = 'bucket') joined to transactions (0001). Output matches templates/sample/buckets-example.json.
select jsonb_build_object(
  'month',    to_char(date :month, 'FMMonth'),
  'title',    to_char(date :month, 'FMMonth') || ' buckets',
  'subtitle', 'Budget buckets',
  'buckets',  coalesce(jsonb_agg(jsonb_build_object(
      'name',    s.name,
      'planned', m.planned,
      'spent',   m.spent,
      -- every expense allocated to this bucket for the month (1st to last day), oldest first
      'expenses', coalesce((select jsonb_agg(jsonb_build_array(coalesce(t.description, 'Transaction'), a.amount, t.date) order by t.date, t.id)
                            from public.transaction_allocations a
                            join public.transactions t on t.id = a.transaction_id
                            where a.target_type = 'bucket' and a.spending_budget_id = s.id and a.budget_month = m.month), '[]'::jsonb)
    ) order by s.sort nulls last, s.name), '[]'::jsonb)
) as chart
from public.budget_months m
join public.spending_budgets s on s.id = m.budget_id
where m.month = date :month;
