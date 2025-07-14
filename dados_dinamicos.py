import pandas as pd

# --- Leitura segura do Excel ---
try:
    df_vendas = pd.read_excel("vendas_ultimos_30_dias.xlsx")
    print("✅ Base de dados carregada com sucesso.")
except Exception as e:
    print("❌ Erro ao carregar o Excel:", e)
    df_vendas = pd.DataFrame(columns=["familia_produto", "sku", "bairro", "nomecliente", "endereco"])

# --- Retorna lista de famílias disponíveis ---
def obter_familias_ativas():
    return sorted(df_vendas["familia_produto"].dropna().unique().tolist())

# --- Retorna SKUs da família escolhida ---
def obter_skus_por_familia(familia):
    df_filtrado = df_vendas[df_vendas["familia_produto"] == familia]
    return sorted(df_filtrado["sku"].dropna().unique().tolist())

# --- Retorna bairros para o SKU selecionado ---
def obter_bairros_por_sku(sku):
    df_filtrado = df_vendas[df_vendas["sku"] == sku]
    return sorted(df_filtrado["bairro"].dropna().unique().tolist())

# --- Retorna lista de pontos de venda (nome + endereço) ---
def obter_pontos_venda(sku, bairro):
    df_filtrado = df_vendas[
        (df_vendas["sku"] == sku) & 
        (df_vendas["bairro"] == bairro)
    ]

    pontos_formatados = []
    for _, row in df_filtrado.iterrows():
        nome = row.get("nomecliente", "Sem nome")
        endereco = row.get("endereco", "Sem endereço")
        pontos_formatados.append(f"{nome} — {endereco}")
    
    return pontos_formatados
