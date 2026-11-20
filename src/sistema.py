import os

# ---------------------------------------------------------------
# Neighborhood Action Dashboard - Global Solution 2026.2
# Painel comunitário de ocorrências de bairro (dados simulados)
# Como executar: python src/sistema.py
# ---------------------------------------------------------------

DIA_ATUAL = 30        # "hoje" na simulação (os dias vão de 1 a 30)
LIMITE_ATRASO = 15    # pendência parada há mais dias que isso conta como atrasada

# valores padronizados (iguais aos do arquivo CSV)
CATEGORIAS = ['iluminacao', 'acessibilidade', 'limpeza', 'conservacao']
SITUACOES = ['aberta', 'em_analise', 'concluida']

# nome que aparece na tela para cada valor padronizado
NOMES = {
    'iluminacao': 'Iluminação',
    'acessibilidade': 'Acessibilidade',
    'limpeza': 'Limpeza',
    'conservacao': 'Conservação',
    'aberta': 'Aberta',
    'em_analise': 'Em análise',
    'concluida': 'Concluída',
}

PASTA_DADOS = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')

# ----- estruturas de dados -----
ocorrencias = []    # lista: todas as ocorrências válidas, na ordem de registro
indice = {}         # dicionário: código -> ocorrência (acesso direto pelo código)
fila = []           # fila: códigos das abertas; a primeira que entrou é a primeira atendida
pilha = []          # pilha: alterações de situação; a mais recente fica no topo
arvore = {}         # hierarquia: bairro -> categoria -> lista de códigos
rejeitados = []     # registros do arquivo que não passaram na validação


# ---------------------------------------------------------------
# Entrada de dados
# ---------------------------------------------------------------

def ler_inteiro(mensagem, minimo, maximo):
    while True:
        texto = input(mensagem).strip()
        if texto.isdigit() and int(texto) >= minimo and int(texto) <= maximo:
            return int(texto)
        print(f'Entrada inválida. Digite um número de {minimo} a {maximo}.')


def ler_texto(mensagem):
    while True:
        texto = input(mensagem).strip()
        if texto != '':
            return texto
        print('Este campo é obrigatório.')


def escolher(titulo, opcoes, permite_todas):
    '''Mostra as opções numeradas e devolve a escolhida ('' quer dizer todas).'''
    print(f'\n{titulo}:')
    for i in range(len(opcoes)):
        print(f'  {i + 1} - {NOMES[opcoes[i]]}')
    minimo = 1
    if permite_todas:
        print('  0 - Todas')
        minimo = 0
    numero = ler_inteiro('Número da opção: ', minimo, len(opcoes))
    if numero == 0:
        return ''
    return opcoes[numero - 1]


def normalizar_codigo(texto):
    '''Aceita "14", "014" ou "oc014" e devolve "OC014". Devolve '' se não for código.'''
    texto = texto.strip().upper()
    if texto.startswith('OC'):
        texto = texto[2:]
    if not texto.isdigit():
        return ''
    return 'OC' + texto.zfill(3)


# ---------------------------------------------------------------
# Regras lógicas
# ---------------------------------------------------------------

def parece_dado_pessoal(texto):
    '''Privacidade: e-mail ou número longo (telefone, CPF) não entra no painel.'''
    digitos = 0
    for letra in texto:
        if letra.isdigit():
            digitos += 1
    return '@' in texto or digitos >= 8


def validar_ocorrencia(oc):
    '''Devolve o motivo da recusa, ou '' quando o registro está correto.'''
    if oc['id'] == '' or oc['id'] in indice:
        return 'código vazio ou repetido'
    elif not oc['categoria'] or oc['categoria'] not in CATEGORIAS:
        return 'categoria ausente ou desconhecida'
    elif oc['situacao'] not in SITUACOES:
        return 'situação desconhecida'
    elif oc['bairro'] == '' or oc['local'] == '' or oc['descricao'] == '':
        return 'bairro, local ou descrição em branco'
    elif oc['dia'] < 1 or oc['dia'] > DIA_ATUAL:
        return f'dia de abertura fora do período de 1 a {DIA_ATUAL}'
    elif parece_dado_pessoal(oc['descricao']) or parece_dado_pessoal(oc['local']):
        return 'o texto parece conter dado pessoal'
    else:
        return ''


