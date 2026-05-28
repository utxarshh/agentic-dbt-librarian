with customers as (

    select * from {{ ref('stg_customers') }}

),

orders as (

    select * from {{ ref('stg_orders') }}

),

customer_orders as (

    select
        customer_id,
        min(ordered_at)                                             as first_order_at,
        max(ordered_at)                                             as most_recent_order_at,
        count(order_id)                                             as number_of_orders,
        sum(case when status = 'completed' then amount else 0 end)  as lifetime_value
    from orders
    group by customer_id

),

final as (

    select
        customers.customer_id,
        customers.first_name,
        customers.last_name,
        customers.email,
        coalesce(customer_orders.first_order_at, null)              as first_order_at,
        coalesce(customer_orders.most_recent_order_at, null)        as most_recent_order_at,
        coalesce(customer_orders.number_of_orders, 0)               as number_of_orders,
        coalesce(customer_orders.lifetime_value, 0)                 as lifetime_value,
        case
            when customer_orders.lifetime_value >= 1000 then 'VIP'
            when customer_orders.lifetime_value >= 500  then 'Loyal'
            when customer_orders.lifetime_value >= 100  then 'Regular'
            else 'New'
        end                                                          as customer_segment
    from customers
    left join customer_orders using (customer_id)

)

select * from final
