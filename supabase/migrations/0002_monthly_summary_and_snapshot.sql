-- 0002_monthly_summary_and_snapshot.sql: reporting view + dashboard_snapshot(month) used by the templates.

create view public.monthly_summary with (security_invoker = true) as
select m.month,
  (select coalesce(sum(expected_amount),0) from public.income_sources where active) as income_expected,
  (select coalesce(sum(amount),0) from public.income_events e where e.month=m.month and e.kind='income') as income_banked,
  (select coalesce(sum(amount),0) from public.income_events e where e.month=m.month and e.kind in ('one_off_income','transfer_in')) as other_income,
  (select coalesce(sum(amount),0) from public.bill_instances b where b.month=m.month) as fixed_planned,
  (select coalesce(sum(coalesce(paid_amount,amount)),0) from public.bill_instances b where b.month=m.month and status<>'unpaid') as fixed_paid,
  (select coalesce(sum(amount),0) from public.bill_instances b where b.month=m.month and status='unpaid') as fixed_left,
  (select count(*) from public.bill_instances b where b.month=m.month and status='unpaid') as fixed_left_count,
  (select coalesce(sum(amount),0) from public.one_off_bills o where o.status='unpaid' and o.month<=m.month) as one_offs_left,
  (select count(*) from public.one_off_bills o where o.status='unpaid' and o.month<=m.month) as one_offs_left_count,
  (select coalesce(sum(planned),0) from public.budget_months bm where bm.month=m.month) as spending_planned,
  (select coalesce(sum(spent),0) from public.budget_months bm where bm.month=m.month) as spending_spent
from (select distinct month from public.bill_instances) m;
revoke all on public.monthly_summary from anon, authenticated;

-- Server-only snapshot used by build_dashboard.py (run via MCP execute_sql; anon/authenticated cannot execute).
create or replace function public.dashboard_snapshot(p_month date)
returns jsonb language sql stable security invoker set search_path = '' as $$
select jsonb_build_object(
 'month', p_month,
 'summary', (select to_jsonb(s) from public.monthly_summary s where s.month=p_month),
 'balances', (select value from public.settings where key='balances'),
 'snowball', (select value from public.settings where key='snowball'),
 'income_sources', (select coalesce(jsonb_agg(to_jsonb(i) order by i.expected_amount desc),'[]') from public.income_sources i where active),
 'income_events', (select coalesce(jsonb_agg(to_jsonb(e) order by e.received_date),'[]') from public.income_events e where e.month=p_month),
 'bills', (select coalesce(jsonb_agg(jsonb_build_object('kind','fixed','id',b.template_id,'name',t.name,'category',t.category,'due_date',b.due_date,'amount',b.amount,'paid_amount',b.paid_amount,'status',b.status,'unverified',t.unverified,'estimated',b.estimated,'notes',b.notes) order by b.due_date, t.name),'[]') from public.bill_instances b join public.bill_templates t on t.id=b.template_id where b.month=p_month),
 'one_offs', (select coalesce(jsonb_agg(to_jsonb(o) order by o.due_date),'[]') from public.one_off_bills o where o.month=p_month or (o.status='unpaid' and o.month<p_month)),
 'budgets', (select coalesce(jsonb_agg(jsonb_build_object('id',s.id,'name',s.name,'planned',m.planned,'spent',m.spent) order by s.sort),'[]') from public.budget_months m join public.spending_budgets s on s.id=m.budget_id where m.month=p_month),
 'transfers', (select coalesce(jsonb_agg(to_jsonb(x) order by x.date),'[]') from public.transfers x where x.month=p_month),
 'transactions', (select coalesce(jsonb_agg(jsonb_build_object('date',t.date,'amount',t.amount,'description',t.description,'category',t.category,'pending',t.pending,'matched',coalesce(bt.name,o.payee)) order by t.date desc, t.id),'[]')
    from public.transactions t left join public.bill_instances bi on bi.id=t.matched_bill_instance left join public.bill_templates bt on bt.id=bi.template_id left join public.one_off_bills o on o.id=t.matched_one_off
    where t.date >= p_month and t.date < (p_month + interval '1 month')),
 'debts', (select coalesce(jsonb_agg(jsonb_build_object('order',d.snowball_order,'name',d.name,'apr',d.apr,'min',d.min_payment,'start',d.starting_balance,
     'paid',(select coalesce(sum(amount),0) from public.debt_payments p where p.debt_id=d.id)) order by d.snowball_order),'[]') from public.debts d where active)
);
$$;
revoke all on function public.dashboard_snapshot(date) from public, anon, authenticated;