def pode_mudar_situacao(atual, nova):
    '''Regra de andamento: diz se a ocorrência pode sair de "atual" e ir para "nova".'''
    if atual == 'aberta':
        return nova == 'em_analise'
    elif atual == 'em_analise':
        return nova == 'concluida'
    else:
        return False


def tempo_acompanhamento(oc):
    '''Dias entre a abertura e a conclusão; se ainda não concluiu, conta até hoje.'''
    if oc['situacao'] == 'concluida' and oc['dia_conclusao'] > 0:
        return oc['dia_conclusao'] - oc['dia']
    else:
        return DIA_ATUAL - oc['dia']


# ---------------------------------------------------------------
# Registro nas estruturas
# ---------------------------------------------------------------

def registrar(oc):
    '''Guarda uma ocorrência já validada em todas as estruturas.'''
    ocorrencias.append(oc)
    indice[oc['id']] = oc

    if oc['bairro'] not in arvore:
        arvore[oc['bairro']] = {}
    if oc['categoria'] not in arvore[oc['bairro']]:
        arvore[oc['bairro']][oc['categoria']] = []
    arvore[oc['bairro']][oc['categoria']].append(oc['id'])

    if oc['situacao'] == 'aberta':
        fila.append(oc['id'])


def mudar_situacao(oc, nova, dia):
    '''Troca a situação e guarda a alteração no histórico (pilha).'''
    pilha.append({'id': oc['id'], 'dia': dia, 'de': oc['situacao'], 'para': nova})
    oc['situacao'] = nova

    if nova == 'concluida':
        oc['dia_conclusao'] = dia
    else:
        oc['dia_conclusao'] = 0

    # a fila só guarda ocorrências abertas
    if oc['id'] in fila and nova != 'aberta':
        fila.remove(oc['id'])
    elif nova == 'aberta' and oc['id'] not in fila:
        fila.append(oc['id'])


def proximo_codigo():
    maior = 0
    for oc in ocorrencias + rejeitados:
        numero = oc['id'][2:]
        if numero.isdigit() and int(numero) > maior:
            maior = int(numero)
    return 'OC' + str(maior + 1).zfill(3)


def ultimo_dia(oc):
    '''Dia do último evento da ocorrência (ou o dia da abertura).'''
    dia = oc['dia']
    for evento in pilha:
        if evento['id'] == oc['id'] and evento['dia'] > dia:
            dia = evento['dia']
    return dia


# ---------------------------------------------------------------
# Leitura dos arquivos
# ---------------------------------------------------------------

def ler_linhas(nome_arquivo):
    '''Devolve as linhas do arquivo sem o cabeçalho e sem linhas vazias.'''
    caminho = os.path.join(PASTA_DADOS, nome_arquivo)
    try:
        with open(caminho, encoding='utf-8') as arquivo:
            linhas = arquivo.readlines()
    except FileNotFoundError:
        print(f'Aviso: arquivo {nome_arquivo} não encontrado. O painel começa vazio.')
        return []

    resultado = []
    for linha in linhas[1:]:
        linha = linha.strip()
        if linha != '':
            resultado.append(linha)
    return resultado


def carregar_ocorrencias():
    for linha in ler_linhas('ocorrencias.csv'):
        campos = linha.split(';')
        if len(campos) != 7:
            rejeitados.append({'id': campos[0], 'motivo': 'linha sem os 7 campos'})
            continue

        dia = 0
        if campos[5].strip().isdigit():
            dia = int(campos[5])

        oc = {
            'id': campos[0].strip().upper(),
            'bairro': campos[1].strip(),
            'categoria': campos[2].strip().lower(),
            'descricao': campos[3].strip(),
            'local': campos[4].strip(),
            'dia': dia,
            'situacao': campos[6].strip().lower(),
            'dia_conclusao': 0,
        }

        motivo = validar_ocorrencia(oc)
        if motivo == '':
            registrar(oc)
        else:
            rejeitados.append({'id': oc['id'], 'motivo': motivo})


