"""admin.settings.* e o editor de YAML que preserva comentarios."""

import shutil

import pytest
import yaml

from quantum_admin.services import _yaml_editor as editor
from quantum_admin.services import settings as svc

REPO_CONFIG = __import__("pathlib").Path(__file__).resolve().parents[2] / "quantum.config.yaml"

CONFIG = """# Configuracao do servidor
server:
  # Porta
  port: 8080   # padrao
  host: 127.0.0.1

  debug: false

paths:
  components: ./components
"""


@pytest.fixture(autouse=True)
def isolado(admin_isolado):
    return admin_isolado


class TestEditor:
    def test_troca_so_o_valor_e_mantem_comentarios(self):
        novo = editor.editar_texto(CONFIG, {("server", "port"): 9090, ("server", "debug"): True})
        assert "  port: 9090   # padrao" in novo
        assert "# Porta" in novo and "# Configuracao do servidor" in novo
        assert "  debug: true" in novo
        assert novo.count("\n") == CONFIG.count("\n")

    def test_insere_chave_e_secao_que_faltam(self):
        novo = editor.editar_texto(CONFIG, {("server", "reload"): False, ("logging", "level"): "INFO"})
        dados = yaml.safe_load(novo)
        assert dados["server"]["reload"] is False and dados["logging"] == {"level": "INFO"}
        assert dados["paths"] == {"components": "./components"}

    def test_texto_que_parece_outro_tipo_e_citado(self, tmp_path):
        arquivo = tmp_path / "c.yaml"
        arquivo.write_text(CONFIG, encoding="utf-8")
        editor.gravar_valores(arquivo, {("server", "host"): "true", ("server", "port"): 8081})
        dados = yaml.safe_load(arquivo.read_text(encoding="utf-8"))
        assert dados["server"]["host"] == "true" and dados["server"]["port"] == 8081

    def test_recusa_quando_o_resultado_nao_seria_o_pedido(self, tmp_path):
        # chave duplicada: editar a primeira nao muda o valor efetivo (o YAML usa a ultima)
        arquivo = tmp_path / "c.yaml"
        original = "server:\n  port: 1\n  port: 2\n"
        arquivo.write_text(original, encoding="utf-8")
        with pytest.raises(editor.YamlEditError):
            editor.gravar_valores(arquivo, {("server", "port"): 3})
        assert arquivo.read_text(encoding="utf-8") == original

    def test_no_config_real_do_repositorio_so_as_linhas_pedidas_mudam(self, tmp_path):
        copia = tmp_path / "quantum.config.yaml"
        shutil.copy2(REPO_CONFIG, copia)
        antes = copia.read_text(encoding="utf-8").splitlines()
        editor.gravar_valores(copia, {("server", "port"): 8181, ("server", "debug"): False})
        depois = copia.read_text(encoding="utf-8").splitlines()
        assert len(antes) == len(depois)
        diferentes = [(a, d) for a, d in zip(antes, depois) if a != d]
        assert len(diferentes) == 1 and "8181" in diferentes[0][1]
        assert sum(1 for l in depois if l.lstrip().startswith("#")) == sum(1 for l in antes if l.lstrip().startswith("#"))


class TestConfigDoServidor:
    def test_le_o_arquivo(self, isolado):
        (isolado / "quantum.config.yaml").write_text(CONFIG, encoding="utf-8")
        c = svc.server_config()
        assert c["found"] and c["server"] == {"port": 8080, "host": "127.0.0.1", "debug": False, "reload": False}

    def test_sem_arquivo(self):
        assert svc.server_config()["found"] is False

    def test_salvar_preserva_comentarios(self, isolado):
        (isolado / "quantum.config.yaml").write_text(CONFIG, encoding="utf-8")
        svc.save_server_config(port=9000, host="127.0.0.1", debug=True, log_level="warning")
        texto = (isolado / "quantum.config.yaml").read_text(encoding="utf-8")
        assert "# Porta" in texto and "port: 9000   # padrao" in texto
        assert yaml.safe_load(texto)["logging"]["level"] == "WARNING"

    @pytest.mark.parametrize("campos,motivo", [
        ({"port": 70000, "host": "127.0.0.1"}, "between 1 and 65535"),
        ({"port": "abc", "host": "127.0.0.1"}, "must be a number"),
        ({"port": 8080, "host": ""}, "host is required"),
        ({"port": 8080, "host": "0.0.0.0", "debug": True}, "debug cannot be on"),
        ({"port": 8080, "host": "127.0.0.1", "log_level": "verbose"}, "log_level"),
    ])
    def test_valores_invalidos_sao_erro_e_nada_e_gravado(self, isolado, campos, motivo):
        (isolado / "quantum.config.yaml").write_text(CONFIG, encoding="utf-8")
        with pytest.raises(svc.SettingsError, match=motivo):
            svc.save_server_config(**campos)
        assert (isolado / "quantum.config.yaml").read_text(encoding="utf-8") == CONFIG


def test_configuracao_global_mascara_segredos(isolado):
    (isolado / "quantum_admin" / "settings" / "global.yaml").write_text(
        "email:\n  smtp_password: senha-real\n  smtp_user: eu\nsecurity:\n  jwt_secret: ${JWT_SECRET}\n",
        encoding="utf-8")
    g = svc.global_get()
    assert "senha-real" not in str(g)
    assert g["email"]["smtp_password"] == "****" and g["email"]["smtp_user"] == "eu"
    assert g["security"]["jwt_secret"] == "${JWT_SECRET}"


def test_informacoes_do_sistema_contam_registros_reais():
    info = svc.system_info()
    assert info["parser_tags"] > 20 and info["executors"] > 20       # a tela antiga mostrava 0
