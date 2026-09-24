<q:component name="DemoPage">
  <q:import component="Layout" />
  <q:import component="Card" />
  <q:import component="Button" />

  <q:set name="pageTitle" value="Component Composition Demo" />
  <q:set name="userName" value="Daniel" />

  <Layout title="{pageTitle}" description="Phase 2: Reusable Components">
    <h2>Welcome, {userName}!</h2>
    <p>This page demonstrates Quantum's component composition system.</p>

    <Card title="Feature 1: Props Passing" subtitle="Pass data from parent to child">
      <p>Components receive props and render them dynamically.</p>
      <Button label="Learn More" color="blue" size="medium" />
    </Card>

    <Card title="Feature 2: Slot Projection" subtitle="Inject content into child components">
      <p>This content is injected into the Card's slot!</p>
      <ul>
        <li>Flexible content composition</li>
        <li>Reusable components</li>
        <li>Clean separation of concerns</li>
      </ul>
      <Button label="Get Started" color="green" size="large" />
    </Card>

    <Card title="Feature 3: Multiple Components" subtitle="Compose complex UIs easily">
      <div style="display: flex; gap: 10px; flex-wrap: wrap;">
        <Button label="Save" color="green" size="small" />
        <Button label="Cancel" color="red" size="small" />
        <Button label="Reset" color="blue" size="small" />
      </div>
    </Card>
  </Layout>
</q:component>
