## Example AI-Generated Output

This file shows what the **Agentic dbt Librarian** produces for `fct_orders.sql` after the AI agent analyzes the SQL code and upstream lineage context.

The AI was given:
- The raw SQL of `fct_orders.sql`
- Upstream descriptions from `stg_orders` and `dim_customers` (from `manifest.json`)
- Existing partial descriptions to preserve

---

### Generated `schema.yml` (AI Output)

```yaml
version: 2

models:
  - name: fct_orders
    description: >
      The central fact table for all order-level analytics at Jaffle Shop.
      Joins staged orders with the customer dimension to produce a single,
      enriched row per order — including customer segment, all payment method
      breakdowns, and revenue impact flags. This is the primary input for
      executive revenue dashboards, MRR calculations, and return-rate tracking.
      All monetary values are in USD. Cancelled and returned orders are included
      with a net_revenue of 0 to preserve order counts.

    columns:
      - name: order_id
        description: >
          [PK] Unique identifier for each order, sourced from stg_orders.
          Used as the join key across all order-related fact and bridge tables.
          Tests: unique, not_null.

      - name: customer_id
        description: >
          [FK → dim_customers] References the customer who placed this order.
          Enables joining to customer lifetime value, segment, and contact info.
          Not nullable — all orders in the source system require a valid customer.

      - name: first_name
        description: >
          [PII] Customer's first name, denormalized from dim_customers for
          reporting convenience. Masked in non-production environments.
          Do not expose in BI tools without row-level security.

      - name: last_name
        description: >
          [PII] Customer's last name, denormalized from dim_customers.
          Masked in non-production environments.

      - name: email
        description: >
          [PII] Customer's primary email address, denormalized from dim_customers.
          Used in marketing reports. Subject to GDPR/CCPA retention policies.
          Masked in non-production environments.

      - name: customer_segment
        description: >
          Customer value tier at the time of this order, derived in dim_customers.
          Values: 'VIP' (lifetime_value ≥ $1,000), 'Loyal' (≥ $500),
          'Regular' (≥ $100), 'New' (< $100). Used to segment revenue reports
          and power personalization logic downstream.

      - name: amount
        description: >
          Total order amount in USD at the time of placement, inclusive of all
          discounts and payment methods but exclusive of post-purchase adjustments.
          This is the gross amount — use net_revenue for recognized revenue.

      - name: bank_transfer_amount
        description: >
          The portion of the order amount paid via bank transfer in USD.
          Sum of all payment method amounts equals the total order amount.

      - name: coupon_amount
        description: >
          The portion of the order amount covered by coupon/promo code redemptions in USD.
          High coupon_amount relative to amount indicates promotional activity.
          Used in marketing attribution reporting.

      - name: credit_card_amount
        description: >
          The portion of the order amount charged to a credit card in USD.
          Primary payment method for most customers. Used in payment mix analysis.

      - name: gift_card_amount
        description: >
          The portion of the order amount redeemed from a gift card balance in USD.
          Non-zero values indicate loyalty/gift card program usage.

      - name: status
        description: >
          Lifecycle status of the order at the time of last update.
          Values: 'placed' (received, not yet processed), 'shipped' (in transit),
          'completed' (delivered and accepted), 'returned' (customer initiated return),
          'cancelled' (cancelled before shipment — terminal state).
          Terminal states: 'completed', 'returned', 'cancelled'.

      - name: ordered_at
        description: >
          UTC timestamp when the customer confirmed the order at checkout.
          Used for cohort analysis, time-series revenue reporting, and SLA tracking.
          Distinct from shipped_at (not available in this model) and delivered_at.

      - name: is_returned
        description: >
          TRUE when the order status is 'returned', indicating the customer
          sent the items back. FALSE for all other statuses. Used to calculate
          return_rate_pct in rpt_monthly_revenue. NULL values should not exist.

      - name: net_revenue
        description: >
          The recognized revenue contribution of this order in USD.
          Equals amount when status is 'completed' or 'shipped'; 0 for all
          other statuses including 'returned' and 'cancelled'. This is the
          primary revenue metric used in executive dashboards and MRR reporting.
          Do not sum amount directly — always use net_revenue for P&L calculations.
```

---

### How to Reproduce

1. Commit a change to `models/marts/fct_orders.sql`
2. GitHub fires a push webhook → n8n workflow triggers
3. The Librarian fetches the SQL + lineage context from the GitHub API
4. Gemini AI applies Impact Prompting to generate the output above
5. A Pull Request is opened with this exact YAML, ready for human review
