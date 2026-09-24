<!-- Positive: Real-world payment processing log -->
<!-- Category: Real-World Patterns -->
<q:component name="LogRealWorldPayment" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:set var="payment" value='{"orderId": "ORD-123", "amount": 99.99, "currency": "USD", "status": "completed"}' operation="json" />

  <q:log level="info"
         message="Payment processed: {payment.orderId} - ${payment.amount}"
         context="{payment}" />

  <q:return value="Payment logged" />
</q:component>
