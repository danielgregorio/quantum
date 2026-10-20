<q:component name="Ajustes">
  <!-- The machine's settings, read: five tabs, one a service of leitura.py.
       On the Hive's screen (hive ajustes) the page is a window of 49 columns;
       every tab fits its rows. A change goes through the Hive, not through
       this page (os/CLAUDE.md, "Apps"). -->
  <!-- a change is asked of the Hive (hive request), never made here -->
  <q:action name="pedir-nome" method="POST">
    <q:param name="nome" required="true" />
    <q:invoke name="pedido" service="ajustes.pedir">
      <q:param name="acao" value="set-hostname" />
      <q:param name="valor" value="{nome}" />
    </q:invoke>
    <q:redirect url="/" flash="{pedido.mensagem}" />
  </q:action>
  <q:action name="pedir-teclado" method="POST">
    <q:param name="layout" required="true" />
    <q:invoke name="pedido" service="ajustes.pedir">
      <q:param name="acao" value="set-keyboard" />
      <q:param name="valor" value="{layout}" />
    </q:invoke>
    <q:redirect url="/" flash="{pedido.mensagem}" />
  </q:action>
  <q:action name="pedir-rede" method="POST">
    <q:param name="interface" required="true" />
    <q:param name="origem" required="true" />
    <q:param name="endereco" />
    <q:param name="gateway" />
    <q:param name="dns" />
    <q:invoke name="pedido" service="ajustes.pedir">
      <q:param name="acao" value="set-network" />
      <q:param name="valor" value="{interface}" />
      <q:param name="origem" value="{origem}" />
      <q:param name="endereco" value="{endereco}" />
      <q:param name="gateway" value="{gateway}" />
      <q:param name="dns" value="{dns}" />
    </q:invoke>
    <q:redirect url="/" flash="{pedido.mensagem}" />
  </q:action>
  <q:action name="pedir-nivel" method="POST">
    <q:param name="nivel" required="true" />
    <q:invoke name="pedido" service="ajustes.pedir">
      <q:param name="acao" value="set-screen-level" />
      <q:param name="valor" value="{nivel}" />
    </q:invoke>
    <q:redirect url="/" flash="{pedido.mensagem}" />
  </q:action>

  <q:invoke name="maquina" service="ajustes.maquina" />
  <q:invoke name="rede" service="ajustes.rede" />
  <q:invoke name="teclado" service="ajustes.teclado" />
  <q:invoke name="tela" service="ajustes.tela" />
  <q:invoke name="hive" service="ajustes.hive" />

  <ui:window title="Ajustes">
    <ui:tabpanel>
      <ui:tab title="Máquina">
        <ui:list source="{maquina.linhas}" as="l">
          <ui:item><ui:text>{l.campo}: {l.valor}</ui:text></ui:item>
        </ui:list>
        <ui:form on-submit="pedir-nome">
          <ui:formitem label="Novo nome">
            <ui:input bind="nome" value="{maquina.nome}" />
          </ui:formitem>
          <ui:button variant="primary">Pedir à Hive</ui:button>
        </ui:form>
      </ui:tab>
      <ui:tab title="Rede">
        <ui:table source="{rede.interfaces}" as="i">
          <ui:column key="nome" label="Interface" />
          <ui:column key="estado" label="Estado" />
          <ui:column key="endereco" label="Endereço" />
          <ui:column key="origem" label="Origem" />
        </ui:table>
        <ui:text>gateway: {rede.gateway}</ui:text>
        <ui:text>DNS: {rede.dns}</ui:text>
        <!-- the address asked of the Hive: by DHCP (the rest is ignored) or fixed; dangerous, so the
             screen asks for Enter twice; a wrong address comes back by itself (network-apply) -->
        <ui:form on-submit="pedir-rede">
          <ui:formitem label="Interface">
            <ui:select bind="interface" options="{rede.opcoes}" value="{rede.escolha}" />
          </ui:formitem>
          <ui:formitem label="Origem">
            <ui:select bind="origem" options="dhcp,fixo" value="{rede.origem}" />
          </ui:formitem>
          <ui:formitem label="Endereço/prefixo (fixo)">
            <ui:input bind="endereco" value="{rede.endereco}" placeholder="10.0.2.20/24" />
          </ui:formitem>
          <ui:formitem label="Gateway">
            <ui:input bind="gateway" value="{rede.via}" placeholder="10.0.2.2" />
          </ui:formitem>
          <ui:formitem label="DNS (vírgulas)">
            <ui:input bind="dns" value="{rede.servidores}" placeholder="10.0.2.3" />
          </ui:formitem>
          <ui:button variant="primary">Pedir à Hive</ui:button>
        </ui:form>
      </ui:tab>
      <ui:tab title="Teclado">
        <ui:list source="{teclado.linhas}" as="l">
          <ui:item><ui:text>{l.campo}: {l.valor}</ui:text></ui:item>
        </ui:list>
        <ui:form on-submit="pedir-teclado">
          <ui:formitem label="Layout">
            <ui:select bind="layout" options="us,br" value="{teclado.escolha}" />
          </ui:formitem>
          <ui:button variant="primary">Pedir à Hive</ui:button>
        </ui:form>
      </ui:tab>
      <ui:tab title="Tela">
        <ui:list source="{tela.linhas}" as="l">
          <ui:item><ui:text>{l.campo}: {l.valor}</ui:text></ui:item>
        </ui:list>
        <ui:form on-submit="pedir-nivel">
          <ui:formitem label="Nível">
            <ui:select bind="nivel" options="auto,plain,effects,fine" value="{tela.escolha}" />
          </ui:formitem>
          <ui:button variant="primary">Pedir à Hive</ui:button>
        </ui:form>
      </ui:tab>
      <ui:tab title="Hive">
        <ui:table source="{hive.daemons}" as="d">
          <ui:column key="nome" label="Daemon" />
          <ui:column key="estado" label="Estado" />
        </ui:table>
        <ui:list source="{hive.linhas}" as="l">
          <ui:item><ui:text>{l.campo}: {l.valor}</ui:text></ui:item>
        </ui:list>
      </ui:tab>
    </ui:tabpanel>
    <q:if condition="flash">
      <ui:alert variant="info">{flash}</ui:alert>
    </q:if>
    <ui:footer>Ler é da página; mudar passa pela Hive. Esc fecha.</ui:footer>
  </ui:window>
</q:component>
