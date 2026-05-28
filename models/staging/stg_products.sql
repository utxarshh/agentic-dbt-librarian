with source as (

    select * from {{ source('jaffle_shop', 'products') }}

),

renamed as (

    select
        id              as product_id,
        name            as product_name,
        sku,
        category,
        price,
        created_at
    from source

)

select * from renamed
