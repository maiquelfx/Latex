import os

def listar_estrutura(raiz, arquivo_saida, prefixo=''):
    ignorar = {'node_modules', '.git'}
    itens = sorted([item for item in os.listdir(raiz) if item not in ignorar])
    
    for i, item in enumerate(itens):
        caminho_completo = os.path.join(raiz, item)
        ultimo = (i == len(itens) - 1)
        conector = '└── ' if ultimo else '├── '
        
        arquivo_saida.write(f"{prefixo}{conector}{item}\n")
        
        if os.path.isdir(caminho_completo):
            novo_prefixo = prefixo + ('    ' if ultimo else '│   ')
            listar_estrutura(caminho_completo, arquivo_saida, novo_prefixo)

if __name__ == "__main__":
    pasta_atual = os.path.dirname(os.path.abspath(__file__))
    caminho_saida = os.path.join(pasta_atual, 'estrutura.txt')
    
    with open(caminho_saida, 'w', encoding='utf-8') as f:
        f.write(f"{os.path.basename(pasta_atual)}\n")
        listar_estrutura(pasta_atual, f)
    
    print(f"Estrutura salva em: {caminho_saida}")