def carregar_historico():
    for linha in ler_linhas('historico.csv'):
        campos = linha.split(';')
        if len(campos) != 4 or not campos[1].isdigit():
            continue
        codigo = campos[0].strip().upper()
        dia = int(campos[1])
        de = campos[2].strip().lower()
        para = campos[3].strip().lower()

        # evento de ocorrência que não existe ou com situação desconhecida é ignorado
        if codigo in indice and de in SITUACOES and para in SITUACOES:
            pilha.append({'id': codigo, 'dia': dia, 'de': de, 'para': para})
            if para == 'concluida':
                indice[codigo]['dia_conclusao'] = dia


# ---------------------------------------------------------------
# Telas
# ---------------------------------------------------------------

def limpar_tela():
    '''Apaga o que está no terminal (cls no Windows, clear no Linux e no Mac).'''
    if os.name == 'nt':
        os.system('cls')
    else:
        os.system('clear')


def voltar_ao_menu():
    input('\nAperte ENTER para voltar ao menu...')


def titulo(texto):
    print()
    print('=' * 60)
    print(texto)
    print('=' * 60)


def mostrar_tabela(lista):
    if len(lista) == 0:
        print('Nenhuma ocorrência para mostrar.')
        return
    print(f'{"Código":<7} {"Categoria":<15} {"Bairro":<17} {"Local":<25} {"Dia":>3}  Situação')
    print('-' * 82)
    for oc in lista:
        print(f'{oc["id"]:<7} {NOMES[oc["categoria"]]:<15} {oc["bairro"]:<17} '
              f'{oc["local"]:<25} {oc["dia"]:>3}  {NOMES[oc["situacao"]]}')
    print(f'Total: {len(lista)} ocorrência(s).')


def mostrar_evento(evento):
    print(f'  Dia {evento["dia"]:>2} | {evento["id"]} | '
          f'{NOMES[evento["de"]]} -> {NOMES[evento["para"]]}')


def listar_todas():
    titulo('OCORRÊNCIAS CADASTRADAS')
    mostrar_tabela(ocorrencias)


def cadastrar():
    titulo('NOVA OCORRÊNCIA')
    print('Não informe nomes, telefones, e-mails nem endereço com número.')
    print('Use um local genérico, como "Praça Central".')

    oc = {
        'id': proximo_codigo(),
        'bairro': ler_texto('Bairro: ').title(),
        'categoria': escolher('Categoria', CATEGORIAS, False),
        'descricao': ler_texto('Descrição breve: '),
        'local': ler_texto('Local genérico: '),
        'dia': ler_inteiro(f'Dia da abertura (1 a {DIA_ATUAL}): ', 1, DIA_ATUAL),
        'situacao': 'aberta',
        'dia_conclusao': 0,
    }

    motivo = validar_ocorrencia(oc)
    if motivo == '':
        registrar(oc)
        print(f'\nOcorrência {oc["id"]} cadastrada como Aberta e colocada no fim da fila.')
    else:
        print(f'\nCadastro recusado: {motivo}.')


