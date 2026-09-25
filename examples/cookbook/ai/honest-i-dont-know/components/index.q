<q:component name="Ask">
  <q:knowledge name="docs" persist="false" chunkSize="300" chunkOverlap="30">
    <q:source type="directory" path="knowledge" pattern="*.md" />
  </q:knowledge>

  <q:set name="question" value="{query.q}" default="" />

  <q:if condition="question">
    <!-- minRelevance: chunks less relevant than 0.8 are not retrieved. When
         none remains, the model is not asked at all — it would answer from
         memory — and answer_result.found is false. The right floor depends
         on the embedding model and the chunk size: look at the relevance of
         a few sources before choosing it. -->
    <q:llm name="answer" knowledge="docs" top="2" minRelevance="0.8">
      <q:message role="user">{question}</q:message>
    </q:llm>
  </q:if>

  <ui:window title="Ask the store">
    <ui:form>
      <ui:input bind="q" value="{question}" placeholder="Your question" />
      <ui:button variant="primary">Ask</ui:button>
    </ui:form>
    <q:if condition="question">
      <q:if condition="answer_result.found">
        <ui:text>{answer}</ui:text>
        <q:loop items="{answer_result.sources}" var="s">
          <ui:text>[{s.n}] {s.name} ({round(s.relevance, 2)})</ui:text>
        </q:loop>
        <q:else>
          <ui:alert variant="info">Our documents do not answer that. Write to us at help@example.com.</ui:alert>
        </q:else>
      </q:if>
    </q:if>
  </ui:window>
</q:component>
