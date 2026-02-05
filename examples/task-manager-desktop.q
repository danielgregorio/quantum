<q:application id="TaskManager" type="ui">
    <!-- State Variables -->
    <q:set name="taskCount" value="0" type="number" />
    <q:set name="completedCount" value="0" type="number" />
    <q:set name="currentFilter" value="all" type="string" />
    <q:set name="darkMode" value="false" type="boolean" />
    <q:set name="username" value="Usuario" type="string" />
    <q:set name="notifications" value="3" type="number" />

    <!-- Functions -->
    <q:function name="addTask">
        <q:set name="taskCount" value="{taskCount + 1}" />
    </q:function>

    <q:function name="completeTask">
        <q:set name="completedCount" value="{completedCount + 1}" />
    </q:function>

    <q:function name="clearCompleted">
        <q:set name="completedCount" value="0" />
    </q:function>

    <q:function name="resetAll">
        <q:set name="taskCount" value="0" />
        <q:set name="completedCount" value="0" />
    </q:function>

    <q:function name="filterAll">
        <q:set name="currentFilter" value="all" />
    </q:function>

    <q:function name="filterActive">
        <q:set name="currentFilter" value="active" />
    </q:function>

    <q:function name="filterCompleted">
        <q:set name="currentFilter" value="completed" />
    </q:function>

    <q:function name="toggleDarkMode">
        <q:set name="darkMode" value="{darkMode}" />
    </q:function>

    <q:function name="dismissNotifications">
        <q:set name="notifications" value="0" />
    </q:function>

    <q:function name="saveSettings">
        <!-- Settings saved via form data -->
    </q:function>

    <q:function name="exportData">
        <!-- Export functionality -->
    </q:function>

    <q:function name="importData">
        <!-- Import functionality -->
    </q:function>

    <ui:window title="Task Manager Pro">
        <!-- Header with user info -->
        <ui:header>
            <ui:hbox justify="between" align="center" padding="8">
                <ui:hbox gap="12" align="center">
                    <ui:text size="xl" weight="bold">Task Manager Pro</ui:text>
                    <ui:badge variant="primary">v2.0</ui:badge>
                </ui:hbox>
                <ui:hbox gap="16" align="center">
                    <ui:button variant="secondary" on-click="dismissNotifications">
                        Notificacoes ({notifications})
                    </ui:button>
                    <ui:text>Ola, {username}</ui:text>
                </ui:hbox>
            </ui:hbox>
        </ui:header>

        <!-- Main Content -->
        <ui:hbox gap="16" padding="16">
            <!-- Left Sidebar - Stats -->
            <ui:vbox width="280" gap="16">
                <ui:panel title="Estatisticas">
                    <ui:vbox gap="12">
                        <ui:hbox justify="between">
                            <ui:text>Total de Tarefas:</ui:text>
                            <ui:text weight="bold">{taskCount}</ui:text>
                        </ui:hbox>
                        <ui:hbox justify="between">
                            <ui:text>Concluidas:</ui:text>
                            <ui:text weight="bold">{completedCount}</ui:text>
                        </ui:hbox>
                        <ui:hbox justify="between">
                            <ui:text>Pendentes:</ui:text>
                            <ui:text weight="bold">{taskCount}</ui:text>
                        </ui:hbox>
                        <ui:rule />
                        <ui:hbox justify="between">
                            <ui:text>Filtro Atual:</ui:text>
                            <ui:badge variant="secondary">{currentFilter}</ui:badge>
                        </ui:hbox>
                    </ui:vbox>
                </ui:panel>

                <ui:panel title="Acoes Rapidas">
                    <ui:vbox gap="8">
                        <ui:button variant="primary" on-click="addTask">
                            + Nova Tarefa
                        </ui:button>
                        <ui:button variant="success" on-click="completeTask">
                            Marcar Concluida
                        </ui:button>
                        <ui:button variant="secondary" on-click="clearCompleted">
                            Limpar Concluidas
                        </ui:button>
                        <ui:button variant="danger" on-click="resetAll">
                            Resetar Tudo
                        </ui:button>
                    </ui:vbox>
                </ui:panel>

                <ui:panel title="Filtros">
                    <ui:vbox gap="8">
                        <ui:button on-click="filterAll">Todas</ui:button>
                        <ui:button on-click="filterActive">Ativas</ui:button>
                        <ui:button on-click="filterCompleted">Concluidas</ui:button>
                    </ui:vbox>
                </ui:panel>
            </ui:vbox>

            <!-- Main Area -->
            <ui:vbox width="fill" gap="16">
                <ui:tabpanel>
                    <!-- Tasks Tab -->
                    <ui:tab title="Tarefas">
                        <ui:vbox gap="16">
                            <!-- Add Task Form -->
                            <ui:panel title="Adicionar Nova Tarefa">
                                <ui:form on-submit="addTask">
                                    <ui:hbox gap="12" align="end">
                                        <ui:vbox width="fill" gap="4">
                                            <ui:text size="sm">Titulo da Tarefa</ui:text>
                                            <ui:input bind="taskTitle" placeholder="Digite o titulo..." />
                                        </ui:vbox>
                                        <ui:vbox width="200" gap="4">
                                            <ui:text size="sm">Prioridade</ui:text>
                                            <ui:select bind="priority" options="Baixa,Media,Alta,Urgente" />
                                        </ui:vbox>
                                        <ui:button variant="primary">Adicionar</ui:button>
                                    </ui:hbox>
                                </ui:form>
                            </ui:panel>

                            <!-- Task List -->
                            <ui:panel title="Lista de Tarefas">
                                <ui:vbox gap="8">
                                    <ui:hbox justify="between" align="center" padding="8" background="light">
                                        <ui:checkbox label="Implementar autenticacao" />
                                        <ui:hbox gap="8">
                                            <ui:badge variant="danger">Urgente</ui:badge>
                                            <ui:button variant="success" on-click="completeTask">Concluir</ui:button>
                                        </ui:hbox>
                                    </ui:hbox>
                                    <ui:hbox justify="between" align="center" padding="8" background="light">
                                        <ui:checkbox label="Criar documentacao da API" />
                                        <ui:hbox gap="8">
                                            <ui:badge variant="warning">Alta</ui:badge>
                                            <ui:button variant="success" on-click="completeTask">Concluir</ui:button>
                                        </ui:hbox>
                                    </ui:hbox>
                                    <ui:hbox justify="between" align="center" padding="8" background="light">
                                        <ui:checkbox label="Revisar pull requests" />
                                        <ui:hbox gap="8">
                                            <ui:badge variant="primary">Media</ui:badge>
                                            <ui:button variant="success" on-click="completeTask">Concluir</ui:button>
                                        </ui:hbox>
                                    </ui:hbox>
                                    <ui:hbox justify="between" align="center" padding="8" background="light">
                                        <ui:checkbox label="Atualizar dependencias" />
                                        <ui:hbox gap="8">
                                            <ui:badge variant="secondary">Baixa</ui:badge>
                                            <ui:button variant="success" on-click="completeTask">Concluir</ui:button>
                                        </ui:hbox>
                                    </ui:hbox>
                                </ui:vbox>
                            </ui:panel>
                        </ui:vbox>
                    </ui:tab>

                    <!-- Calendar Tab -->
                    <ui:tab title="Calendario">
                        <ui:panel title="Visao do Calendario">
                            <ui:vbox gap="16" align="center" padding="32">
                                <ui:text size="xl">Calendario de Tarefas</ui:text>
                                <ui:text>Visualize suas tarefas por data</ui:text>
                                <ui:grid columns="7" gap="4">
                                    <ui:text weight="bold">Dom</ui:text>
                                    <ui:text weight="bold">Seg</ui:text>
                                    <ui:text weight="bold">Ter</ui:text>
                                    <ui:text weight="bold">Qua</ui:text>
                                    <ui:text weight="bold">Qui</ui:text>
                                    <ui:text weight="bold">Sex</ui:text>
                                    <ui:text weight="bold">Sab</ui:text>
                                </ui:grid>
                                <ui:loading text="Carregando calendario..." />
                            </ui:vbox>
                        </ui:panel>
                    </ui:tab>

                    <!-- Reports Tab -->
                    <ui:tab title="Relatorios">
                        <ui:hbox gap="16">
                            <ui:panel title="Produtividade Semanal" width="50%">
                                <ui:vbox gap="12">
                                    <ui:hbox justify="between">
                                        <ui:text>Segunda</ui:text>
                                        <ui:progress value="80" max="100" />
                                    </ui:hbox>
                                    <ui:hbox justify="between">
                                        <ui:text>Terca</ui:text>
                                        <ui:progress value="65" max="100" />
                                    </ui:hbox>
                                    <ui:hbox justify="between">
                                        <ui:text>Quarta</ui:text>
                                        <ui:progress value="90" max="100" />
                                    </ui:hbox>
                                    <ui:hbox justify="between">
                                        <ui:text>Quinta</ui:text>
                                        <ui:progress value="45" max="100" />
                                    </ui:hbox>
                                    <ui:hbox justify="between">
                                        <ui:text>Sexta</ui:text>
                                        <ui:progress value="70" max="100" />
                                    </ui:hbox>
                                </ui:vbox>
                            </ui:panel>
                            <ui:panel title="Resumo por Prioridade" width="50%">
                                <ui:vbox gap="12">
                                    <ui:hbox justify="between" align="center">
                                        <ui:hbox gap="8" align="center">
                                            <ui:badge variant="danger">Urgente</ui:badge>
                                        </ui:hbox>
                                        <ui:text weight="bold">3 tarefas</ui:text>
                                    </ui:hbox>
                                    <ui:hbox justify="between" align="center">
                                        <ui:hbox gap="8" align="center">
                                            <ui:badge variant="warning">Alta</ui:badge>
                                        </ui:hbox>
                                        <ui:text weight="bold">7 tarefas</ui:text>
                                    </ui:hbox>
                                    <ui:hbox justify="between" align="center">
                                        <ui:hbox gap="8" align="center">
                                            <ui:badge variant="primary">Media</ui:badge>
                                        </ui:hbox>
                                        <ui:text weight="bold">12 tarefas</ui:text>
                                    </ui:hbox>
                                    <ui:hbox justify="between" align="center">
                                        <ui:hbox gap="8" align="center">
                                            <ui:badge variant="secondary">Baixa</ui:badge>
                                        </ui:hbox>
                                        <ui:text weight="bold">5 tarefas</ui:text>
                                    </ui:hbox>
                                </ui:vbox>
                            </ui:panel>
                        </ui:hbox>
                    </ui:tab>

                    <!-- Settings Tab -->
                    <ui:tab title="Configuracoes">
                        <ui:hbox gap="16">
                            <ui:panel title="Perfil do Usuario" width="50%">
                                <ui:form on-submit="saveSettings">
                                    <ui:vbox gap="16">
                                        <ui:formitem label="Nome">
                                            <ui:input bind="username" placeholder="Seu nome" />
                                        </ui:formitem>
                                        <ui:formitem label="Email">
                                            <ui:input bind="email" type="email" placeholder="seu@email.com" />
                                        </ui:formitem>
                                        <ui:formitem label="Fuso Horario">
                                            <ui:select bind="timezone" options="America/Sao_Paulo,America/New_York,Europe/London,Asia/Tokyo" />
                                        </ui:formitem>
                                        <ui:formitem label="Idioma">
                                            <ui:select bind="language" options="Portugues,English,Espanol" />
                                        </ui:formitem>
                                        <ui:hbox justify="end" gap="8">
                                            <ui:button variant="secondary">Cancelar</ui:button>
                                            <ui:button variant="primary">Salvar</ui:button>
                                        </ui:hbox>
                                    </ui:vbox>
                                </ui:form>
                            </ui:panel>
                            <ui:panel title="Preferencias" width="50%">
                                <ui:vbox gap="16">
                                    <ui:formitem label="Modo Escuro">
                                        <ui:switch bind="darkMode" label="Ativar tema escuro" />
                                    </ui:formitem>
                                    <ui:formitem label="Notificacoes">
                                        <ui:switch bind="notifications_enabled" label="Receber notificacoes" />
                                    </ui:formitem>
                                    <ui:formitem label="Som">
                                        <ui:switch bind="sound_enabled" label="Sons de notificacao" />
                                    </ui:formitem>
                                    <ui:formitem label="Auto-save">
                                        <ui:switch bind="autosave" label="Salvar automaticamente" />
                                    </ui:formitem>
                                    <ui:rule />
                                    <ui:text size="sm" weight="bold">Dados</ui:text>
                                    <ui:hbox gap="8">
                                        <ui:button variant="secondary" on-click="exportData">Exportar</ui:button>
                                        <ui:button variant="secondary" on-click="importData">Importar</ui:button>
                                    </ui:hbox>
                                </ui:vbox>
                            </ui:panel>
                        </ui:hbox>
                    </ui:tab>
                </ui:tabpanel>
            </ui:vbox>
        </ui:hbox>

        <!-- Footer -->
        <ui:footer>
            <ui:hbox justify="between" align="center">
                <ui:text>Task Manager Pro - Quantum Framework</ui:text>
                <ui:hbox gap="16">
                    <ui:text>Tarefas: {taskCount}</ui:text>
                    <ui:text>Concluidas: {completedCount}</ui:text>
                    <ui:text>Filtro: {currentFilter}</ui:text>
                </ui:hbox>
            </ui:hbox>
        </ui:footer>
    </ui:window>
</q:application>
