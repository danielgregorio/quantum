<q:component name="Ajustes">
  <!-- The machine's settings, read: five tabs, one a service of leitura.py.
       On the Hive's screen (hive ajustes) the page is a window of 49 columns;
       every tab fits its rows. A change goes through the Hive, not through
       this page (os/CLAUDE.md, "Apps"). -->
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
      </ui:tab>
      <ui:tab title="Teclado">
        <ui:list source="{teclado.linhas}" as="l">
          <ui:item><ui:text>{l.campo}: {l.valor}</ui:text></ui:item>
        </ui:list>
      </ui:tab>
      <ui:tab title="Tela">
        <ui:list source="{tela.linhas}" as="l">
          <ui:item><ui:text>{l.campo}: {l.valor}</ui:text></ui:item>
        </ui:list>
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
    <ui:footer>Ler é da página; mudar passa pela Hive. Esc fecha.</ui:footer>
  </ui:window>
</q:component>
