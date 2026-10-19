"""Cliente de leitura Kobo v2; nunca guarda credenciais no código."""
from urllib.parse import urlparse
import requests

DEFAULT_BASE_URL = "https://kf.kobo.ucp-pch.org"
PRE_UID = "a9UStPiv4QDyzfZeHiBzwu"
POS_UID = "a2JXAwUZP7h3z3nUmpfchj"


class KoboAPIError(RuntimeError):
    pass


def fetch_submissions(base_url: str, asset_uid: str, token: str, max_pages: int = 200):
    """Carrega todas as páginas da API v2, verifica os redirects e o destino do next.

    Não imprimimos cabeçalhos, URL com credenciais nem bodies com respostas.
    """
    if not token or not token.strip():
        raise KoboAPIError("Token Kobo não configurado.")
    base = base_url.rstrip("/")
    parsed_base = urlparse(base)
    if parsed_base.scheme != "https" or not parsed_base.netloc:
        raise KoboAPIError("O endereço do servidor Kobo tem de usar HTTPS.")
    if not asset_uid.isalnum():
        raise KoboAPIError("Identificador do formulário inválido.")

    url = f"{base}/api/v2/assets/{asset_uid}/data/"
    params = {"limit": 1000}
    records = []
    seen_urls = set()
    try:
        with requests.Session() as session:
            session.headers.update({
                "Authorization": f"Token {token.strip()}",
                "Accept": "application/json",
                "User-Agent": "FBP-PCH-Streamlit-Dashboard/1.0",
            })
            for _ in range(max_pages):
                p = urlparse(url)
                if p.scheme != "https" or p.netloc != parsed_base.netloc or not p.path.startswith("/api/v2/assets/"):
                    raise KoboAPIError("A resposta da API apontou para um endereço não autorizado.")
                if url in seen_urls:
                    raise KoboAPIError("A paginação da API entrou num ciclo.")
                seen_urls.add(url)
                response = session.get(url, params=params, timeout=(10, 40), allow_redirects=False)
                if response.status_code in (301, 302, 303, 307, 308):
                    raise KoboAPIError("O servidor Kobo redirecionou a API. Confirma o domínio e HTTPS.")
                if response.status_code in (401, 403):
                    raise KoboAPIError("Acesso recusado. Verifica se o token tem permissão para ler os dois projetos.")
                if response.status_code == 404:
                    raise KoboAPIError(f"Projeto Kobo não encontrado ou inacessível: {asset_uid}.")
                if response.status_code >= 400:
                    raise KoboAPIError(f"O Kobo devolveu HTTP {response.status_code}.")
                try:
                    body = response.json()
                except ValueError:
                    raise KoboAPIError("O servidor Kobo não devolveu JSON válido.") from None
                if isinstance(body, list):  # compatibilidade com instalações personalizadas
                    records.extend(body)
                    return records
                if not isinstance(body, dict) or not isinstance(body.get("results"), list):
                    raise KoboAPIError("Formato de resposta inesperado na API Kobo.")
                records.extend(body["results"])
                nxt = body.get("next")
                if not nxt:
                    return records
                url = requests.compat.urljoin(url, str(nxt))
                params = None
            raise KoboAPIError("Número máximo de páginas da API atingido. Aumenta max_pages.")
    except requests.exceptions.Timeout:
        raise KoboAPIError("Tempo de espera esgotado ao contactar o Kobo.") from None
    except requests.exceptions.SSLError:
        raise KoboAPIError("Falha de certificado HTTPS no servidor Kobo.") from None
    except requests.exceptions.ConnectionError:
        raise KoboAPIError("Não foi possível contactar o servidor Kobo. Verifica a rede e o domínio.") from None
