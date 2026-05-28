with source as (

    select * from {{ source('jaffle_shop', 'customers') }}

),

renamed as (

    select
        id              as customer_id,
        first_name,
        last_name,
        email,
        created_at,
        updated_at
    from source

)

select * from renamed
