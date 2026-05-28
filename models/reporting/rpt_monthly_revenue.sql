with orders as (

    select * from {{ ref('fct_orders') }}

),

monthly as (

    select
        date_trunc('month', ordered_at)                                 as month,
        count(order_id)                                                 as order_count,
        count(distinct customer_id)                                     as unique_customers,
        sum(net_revenue)                                                as total_revenue,
        avg(net_revenue)                                                as avg_order_value,
        sum(case when is_returned then 1 else 0 end)                    as return_count,
        sum(case when is_returned then amount else 0 end)               as returned_revenue
    from orders
    group by 1

)

select
    month,
    order_count,
    unique_customers,
    total_revenue,
    avg_order_value,
    return_count,
    returned_revenue,
    total_revenue - returned_revenue                                     as net_revenue,
    round(100.0 * return_count / nullif(order_count, 0), 2)             as return_rate_pct
from monthly
order by month