def buscar_por_codigo():
    titulo('BUSCA POR CÓDIGO')
    codigo = normalizar_codigo(input('Código (exemplo: 14 ou OC014): '))
    if codigo == '':
        print('Código inválido. Use o número da ocorrência, como 14 ou OC014.')
    elif codigo not in indice:
        print(f'Ocorrência {codigo} não encontrada.')
    else:
        oc = indice[codigo]
        print(f'Código:     {oc["id"]}')
        print(f'Categoria:  {NOMES[oc["categoria"]]}')
        print(f'Bairro:     {oc["bairro"]}')
        print(f'Local:      {oc["local"]}')
        print(f'Descrição:  {oc["descricao"]}')
        print(f'Abertura:   dia {oc["dia"]}')
        print(f'Situação:   {NOMES[oc["situacao"]]}')
        print(f'Tempo de acompanhamento: {tempo_acompanhamento(oc)} dia(s)')
        print('Histórico:')
        quantidade = 0
        for evento in pilha:
            if evento['id'] == codigo:
                mostrar_evento(evento)
                quantidade += 1
        if quantidade == 0:
            print('  Nenhuma alteração registrada.')


def filtrar():
    titulo('FILTRO POR CATEGORIA E SITUAÇÃO')
    categoria = escolher('Categoria', CATEGORIAS, True)
    situacao = escolher('Situação', SITUACOES, True)

    encontradas = []
    for oc in ocorrencias:
        if (categoria == '' or oc['categoria'] == categoria) and \
           (situacao == '' or oc['situacao'] == situacao):
            encontradas.append(oc)

    print()
    mostrar_tabela(encontradas)


def atualizar_situacao():
    titulo('ATUALIZAR SITUAÇÃO')
    codigo = normalizar_codigo(input('Código da ocorrência: '))
    if codigo == '' or codigo not in indice:
        print('Ocorrência não encontrada. Confira o código na listagem (opção 1).')
        return

    oc = indice[codigo]
    print(f'{oc["id"]} - {oc["descricao"]} ({oc["local"]})')
    print(f'Situação atual: {NOMES[oc["situacao"]]}')
    nova = escolher('Nova situação', SITUACOES, False)

    if nova not in SITUACOES:
        print('Situação desconhecida. Nada foi alterado.')
    elif not pode_mudar_situacao(oc['situacao'], nova):
        print(f'Mudança não permitida: de {NOMES[oc["situacao"]]} para {NOMES[nova]}.')
    else:
        minimo = ultimo_dia(oc)
        dia = ler_inteiro(f'Dia da alteração ({minimo} a {DIA_ATUAL}): ', minimo, DIA_ATUAL)
        anterior = oc['situacao']
        mudar_situacao(oc, nova, dia)
        print(f'{oc["id"]}: {NOMES[anterior]} -> {NOMES[nova]}. Alteração guardada no histórico.')


def atender_proxima():
    titulo('FILA DE OCORRÊNCIAS ABERTAS')
    if len(fila) == 0:
        print('A fila está vazia: não há ocorrência aberta esperando análise.')
        return

    print(f'Na fila, por ordem de registro: {", ".join(fila)}')
    oc = indice[fila[0]]
    print(f'Próxima: {oc["id"]} - {NOMES[oc["categoria"]]} - {oc["descricao"]} ({oc["local"]})')

    resposta = input('Colocar esta ocorrência em análise? (s/n): ').strip().lower()
    if resposta == 's':
        minimo = ultimo_dia(oc)
        dia = ler_inteiro(f'Dia da alteração ({minimo} a {DIA_ATUAL}): ', minimo, DIA_ATUAL)
        mudar_situacao(oc, 'em_analise', dia)    # sai do começo da fila
        print(f'{oc["id"]} agora está Em análise. Restam {len(fila)} na fila.')
    else:
        print('Nada foi alterado.')


def ultimas_atualizacoes():
    titulo('ÚLTIMAS ATUALIZAÇÕES')
    if len(pilha) == 0:
        print('Nenhuma alteração registrada.')
        return
    quantidade = ler_inteiro(f'Quantas mostrar (1 a {len(pilha)}): ', 1, len(pilha))
    print('Da mais recente para a mais antiga:')
    posicao = len(pilha) - 1          # topo da pilha
    while posicao >= len(pilha) - quantidade:
        mostrar_evento(pilha[posicao])
        posicao -= 1


