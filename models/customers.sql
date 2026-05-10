select customer_id, first_name from {{ source('jaffle_shop', 'customers') }}
--trigger
--bulletproof
