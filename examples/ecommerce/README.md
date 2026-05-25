# examples/ecommerce — E-commerce demo app

A small shop catalog with product hierarchy, customers, orders, and
order items. Useful for exercising self-referential foreign keys,
status workflows, and conditional permissions.

## What's here

- `models.py` — `Category` (self-referential parent), `Product`,
  `Customer`, `Order`, `OrderItem`.
- `admin.py` — `OrderAdmin.has_delete_permission` returns `False`
  once an order has been paid/shipped/delivered, so the React UI
  hides the delete button accordingly.
- `tests/test_admin.py` — smoke test.

## Why this app demonstrates the design

- **Self-referential FK**: `Category.parent` points to `Category`.
  The API surfaces this like any other FK; the React UI renders it as
  an FK input. (Tree navigation is a v1.x enhancement, not required.)
- **Conditional `has_delete_permission`**: server-side enforcement;
  the React UI receives `permissions.delete = false` for orders in a
  terminal state and hides the button. No React code change needed
  for new business rules.
- **`PROTECT` on `OrderItem.product`**: deleting a product that has
  ever been ordered is blocked, surfaced as `409 conflict`.
- **`PROTECT` on `Order.customer`**: deleting a customer with orders
  is blocked. Useful test of the conflict-error path.

## Running

When `examples/project/` is wired up — same procedure as the other
examples.