def mostrar_hierarquia():
    titulo('BAIRRO > CATEGORIA > OCORRÊNCIAS')
    for bairro in arvore:
        print(bairro)
        for categoria in arvore[bairro]:
            codigos = arvore[bairro][categoria]
            print(f'  {NOMES[categoria]} ({len(codigos)}): {", ".join(codigos)}')


def mostrar_rejeitados():
    titulo('REGISTROS REJEITADOS NA LEITURA DO ARQUIVO')
    if len(rejeitados) == 0:
        print('Nenhum registro rejeitado.')
        return
    for registro in rejeitados:
        print(f'  {registro["id"]}: {registro["motivo"]}')
    print('Estes registros não entram na listagem nem nos indicadores.')
    print('Para aproveitá-los, corrija o campo no arquivo data/ocorrencias.csv.')


# ---------------------------------------------------------------
# Indicadores
# ---------------------------------------------------------------

def montar_matriz():
    '''Matriz (lista de listas): cada linha é uma categoria, cada coluna uma situação.'''
    matriz = []
    for i in range(len(CATEGORIAS)):
        matriz.append([0] * len(SITUACOES))
    for oc in ocorrencias:
        linha = CATEGORIAS.index(oc['categoria'])
        coluna = SITUACOES.index(oc['situacao'])
        matriz[linha][coluna] += 1
    return matriz


def ordenar_por_dia(lista):
    '''Bubble sort: devolve uma cópia com a abertura mais antiga primeiro.'''
    copia = lista[:]
    for i in range(len(copia) - 1):
        for j in range(len(copia) - 1 - i):
            if copia[j]['dia'] > copia[j + 1]['dia']:
                copia[j], copia[j + 1] = copia[j + 1], copia[j]
    return copia


def porcentagem(parte, total):
    if total == 0:
        return 0
    return parte / total * 100


def mostrar_indicadores():
    titulo(f'INDICADORES (dia simulado {DIA_ATUAL})')
    total = len(ocorrencias)
    print(f'Dados de origem: {total} ocorrências válidas '
          f'({len(rejeitados)} registro(s) rejeitado(s) ficaram de fora).')
    if total == 0:
        return

    matriz = montar_matriz()

    print('\n1) Matriz categoria x situação')
    print(f'{"":<15} {"Aberta":>7} {"Em análise":>11} {"Concluída":>10} {"Total":>6} {"%":>6}')
    por_categoria = []
    for i in range(len(CATEGORIAS)):
        soma = 0
        for j in range(len(SITUACOES)):
            soma += matriz[i][j]
        por_categoria.append(soma)
        print(f'{NOMES[CATEGORIAS[i]]:<15} {matriz[i][0]:>7} {matriz[i][1]:>11} '
              f'{matriz[i][2]:>10} {soma:>6} {porcentagem(soma, total):>5.1f}%')

    por_situacao = []
    for j in range(len(SITUACOES)):
        soma = 0
        for i in range(len(CATEGORIAS)):
            soma += matriz[i][j]
        por_situacao.append(soma)
    print(f'{"Total":<15} {por_situacao[0]:>7} {por_situacao[1]:>11} '
          f'{por_situacao[2]:>10} {total:>6}')
    print('Regra: % = quantidade da categoria / total de ocorrências * 100')

    print('\n2) Proporção por situação')
    for j in range(len(SITUACOES)):
        print(f'  {NOMES[SITUACOES[j]]:<11} {por_situacao[j]:>3}  '
              f'{porcentagem(por_situacao[j], total):>5.1f}%')

    print('\n3) Pendências (toda ocorrência que não está Concluída)')
    pendentes = []
    atrasadas = 0
    for oc in ocorrencias:
        if oc['situacao'] != 'concluida':
            pendentes.append(oc)
            if DIA_ATUAL - oc['dia'] > LIMITE_ATRASO:
                atrasadas += 1
    print(f'  Pendentes: {len(pendentes)} de {total} '
          f'({porcentagem(len(pendentes), total):.1f}%)')
    print(f'  Atrasadas (pendentes há mais de {LIMITE_ATRASO} dias): {atrasadas}')
    print('  As três mais antigas:')
    for oc in ordenar_por_dia(pendentes)[:3]:
        print(f'    {oc["id"]} - {NOMES[oc["categoria"]]} - {oc["local"]} - '
              f'{tempo_acompanhamento(oc)} dias em acompanhamento')

    print('\n4) Tempo médio simulado até a conclusão')
    soma_dias = 0
    concluidas = 0
    for oc in ocorrencias:
        if oc['situacao'] == 'concluida' and oc['dia_conclusao'] > 0:
            dias = oc['dia_conclusao'] - oc['dia']
            print(f'  {oc["id"]}: dia {oc["dia_conclusao"]} - dia {oc["dia"]} = {dias} dias')
            soma_dias += dias
            concluidas += 1
    print('  Regra: soma(dia da conclusão - dia da abertura) / quantidade de concluídas')
    if concluidas > 0:
        print(f'  Resultado: {soma_dias} / {concluidas} = {soma_dias / concluidas:.1f} dias')
    else:
        print('  Ainda não há ocorrência concluída para calcular.')

    print('\nLeitura dos números:')
    maior = 0
    for i in range(len(CATEGORIAS)):
        if por_categoria[i] > por_categoria[maior]:
            maior = i
    print(f'  A categoria com mais registros é {NOMES[CATEGORIAS[maior]]} '
          f'({por_categoria[maior]} de {total}).')

    perc_pendentes = porcentagem(len(pendentes), total)
    if perc_pendentes >= 70:
        print('  A maior parte das demandas ainda espera solução: o bairro registra')
        print('  problemas mais rápido do que eles são resolvidos.')
    elif perc_pendentes >= 40:
        print('  Cerca de metade das demandas já foi resolvida; vale acompanhar as atrasadas.')
    else:
        print('  A maior parte das demandas já foi concluída.')
    print('  Os dados são simulados: servem para testar o painel, não para decidir obras.')


