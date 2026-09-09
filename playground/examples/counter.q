<!-- Counter App -->
<q:component name="Counter">
  <q:set name="count" type="number" value="0" />
  <q:set name="step" type="number" value="1" />

  <style>
    .counter-app { text-align: center; padding: 40px; font-family: sans-serif; }
    .counter-value { font-size: 72px; font-weight: bold; color: #3b82f6; margin: 20px 0; }
    .counter-label { color: #666; margin-bottom: 20px; }
    .counter-buttons { display: flex; gap: 12px; justify-content: center; }
    .btn { padding: 12px 24px; font-size: 18px; border: none; border-radius: 8px; cursor: pointer; }
    .btn-dec { background: #ef4444; color: white; }
    .btn-inc { background: #22c55e; color: white; }
    .btn-reset { background: #6b7280; color: white; }
  </style>

  <div class="counter-app">
    <h1>Quantum Counter</h1>
    <p class="counter-label">Current count (step: {step})</p>
    <div class="counter-value">{count}</div>
    <div class="counter-buttons">
      <button class="btn btn-dec">- Decrease</button>
      <button class="btn btn-reset">Reset</button>
      <button class="btn btn-inc">+ Increase</button>
    </div>
    <p style="margin-top: 20px; color: #999;">
      Note: Interactivity requires server-side execution.
      This is a static preview.
    </p>
  </div>
</q:component>
