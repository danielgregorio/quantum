/**
 * Internationalization (i18n) System
 * Multi-language support for Quantum Admin
 */

const TRANSLATIONS = {
    'en': {
        // Navigation
        'nav.dashboard': 'Dashboard',
        'nav.monitoring': 'Monitoring',
        'nav.datasources': 'Datasources',
        'nav.containers': 'Containers',
        'nav.components': 'Components',
        'nav.playground': 'Playground',
        'nav.templates': 'Templates',
        'nav.queryBuilder': 'Query Builder',
        'nav.apiExplorer': 'API Explorer',
        'nav.logs': 'Logs',
        'nav.settings': 'Settings',
        'nav.security': 'Security',

        // Dashboard
        'dashboard.title': 'Dashboard',
        'dashboard.components': 'Active Components',
        'dashboard.datasources': 'Datasources',
        'dashboard.containers': 'Running Containers',
        'dashboard.endpoints': 'API Endpoints',
        'dashboard.recentDatasources': 'Recent Datasources',
        'dashboard.systemHealth': 'System Health',

        // Buttons
        'btn.refresh': 'Refresh',
        'btn.save': 'Save',
        'btn.cancel': 'Cancel',
        'btn.delete': 'Delete',
        'btn.edit': 'Edit',
        'btn.create': 'Create',
        'btn.export': 'Export',
        'btn.import': 'Import',
        'btn.download': 'Download',
        'btn.upload': 'Upload',
        'btn.run': 'Run',
        'btn.copy': 'Copy',
        'btn.share': 'Share',

        // Messages
        'msg.success': 'Operation successful',
        'msg.error': 'An error occurred',
        'msg.loading': 'Loading...',
        'msg.noData': 'No data available',
        'msg.confirmDelete': 'Are you sure you want to delete this?',
        'msg.unsavedChanges': 'You have unsaved changes',

        // Datasources
        'datasources.title': 'Datasources',
        'datasources.new': 'New Datasource',
        'datasources.name': 'Name',
        'datasources.type': 'Type',
        'datasources.status': 'Status',
        'datasources.connection': 'Connection',
        'datasources.host': 'Host',
        'datasources.port': 'Port',

        // Monitoring
        'monitoring.title': 'System Monitoring',
        'monitoring.cpu': 'CPU Usage',
        'monitoring.memory': 'Memory Used',
        'monitoring.disk': 'Disk Usage',
        'monitoring.connections': 'Active Connections',

        // AI Assistant
        'ai.title': 'Quantum AI Assistant',
        'ai.placeholder': 'Ask me anything about Quantum...',
        'ai.send': 'Send',
        'ai.close': 'Close',

        // Command Palette
        'cmd.placeholder': 'Type a command or search...',
        'cmd.navigate': 'Navigate',
        'cmd.actions': 'Actions',
        'cmd.noResults': 'No commands found',

        // Settings
        'settings.title': 'Settings',
        'settings.server': 'Server',
        'settings.auth': 'Authentication',
        'settings.database': 'Database Defaults',
        'settings.email': 'Email',
        'settings.development': 'Development',
        'settings.security': 'Security',
        'settings.storage': 'Storage'
    },

    'pt-BR': {
        // Navegação
        'nav.dashboard': 'Painel',
        'nav.monitoring': 'Monitoramento',
        'nav.datasources': 'Fontes de Dados',
        'nav.containers': 'Containers',
        'nav.components': 'Componentes',
        'nav.playground': 'Playground',
        'nav.templates': 'Modelos',
        'nav.queryBuilder': 'Construtor de Consultas',
        'nav.apiExplorer': 'Explorador de API',
        'nav.logs': 'Logs',
        'nav.settings': 'Configurações',
        'nav.security': 'Segurança',

        // Dashboard
        'dashboard.title': 'Painel de Controle',
        'dashboard.components': 'Componentes Ativos',
        'dashboard.datasources': 'Fontes de Dados',
        'dashboard.containers': 'Containers Rodando',
        'dashboard.endpoints': 'Endpoints da API',
        'dashboard.recentDatasources': 'Fontes de Dados Recentes',
        'dashboard.systemHealth': 'Saúde do Sistema',

        // Botões
        'btn.refresh': 'Atualizar',
        'btn.save': 'Salvar',
        'btn.cancel': 'Cancelar',
        'btn.delete': 'Excluir',
        'btn.edit': 'Editar',
        'btn.create': 'Criar',
        'btn.export': 'Exportar',
        'btn.import': 'Importar',
        'btn.download': 'Baixar',
        'btn.upload': 'Enviar',
        'btn.run': 'Executar',
        'btn.copy': 'Copiar',
        'btn.share': 'Compartilhar',

        // Mensagens
        'msg.success': 'Operação realizada com sucesso',
        'msg.error': 'Ocorreu um erro',
        'msg.loading': 'Carregando...',
        'msg.noData': 'Nenhum dado disponível',
        'msg.confirmDelete': 'Tem certeza que deseja excluir?',
        'msg.unsavedChanges': 'Você tem alterações não salvas',

        // Fontes de Dados
        'datasources.title': 'Fontes de Dados',
        'datasources.new': 'Nova Fonte de Dados',
        'datasources.name': 'Nome',
        'datasources.type': 'Tipo',
        'datasources.status': 'Status',
        'datasources.connection': 'Conexão',
        'datasources.host': 'Host',
        'datasources.port': 'Porta',

        // Monitoramento
        'monitoring.title': 'Monitoramento do Sistema',
        'monitoring.cpu': 'Uso de CPU',
        'monitoring.memory': 'Memória Utilizada',
        'monitoring.disk': 'Uso de Disco',
        'monitoring.connections': 'Conexões Ativas',

        // Assistente AI
        'ai.title': 'Assistente IA Quantum',
        'ai.placeholder': 'Pergunte qualquer coisa sobre Quantum...',
        'ai.send': 'Enviar',
        'ai.close': 'Fechar',

        // Paleta de Comandos
        'cmd.placeholder': 'Digite um comando ou busca...',
        'cmd.navigate': 'Navegar',
        'cmd.actions': 'Ações',
        'cmd.noResults': 'Nenhum comando encontrado',

        // Configurações
        'settings.title': 'Configurações',
        'settings.server': 'Servidor',
        'settings.auth': 'Autenticação',
        'settings.database': 'Padrões de Banco',
        'settings.email': 'Email',
        'settings.development': 'Desenvolvimento',
        'settings.security': 'Segurança',
        'settings.storage': 'Armazenamento'
    }
};

