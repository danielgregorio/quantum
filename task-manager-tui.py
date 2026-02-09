"""Quantum UI App - Generated Textual Application"""

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, Grid, ScrollableContainer
from textual.widgets import (
    Header, Footer, Static, Button, Input, DataTable,
    Checkbox, Switch, ProgressBar, Tree, RichLog, Rule,
    LoadingIndicator, Markdown, TabbedContent, TabPane,
    Collapsible, OptionList, Select, Label,
)



class QuantumUIApp(App):
    """Quantum UI Application"""

    TITLE = "TaskManager"
    CSS = """/* Quantum UI Textual CSS */\n\n/* Base styles */\n.q-panel { border: solid $primary; padding: 1 2; }\n.q-panel-title { text-style: bold; color: $text; }\n\n/* Badge styles */\n.q-badge { padding: 0 1; }\n.q-badge-primary { background: $primary; color: $text; }\n.q-badge-secondary { background: $secondary; color: $text; }\n.q-badge-success { background: $success; color: $text; }\n.q-badge-danger { background: $error; color: $text; }\n.q-badge-warning { background: $warning; color: $text; }\n\n/* Image placeholder */\n.q-image-placeholder { color: $text-muted; text-style: italic; }\n\n/* Link style */\n.q-link { color: $primary; text-style: underline; }\n\n/* Dynamic layout styles */\n#hbox_2 { padding: 2; }\n#vbox_3 { width: 35; }\n#text_8 { text-style: bold; }\n#text_11 { text-style: bold; }\n#text_14 { text-style: bold; }\n#vbox_29 { width: 1fr; }\n#hbox_34 { align-horizontal: right; }\n#vbox_35 { width: 1fr; }\n#vbox_38 { width: 25; }\n#hbox_44 { padding: 1; background: $surface; align-horizontal: center; }\n#hbox_49 { padding: 1; background: $surface; align-horizontal: center; }\n#hbox_54 { padding: 1; background: $surface; align-horizontal: center; }\n#hbox_59 { padding: 1; background: $surface; align-horizontal: center; }\n#vbox_65 { padding: 4; align-horizontal: center; }\n#text_69 { text-style: bold; }\n#text_70 { text-style: bold; }\n#text_71 { text-style: bold; }\n#text_72 { text-style: bold; }\n#text_73 { text-style: bold; }\n#text_74 { text-style: bold; }\n#text_75 { text-style: bold; }\n#panel_78 { width: 50%; }\n#panel_95 { width: 50%; }\n#hbox_97 { align-horizontal: center; }\n#hbox_98 { align-horizontal: center; }\n#text_100 { text-style: bold; }\n#hbox_101 { align-horizontal: center; }\n#hbox_102 { align-horizontal: center; }\n#text_104 { text-style: bold; }\n#hbox_105 { align-horizontal: center; }\n#hbox_106 { align-horizontal: center; }\n#text_108 { text-style: bold; }\n#hbox_109 { align-horizontal: center; }\n#hbox_110 { align-horizontal: center; }\n#text_112 { text-style: bold; }\n#panel_114 { width: 50%; }\n#panel_128 { width: 50%; }\n#text_138 { text-style: bold; }"""


    def compose(self) -> ComposeResult:
        with Vertical(id="window_1"):
            yield Header()
            with Horizontal(id="hbox_2"):
                with Vertical(id="vbox_3"):
                    with Vertical(id="panel_4", classes="q-panel"):
                        yield Static("Estatisticas", classes="q-panel-title")
                        with Vertical(id="vbox_5"):
                            with Horizontal(id="hbox_6"):
                                yield Static("Total de Tarefas:", id="text_7")
                                yield Static("{taskCount}", id="text_8")
                            with Horizontal(id="hbox_9"):
                                yield Static("Concluidas:", id="text_10")
                                yield Static("{completedCount}", id="text_11")
                            with Horizontal(id="hbox_12"):
                                yield Static("Pendentes:", id="text_13")
                                yield Static("{taskCount}", id="text_14")
                            yield Rule()
                            with Horizontal(id="hbox_15"):
                                yield Static("Filtro Atual:", id="text_16")
                                yield Static("{currentFilter}", id="badge_17", classes="q-badge q-badge-secondary")
                    with Vertical(id="panel_18", classes="q-panel"):
                        yield Static("Acoes Rapidas", classes="q-panel-title")
                        with Vertical(id="vbox_19"):
                            yield Button("+ Nova Tarefa", variant="primary", id="btn_20")
                            yield Button("Marcar Concluida", variant="success", id="btn_21")
                            yield Button("Limpar Concluidas", variant="default", id="btn_22")
                            yield Button("Resetar Tudo", variant="error", id="btn_23")
                    with Vertical(id="panel_24", classes="q-panel"):
                        yield Static("Filtros", classes="q-panel-title")
                        with Vertical(id="vbox_25"):
                            yield Button("Todas", id="btn_26")
                            yield Button("Ativas", id="btn_27")
                            yield Button("Concluidas", id="btn_28")
                with Vertical(id="vbox_29"):
                    with TabbedContent(id="tabs_30"):
                        with TabPane("Tarefas"):
                            with Vertical(id="vbox_31"):
                                with Vertical(id="panel_32", classes="q-panel"):
                                    yield Static("Adicionar Nova Tarefa", classes="q-panel-title")
                                    with Vertical(id="form_33"):
                                        with Horizontal(id="hbox_34"):
                                            with Vertical(id="vbox_35"):
                                                yield Static("Titulo da Tarefa", id="text_36")
                                                yield Input(placeholder="Digite o titulo...", id="input_37")
                                            with Vertical(id="vbox_38"):
                                                yield Static("Prioridade", id="text_39")
                                                yield Select([("Baixa", "Baixa"), ("Media", "Media"), ("Alta", "Alta"), ("Urgente", "Urgente")])
                                            yield Button("Adicionar", variant="primary", id="btn_41")
                                with Vertical(id="panel_42", classes="q-panel"):
                                    yield Static("Lista de Tarefas", classes="q-panel-title")
                                    with Vertical(id="vbox_43"):
                                        with Horizontal(id="hbox_44"):
                                            yield Checkbox("Implementar autenticacao", id="cb_45")
                                            with Horizontal(id="hbox_46"):
                                                yield Static("Urgente", id="badge_47", classes="q-badge q-badge-danger")
                                                yield Button("Concluir", variant="success", id="btn_48")
                                        with Horizontal(id="hbox_49"):
                                            yield Checkbox("Criar documentacao da API", id="cb_50")
                                            with Horizontal(id="hbox_51"):
                                                yield Static("Alta", id="badge_52", classes="q-badge q-badge-warning")
                                                yield Button("Concluir", variant="success", id="btn_53")
                                        with Horizontal(id="hbox_54"):
                                            yield Checkbox("Revisar pull requests", id="cb_55")
                                            with Horizontal(id="hbox_56"):
                                                yield Static("Media", id="badge_57", classes="q-badge q-badge-primary")
                                                yield Button("Concluir", variant="success", id="btn_58")
                                        with Horizontal(id="hbox_59"):
                                            yield Checkbox("Atualizar dependencias", id="cb_60")
                                            with Horizontal(id="hbox_61"):
                                                yield Static("Baixa", id="badge_62", classes="q-badge q-badge-secondary")
                                                yield Button("Concluir", variant="success", id="btn_63")
                        with TabPane("Calendario"):
                            with Vertical(id="panel_64", classes="q-panel"):
                                yield Static("Visao do Calendario", classes="q-panel-title")
                                with Vertical(id="vbox_65"):
                                    yield Static("Calendario de Tarefas", id="text_66")
                                    yield Static("Visualize suas tarefas por data", id="text_67")
                                    with Grid(id="grid_68"):
                                        yield Static("Dom", id="text_69")
                                        yield Static("Seg", id="text_70")
                                        yield Static("Ter", id="text_71")
                                        yield Static("Qua", id="text_72")
                                        yield Static("Qui", id="text_73")
                                        yield Static("Sex", id="text_74")
                                        yield Static("Sab", id="text_75")
                                    yield LoadingIndicator(id="loading_76")
                        with TabPane("Relatorios"):
                            with Horizontal(id="hbox_77"):
                                with Vertical(id="panel_78", classes="q-panel"):
                                    yield Static("Produtividade Semanal", classes="q-panel-title")
                                    with Vertical(id="vbox_79"):
                                        with Horizontal(id="hbox_80"):
                                            yield Static("Segunda", id="text_81")
                                            yield ProgressBar(id="prog_82")
                                        with Horizontal(id="hbox_83"):
                                            yield Static("Terca", id="text_84")
                                            yield ProgressBar(id="prog_85")
                                        with Horizontal(id="hbox_86"):
                                            yield Static("Quarta", id="text_87")
                                            yield ProgressBar(id="prog_88")
                                        with Horizontal(id="hbox_89"):
                                            yield Static("Quinta", id="text_90")
                                            yield ProgressBar(id="prog_91")
                                        with Horizontal(id="hbox_92"):
                                            yield Static("Sexta", id="text_93")
                                            yield ProgressBar(id="prog_94")
                                with Vertical(id="panel_95", classes="q-panel"):
                                    yield Static("Resumo por Prioridade", classes="q-panel-title")
                                    with Vertical(id="vbox_96"):
                                        with Horizontal(id="hbox_97"):
                                            with Horizontal(id="hbox_98"):
                                                yield Static("Urgente", id="badge_99", classes="q-badge q-badge-danger")
                                            yield Static("3 tarefas", id="text_100")
                                        with Horizontal(id="hbox_101"):
                                            with Horizontal(id="hbox_102"):
                                                yield Static("Alta", id="badge_103", classes="q-badge q-badge-warning")
                                            yield Static("7 tarefas", id="text_104")
                                        with Horizontal(id="hbox_105"):
                                            with Horizontal(id="hbox_106"):
                                                yield Static("Media", id="badge_107", classes="q-badge q-badge-primary")
                                            yield Static("12 tarefas", id="text_108")
                                        with Horizontal(id="hbox_109"):
                                            with Horizontal(id="hbox_110"):
                                                yield Static("Baixa", id="badge_111", classes="q-badge q-badge-secondary")
                                            yield Static("5 tarefas", id="text_112")
                        with TabPane("Configuracoes"):
                            with Horizontal(id="hbox_113"):
                                with Vertical(id="panel_114", classes="q-panel"):
                                    yield Static("Perfil do Usuario", classes="q-panel-title")
                                    with Vertical(id="form_115"):
                                        with Vertical(id="vbox_116"):
                                            with Horizontal(id="formitem_117"):
                                                yield Label("Nome")
                                                yield Input(placeholder="Seu nome", id="input_118")
                                            with Horizontal(id="formitem_119"):
                                                yield Label("Email")
                                                yield Input(placeholder="seu@email.com", id="input_120")
                                            with Horizontal(id="formitem_121"):
                                                yield Label("Fuso Horario")
                                                yield Select([("America/Sao_Paulo", "America/Sao_Paulo"), ("America/New_York", "America/New_York"), ("Europe/London", "Europe/London"), ("Asia/Tokyo", "Asia/Tokyo")])
                                            with Horizontal(id="formitem_123"):
                                                yield Label("Idioma")
                                                yield Select([("Portugues", "Portugues"), ("English", "English"), ("Espanol", "Espanol")])
                                            with Horizontal(id="hbox_125"):
                                                yield Button("Cancelar", variant="default", id="btn_126")
                                                yield Button("Salvar", variant="primary", id="btn_127")
                                with Vertical(id="panel_128", classes="q-panel"):
                                    yield Static("Preferencias", classes="q-panel-title")
                                    with Vertical(id="vbox_129"):
                                        with Horizontal(id="formitem_130"):
                                            yield Label("Modo Escuro")
                                            yield Switch(id="sw_131")
                                        with Horizontal(id="formitem_132"):
                                            yield Label("Notificacoes")
                                            yield Switch(id="sw_133")
                                        with Horizontal(id="formitem_134"):
                                            yield Label("Som")
                                            yield Switch(id="sw_135")
                                        with Horizontal(id="formitem_136"):
                                            yield Label("Auto-save")
                                            yield Switch(id="sw_137")
                                        yield Rule()
                                        yield Static("Dados", id="text_138")
                                        with Horizontal(id="hbox_139"):
                                            yield Button("Exportar", variant="default", id="btn_140")
                                            yield Button("Importar", variant="default", id="btn_141")
            yield Footer()
        # q:set taskCount = 0
        # q:set completedCount = 0
        # q:set currentFilter = all
        # q:set darkMode = false
        # q:set username = Usuario
        # q:set notifications = 3

    pass

if __name__ == "__main__":
    app = QuantumUIApp()
    app.run()
