import requests
from datetime import datetime, timezone
from config import SUPABASE_URL, SUPABASE_KEY

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

def enviar_interacao_supabase(dados):
    try:
        url = f"{SUPABASE_URL}/rest/v1/interacoes_clientes"

        registro = {
            "cliente_id": dados.get("cliente_id"),
            "telefone": dados.get("telefone"),
            "familia_produto": dados.get("familia_produto"),
            "sku": dados.get("sku"),
            "bairro": dados.get("bairro"),
            "pontos_venda_retorno": dados.get("pontos_venda_retorno", []),
            "data_hora_contato": dados.get("data_hora_contato") or datetime.now(timezone.utc).isoformat()
        }

        response = requests.post(url, headers=headers, json=registro)
        response.raise_for_status()

        resp_json = response.json()
        if isinstance(resp_json, list) and len(resp_json) > 0 and "id" in resp_json[0]:
            print("✅ Dados enviados ao Supabase.")
            return resp_json[0]["id"]
        else:
            print("❌ Resposta inesperada do Supabase:", resp_json)
            return None

    except requests.exceptions.HTTPError as http_err:
        print(f"❌ HTTP error ao enviar dados para o Supabase: {http_err} - {response.text}")
        return None
    except Exception as e:
        print("❌ Exceção ao enviar dados para o Supabase:", e)
        return None


def salvar_resposta_followup(dados):
    try:
        url = f"{SUPABASE_URL}/rest/v1/respostas_retorno"

        registro = {
            "interacao_id": dados.get("interacao_id"),
            "encontrou_produto": dados.get("encontrou_produto"),
            "nota_produto": dados.get("nota_produto"),
            "motivo_nao_encontrou": dados.get("motivo_nao_encontrou"),
            "data_resposta": dados.get("data_resposta") or datetime.now(timezone.utc).isoformat()
        }

        if registro["interacao_id"] is None:
            print("❌ Erro: 'interacao_id' é obrigatório para salvar resposta.")
            return

        response = requests.post(url, headers=headers, json=registro)
        response.raise_for_status()

        print("✅ Resposta de follow-up salva no Supabase.")

    except requests.exceptions.HTTPError as http_err:
        print(f"❌ HTTP error ao salvar resposta de follow-up: {http_err} - {response.text}")
    except Exception as e:
        print("❌ Exceção ao salvar resposta de follow-up:", e)
