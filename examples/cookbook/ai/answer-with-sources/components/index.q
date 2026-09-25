<q:component name="Ask">
  <!-- The documents in knowledge/, split into chunks and embedded when the
       page runs. persist="false" keeps the index in memory; without it, it is
       stored in ./.quantum/knowledge and reused until a document changes. -->
  <q:knowledge name="docs" persist="false" chunkSize="300" chunkOverlap="30">
    <q:source type="directory" path="knowledge" pattern="*.md" />
  </q:knowledge>

  <q:set name="question" value="{query.q}" default="" />

  <q:if condition="question">
    <!-- The question retrieves the closest chunks; they reach the model
         numbered, with the instruction to answer only from them and cite
         them like [1]. -->
    <q:llm name="answer" knowledge="docs" top="2">
      <q:message role="user">{question}</q:message>
    </q:llm>
  </q:if>

  <ui:window title="Ask the store">
    <ui:form>
      <ui:input bind="q" value="{question}" placeholder="Your question" />
      <ui:button variant="primary">Ask</ui:button>
    </ui:form>
    <q:if condition="question">
      <ui:text>{answer}</ui:text>
      <q:if condition="answer_result.grounded">
        <ui:text>Sources:</ui:text>
        <q:loop items="{answer_result.sources}" var="s">
          <ui:text>[{s.n}] {s.name}</ui:text>
        </q:loop>
        <q:else>
          <ui:alert variant="warning">This answer cites none of the documents.</ui:alert>
        </q:else>
      </q:if>
    </q:if>
  </ui:window>
</q:component>