# ---------------------------------------------------------------
# Menu principal
# ---------------------------------------------------------------

def menu():
    while True:
        limpar_tela()
        titulo('NEIGHBORHOOD ACTION DASHBOARD - painel de ocorrências do bairro')
        print(f'{len(ocorrencias)} ocorrências carregadas, {len(rejeitados)} registro(s) rejeitado(s) '
              f'(veja a opção 10), {len(pilha)} alterações no histórico.\n')
        print(' 1 - Listar ocorrências')
        print(' 2 - Cadastrar nova ocorrência')
        print(' 3 - Buscar por código')
        print(' 4 - Filtrar por categoria e situação')
        print(' 5 - Atualizar situação')
        print(' 6 - Atender a próxima da fila de abertas')
        print(' 7 - Ver últimas atualizações')
        print(' 8 - Ver por bairro e categoria')
        print(' 9 - Indicadores')
        print('10 - Registros rejeitados na leitura')
        print(' 0 - Sair')
        opcao = input('Digite o número da opção e aperte ENTER: ').strip()

        if opcao == '0':
            print('Até logo.')
            break

        limpar_tela()
        if opcao == '1':
            listar_todas()
        elif opcao == '2':
            cadastrar()
        elif opcao == '3':
            buscar_por_codigo()
        elif opcao == '4':
            filtrar()
        elif opcao == '5':
            atualizar_situacao()
        elif opcao == '6':
            atender_proxima()
        elif opcao == '7':
            ultimas_atualizacoes()
        elif opcao == '8':
            mostrar_hierarquia()
        elif opcao == '9':
            mostrar_indicadores()
        elif opcao == '10':
            mostrar_rejeitados()
        else:
            print('Opção inválida. Digite um número de 0 a 10.')
        voltar_ao_menu()


carregar_ocorrencias()
carregar_historico()
menu()
