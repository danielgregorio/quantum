<q:component name="TestEmailHtml">
  <!-- Test: HTML email with formatting -->

  <q:set name="customerName" value="Jane Smith" />
  <q:set name="orderNumber" value="12345" />
  <q:set name="totalAmount" value="99.99" />

  <q:mail to="customer@example.com"
          from="orders@quantum.dev"
          subject="Order Confirmation #{orderNumber}">
    <h1>Order Confirmation</h1>
    <p>Dear {customerName},</p>
    <p>Your order <strong>#{orderNumber}</strong> has been confirmed.</p>
    <p>Total: <strong>${totalAmount}</strong></p>
    <hr />
    <p style="color: #666;">Thank you for your purchase!</p>
  </q:mail>

  <!-- Expected: HTML email formatted correctly -->
  HTML email sent for order #{orderNumber}
</q:component>
