with orders as (

    select * from {{ ref('stg_orders') }}

),

customers as (

    select * from {{ ref('dim_customers') }}

),

final as (

    select
        orders.order_id,
        orders.customer_id,
        customers.first_name,
        customers.last_name,
        customers.email,
        customers.customer_segment,

        orders.amount,
        orders.bank_transfer_amount,
        orders.coupon_amount,
        orders.credit_card_amount,
        orders.gift_card_amount,
        orders.status,
        orders.ordered_at,

        case
            when orders.status = 'returned' then true
            else false
        end                                                             as is_returned,

        case
            when orders.status in ('completed', 'shipped') then orders.amount
            else 0
        end                                                             as net_revenue

    from orders
    left join customers using (customer_id)

)

select * from final
