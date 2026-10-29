-- FAKE sample data for trying the tracker. Run after all migrations. Every name/amount is invented.
insert into public.accounts (id,name,nickname,institution,account_type,last4,mask,kind,owner_name,funding_role) values
 ('chk-bills','Bills checking','Bills checking','Example Community Bank','checking','1111','1111','checking','Alex Sample','bills'),
 ('card-spend','Spending debit card','Spending card','Example Fintech','checking','2222','2222','checking','Alex Sample','spending'),
 ('cc-payoff','Rewards credit card','Payoff card','Example Card Co','credit_card','3333','3333','credit_card','Alex Sample','debt');
insert into public.income_sources values ('client-a','Client A retainer',3000,1,'chk-bills',true),('client-b','Client B retainer',1500,1,'chk-bills',true);
insert into public.income_events (id,source_id,month,received_date,amount,account_id,kind,notes) values
 ('client-a-2026-01','client-a','2026-01-01','2026-01-02',3000,'chk-bills','income','January retainer');
insert into public.bill_templates (id,name,default_amount,due_day,category,payee_hint) values
 ('mortgage','Mortgage',1200,1,'Housing','EXAMPLE MORTGAGE'),('electric','Electric',140,12,'Utilities','EXAMPLE POWER'),
 ('internet','Internet',70,18,'Utilities','EXAMPLE ISP'),('auto-ins','Auto insurance',110,20,'Insurance','EXAMPLE INS'),('streaming','Streaming',16,5,'Subscriptions','STREAMCO');
insert into public.bill_instances (template_id,month,due_date,amount,status,paid_amount,paid_date,paid_from)
 select id,'2026-01-01',make_date(2026,1,due_day),default_amount,case when due_day<=12 then 'cleared' else 'unpaid' end,
        case when due_day<=12 then default_amount end, case when due_day<=12 then make_date(2026,1,due_day) end, case when due_day<=12 then 'chk-bills' end
 from public.bill_templates;
insert into public.one_off_bills (id,payee,amount,month,due_date,status) values ('dentist-2026-01','Example Dental',180,'2026-01-01','2026-01-25','unpaid');
insert into public.spending_budgets values ('groceries','Groceries',500,'card-spend',1),('fuel','Fuel',250,'card-spend',2),('dining','Food (eating out)',150,'card-spend',3),('shopping','Shopping',100,'card-spend',4);
insert into public.budget_months (budget_id,month,planned,spent) values ('groceries','2026-01-01',500,310),('fuel','2026-01-01',250,120),('dining','2026-01-01',150,95),('shopping','2026-01-01',100,40);
insert into public.transfers values ('budget-2026-01','2026-01-01','chk-bills','card-spend',1000,1000,'2026-01-02',null,'done','Monthly spending budget');
insert into public.transactions (plaid_id,external_id,account_id,date,amount,description,category,bank_status) values
 ('sample-1','sample-1','chk-bills','2026-01-02',3000,'CLIENT A ACH DEPOSIT','Income','posted'),
 ('sample-2','sample-2','chk-bills','2026-01-01',-1200,'EXAMPLE MORTGAGE PMT','Housing','posted'),
 ('sample-3','sample-3','chk-bills','2026-01-02',-1000,'TRANSFER TO SPENDING CARD','Transfer','posted'),
 ('sample-4','sample-4','chk-bills','2026-01-12',-140,'EXAMPLE POWER AUTOPAY','Utilities','posted'),
 ('sample-5','sample-5','chk-bills','2026-01-14',-22.50,'CORNER CAFE','Food (eating out)','pending');
update public.transactions t set matched_bill_instance=b.id from public.bill_instances b join public.bill_templates bt on bt.id=b.template_id
 where t.description like bt.payee_hint||'%' and b.month='2026-01-01';
insert into public.debts (snowball_order,name,apr,min_payment,starting_balance,as_of,account_id) values
 (1,'Store card',24.99,35,900,'2026-01-01',null),(2,'Payoff card',21.5,90,4200,'2026-01-01','cc-payoff'),(3,'Auto loan',6.9,320,11000,'2026-01-01',null);
insert into public.settings values ('snowball','{"extra_per_month":200}'),('balances','{"chk-bills":{"available":2450.00,"as_of":"2026-01-14"}}');
