<q:component name="DocsAssistant">
  <!-- Ask the Quantum guide. The answer comes only from docs/guide, cites its
       sources (IA-6) and arrives as the model writes it (IA-7). A question
       no chunk of the guide is relevant to is not sent to the model (IA-9).
       When the model server or the index fails, the page says so (IA-5). -->

  <q:action name="ask" method="POST">
    <q:param name="question" required="true" minlength="3" maxlength="300" />
    <q:redirect url="/?q={urlencode(question)}" />
  </q:action>

  <q:set name="question" value="{query.q}" default="" />
  <q:set name="question" value="{trim(question)}" />

  <q:knowledge name="guide" chunkSize="1500" chunkOverlap="150" onerror="continue">
    <q:source type="directory" path="../../docs/guide" pattern="*.md" />
  </q:knowledge>

  <q:if condition="question and guide_info.success">
    <q:llm name="answer" model="phi3" knowledge="guide" top="5" minRelevance="0.79" stream="true" onerror="continue" timeout="240" temperature="0" maxTokens="400">
      <q:message role="system">You answer questions about the Quantum framework. Be brief. Copy code only as it appears in the sources; never invent tags or attributes.</q:message>
      <q:message role="user">{question}</q:message>
    </q:llm>
  </q:if>

  <ui:window title="Quantum docs assistant">
    <ui:vbox gap="md" padding="lg">
      <ui:header title="Ask the Quantum guide" />
      <q:if condition="flash">
        <ui:alert variant="danger">{flash}</ui:alert>
      </q:if>
      <q:if condition="not guide_info.success">
        <ui:alert variant="danger" id="guide-error">The guide could not be indexed: {guide_info.error}</ui:alert>
      </q:if>

      <ui:form on-submit="ask">
        <ui:hbox gap="sm" stack-below="sm">
          <ui:input bind="question" value="{question}" placeholder="How do I paginate a query?" grow="true" />
          <ui:button variant="primary">Ask</ui:button>
        </ui:hbox>
      </ui:form>

      <q:if condition="question and guide_info.success">
        <q:if condition="not answer_result.success">
          <ui:alert variant="danger" id="answer-error">The assistant is unavailable: {answer_result.error.message}</ui:alert>
          <q:elseif condition="not answer_result.found">
            <ui:alert variant="warning" id="not-found">The guide says nothing about that.</ui:alert>
          </q:elseif>
          <q:else>
          <ui:panel title="Answer">
            <ui:stream for="answer" id="answer" />
          </ui:panel>
          <ui:panel title="Sources">
            <ui:list source="{answer_result.sources}" as="s">
              <ui:item><ui:text>[{s.n}] {s.name}</ui:text></ui:item>
            </ui:list>
          </ui:panel>
          </q:else>
        </q:if>
      </q:if>
    </ui:vbox>
  </ui:window>
</q:component>
