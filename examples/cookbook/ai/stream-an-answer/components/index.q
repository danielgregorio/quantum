<q:component name="Ask">
  <q:knowledge name="docs" persist="false" chunkSize="300" chunkOverlap="30">
    <q:source type="directory" path="knowledge" pattern="*.md" />
  </q:knowledge>

  <q:set name="question" value="{query.q}" default="" />

  <q:if condition="question">
    <!-- stream="true": the page does not wait for the model. The sources are
         known at once; the answer is read from /_stream/… as it is written. -->
    <q:llm name="answer" knowledge="docs" top="2" stream="true">
      <q:message role="user">{question}</q:message>
    </q:llm>
  </q:if>

  <ui:window title="Ask the store">
    <ui:form>
      <ui:input bind="q" value="{question}" placeholder="Your question" />
      <ui:button variant="primary">Ask</ui:button>
    </ui:form>
    <q:if condition="question">
      <!-- The framework's own script fills it in; without JavaScript, a link
           opens the answer. -->
      <ui:stream for="answer" />
      <q:loop items="{answer_result.sources}" var="s">
        <ui:text>[{s.n}] {s.name}</ui:text>
      </q:loop>
    </q:if>
  </ui:window>
</q:component>
