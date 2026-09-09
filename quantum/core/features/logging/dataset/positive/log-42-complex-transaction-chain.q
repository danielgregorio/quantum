<!-- Positive: Complex transaction chain logging -->
<!-- Category: Complex Scenarios -->
<q:component name="LogComplexTransactionChain" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:set var="transactionId" value="TXN-999" />

  <q:log level="info" message="Transaction {transactionId} started" />

  <q:invoke name="validatePayment" url="https://api.example.com/validate" method="POST" />
  <q:log level="debug"
         message="Payment validation: {validatePayment_result.success}"
         context="{validatePayment_result}" />

  <q:invoke name="processPayment"
            url="https://api.example.com/process"
            method="POST"
            when="{validatePayment_result.success}" />
  <q:log level="info"
         message="Payment processed for {transactionId}"
         when="{processPayment_result.success}" />

  <q:log level="error"
         message="Transaction {transactionId} failed at payment processing"
         when="{!processPayment_result.success}"
         context="{processPayment_result.error}" />

  <q:return value="{processPayment_result.success}" />
</q:component>
