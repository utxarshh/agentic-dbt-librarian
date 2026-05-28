with source as (

    select * from {{ source('jaffle_shop', 'orders') }}

),

renamed as (

    select
        id                      as order_id,
        user_id                 as customer_id,
        amount,
        bank_transfer_amount,
        coupon_amount,
        credit_card_amount,
        gift_card_amount,
        status,
        created_at              as ordered_at,
        updated_at
    from source

)

select * from renamed
