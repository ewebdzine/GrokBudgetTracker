-- Default category template (no amounts). Derived from a real household setup, genericized.
-- Run after 0004. Edit freely; ids are stable keys used by bill_templates/spending_budgets/transactions.
insert into public.categories (id,name,parent_group,default_expense_type,sort) values
 -- recurring / fixed bills
 ('housing','Housing (mortgage / rent / property tax)','Housing & Loan','recurring_fixed',10),
 ('utilities','Utilities (electric, water, trash, propane, internet, phone)','Utilities','recurring_fixed',20),
 ('insurance','Insurance (health, auto, home, life)','Insurance','recurring_fixed',30),
 ('subscriptions','Subscriptions & streaming','Subscriptions','recurring_fixed',40),
 ('kids-school','Kids & school (lunch, fees)','School','recurring_fixed',50),
 ('savings','Savings / investing','Savings / Investing','recurring_fixed',60),
 ('taxes','Income / estimated taxes','Debt & Tax payments','recurring_fixed',70),
 ('debt-payment','Debt payment (loans, cards, payment plans)','Debt & Tax payments','recurring_fixed',80),
 ('household-services','Household services (pest control etc.)','Household','recurring_fixed',90),
 -- budget buckets
 ('groceries','Groceries','Spending','budget_bucket',100),
 ('fuel-vehicle','Gas, fuel & vehicle maintenance','Spending','budget_bucket',110),
 ('dining','Food (dining out)','Spending','budget_bucket',120),
 ('home-maintenance','Home maintenance / hardware','Spending','budget_bucket',130),
 ('drinks','Drinks & coffee','Spending','budget_bucket',140),
 ('entertainment','Entertainment','Spending','budget_bucket',150),
 ('animal-supplies','Animal / pet supplies','Spending','budget_bucket',160),
 ('shopping','Shopping','Spending','budget_bucket',170),
 ('family-allowance','Family allowance (e.g. a kid''s monthly money)','Spending','budget_bucket',180),
 -- one-offs
 ('medical','Medical / dental / vet','One-off','one_off',200),
 ('auto-repair','Auto & equipment repair','One-off','one_off',210),
 ('education','Tuition & education','One-off','one_off',220),
 ('gifts','Gifts','One-off','one_off',230),
 ('bank-fees','Bank fees (overdraft, ATM)','One-off','one_off',240),
 ('other-one-off','Other one-off','One-off','one_off',250),
 -- non-spending
 ('transfer-own','Transfer between my accounts','Transfers','transfer',300),
 ('card-payment','Credit card payment (not spending)','Transfers','transfer',310),
 ('income-regular','Income: regular / retainer','Income','income',400),
 ('income-one-off','Income: one-off (sale etc.)','Income','income',410),
 ('refund','Refund (not income)','Income','income',420),
 ('cashback','Cashback','Income','income',430)
on conflict (id) do nothing;