class I18n {
    constructor() {
        this.currentLocale = localStorage.getItem('quantum-locale') || 'en';
        this.translations = TRANSLATIONS;
    }

    // Get translated text
    t(key, params = {}) {
        let text = this.translations[this.currentLocale][key] || key;

        // Replace params
        Object.keys(params).forEach(param => {
            text = text.replace(`{${param}}`, params[param]);
        });

        return text;
    }

    // Set locale
    setLocale(locale) {
        if (!this.translations[locale]) {
            console.error(`Locale ${locale} not found`);
            return;
        }

        this.currentLocale = locale;
        localStorage.setItem('quantum-locale', locale);

        // Update page
        this.updatePage();

        // Dispatch event
        window.dispatchEvent(new CustomEvent('localeChanged', { detail: { locale } }));
    }

    // Get current locale
    getLocale() {
        return this.currentLocale;
    }

    // Update all translatable elements
    updatePage() {
        document.querySelectorAll('[data-i18n]').forEach(element => {
            const key = element.getAttribute('data-i18n');
            element.textContent = this.t(key);
        });

        document.querySelectorAll('[data-i18n-placeholder]').forEach(element => {
            const key = element.getAttribute('data-i18n-placeholder');
            element.placeholder = this.t(key);
        });

        document.querySelectorAll('[data-i18n-title]').forEach(element => {
            const key = element.getAttribute('data-i18n-title');
            element.title = this.t(key);
        });
    }

    // Add language selector to header
    addLanguageSelector() {
        const header = document.querySelector('.header-actions');
        if (!header) return;

        const selector = document.createElement('select');
        selector.id = 'language-selector';
        selector.className = 'language-selector';
        selector.style.cssText = 'padding: 8px 12px; border: 1px solid var(--border-color); border-radius: 6px; background: var(--bg-secondary); color: var(--text-primary); cursor: pointer;';

        const locales = {
            'en': '🇺🇸 English',
            'pt-BR': '🇧🇷 Português'
        };

        Object.keys(locales).forEach(locale => {
            const option = document.createElement('option');
            option.value = locale;
            option.textContent = locales[locale];
            if (locale === this.currentLocale) {
                option.selected = true;
            }
            selector.appendChild(option);
        });

        selector.addEventListener('change', (e) => {
            this.setLocale(e.target.value);
            window.Quantum?.notify?.success(this.t('msg.success'));
        });

        header.insertBefore(selector, header.firstChild);
    }
}

// Global instance
const i18n = new I18n();

// Initialize on load
document.addEventListener('DOMContentLoaded', function() {
    i18n.updatePage();
    i18n.addLanguageSelector();
});

// Export
window.i18n = i18n;
