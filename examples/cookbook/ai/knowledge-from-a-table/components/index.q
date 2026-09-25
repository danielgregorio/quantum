<q:component name="Help">
  <!-- A query source: each row becomes text to index. Every user can
       retrieve any row, so index only what everyone may read. -->
  <q:knowledge name="faq" persist="false">
    <q:source type="query" datasource="db">
      SELECT question || ' ' || answer AS content FROM faq
    </q:source>
  </q:knowledge>

  <q:set name="question" value="{query.q}" default="" />
  <q:if condition="question">
    <q:llm name="answer" knowledge="faq" top="1" minRelevance="0.8">
      <q:message role="user">{question}</q:message>
    </q:llm>
  </q:if>

  <ui:window title="Help">
    <ui:form>
      <ui:input bind="q" value="{question}" placeholder="Ask about your account" />
      <ui:button variant="primary">Ask</ui:button>
    </ui:form>
    <q:if condition="question">
      <q:if condition="answer_result.found">
        <ui:text>{answer}</ui:text>
        <ui:text>From the FAQ: {answer_result.sources[0].text}</ui:text>
        <q:else>
          <ui:alert variant="info">The FAQ does not cover that yet.</ui:alert>
        </q:else>
      </q:if>
    </q:if>
  </ui:window>
</q:component>
