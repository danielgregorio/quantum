"""
Serviços declarados do Quantum Admin (passo A2 do plano de oficialização).

As telas .q de components/admin chamam estas funções com
`<q:invoke service="admin.<área>.<ação>">`. Elas envolvem a biblioteca que já
existia em quantum_admin/backend (modelos, crud, serviços), para que o admin
tenha UMA fonte de dados — o banco do admin — em vez de dois caminhos: o
FastAPI gravava no banco, e as telas .q em quantum_admin/settings/*.yaml.

Cada módulo registra os serviços de uma área:

    admin.projects.*   projects.py
    admin.import.*     yaml_import.py   (traz os YAML antigos para o banco)

quantum.config.yaml lista os módulos em `services:` (SVC-2).
"""
