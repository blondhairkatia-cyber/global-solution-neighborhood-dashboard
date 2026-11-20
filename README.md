# Neighborhood Action Dashboard

Global Solution 2026.2 (CitizenTech) - painel comunitário para registrar e acompanhar ocorrências de bairro.

## Equipe

Trabalho individual (equipe de um integrante).

| Nome | RM |
|------|----|
| Fhilipe Gregorio | RM574609 |

## Comunidade simulada

Três bairros fictícios de uma mesma região: **Vila Aurora**, **Jardim Horizonte** e **Parque das Águas**.

Problema: os moradores avisam sobre poste apagado, calçada sem rampa, lixo e brinquedo quebrado em lugares diferentes (grupo de mensagens, recado, conversa). Ninguém sabe quantos pedidos existem, quais estão parados nem há quanto tempo.

Quem se beneficia: moradores e a associação do bairro, que passam a ver todos os pedidos em um lugar, com a situação de cada um.

Todos os dados são inventados. O sistema não se liga à prefeitura e não promete atendimento.

## Como executar

Precisa só do Python 3 (nenhuma biblioteca para instalar). Na pasta do projeto:

```
python src/sistema.py
```

## Dados

`data/ocorrencias.csv`, separado por ponto e vírgula, uma ocorrência por linha:

| Campo | Obrigatório | Exemplo |
|-------|-------------|---------|
| id | sim, único | OC014 |
| bairro | sim | Vila Aurora |
| categoria | sim | iluminacao, acessibilidade, limpeza ou conservacao |
| descricao | sim | Poste apagado há várias noites |
| local | sim, genérico | Praça Central |
| dia_abertura | sim, de 1 a 30 | 2 |
| situacao | sim | aberta, em_analise ou concluida |

`data/historico.csv` guarda as alterações de situação: `id;dia;de;para`. São 10 eventos.

Significado das situações:

- **aberta**: registrada, ninguém examinou ainda. Fica na fila.
- **em_analise**: alguém já examinou e o pedido está sendo acompanhado.
- **concluida**: o problema foi resolvido.

O tempo é simulado em dias de 1 a 30. O dia 30 é o "hoje" do painel.

O arquivo tem 14 linhas. Duas estão erradas de propósito: a OC013 não tem categoria e a OC014 tem a situação "resolvido", que não existe. O sistema recusa as duas na leitura, mostra o motivo na opção 10 e segue com as 12 válidas.

## Estruturas de dados

| Estrutura | Variável | Para que serve | Por que essa |
|-----------|----------|----------------|--------------|
| Lista | `ocorrencias` | guarda todas as ocorrências válidas | mantém a ordem de registro e é fácil de percorrer com `for` nas listagens e nos filtros |
| Dicionário | `indice` | acha uma ocorrência pelo código | vai direto ao registro, sem percorrer a lista inteira |
| Fila | `fila` | códigos das ocorrências abertas | a primeira registrada é a primeira examinada (entra no fim, sai do começo) |
| Pilha | `pilha` | alterações de situação | a última alteração fica no topo, que é a que se quer ver primeiro |
| Hierarquia | `arvore` | bairro → categoria → códigos | mostra onde cada tipo de problema se concentra |
| Matriz | `montar_matriz()` | linhas = categorias, colunas = situações | um cruzamento só dá os totais por linha e por coluna |

A lista e o dicionário apontam para os mesmos registros: mudar a situação por um aparece no outro.

## Regras lógicas

**Cadastro e leitura do arquivo** (`validar_ocorrencia`): o registro só entra se tiver código único, categoria conhecida, situação conhecida, bairro, local e descrição preenchidos, dia entre 1 e 30 e nenhum texto com cara de dado pessoal.

Expressão booleana da categoria:

```python
not oc['categoria'] or oc['categoria'] not in CATEGORIAS
```

Ela é verdadeira (registro recusado) em dois casos: a categoria veio vazia (`not ''` é `True`) ou veio preenchida com um valor fora da lista. É o que recusa a OC013.

**Privacidade** (`parece_dado_pessoal`): `'@' in texto or digitos >= 8`. Um e-mail ou um número longo (telefone, CPF) faz o cadastro ser recusado.

**Consulta** (`filtrar`):

```python
(categoria == '' or oc['categoria'] == categoria) and (situacao == '' or oc['situacao'] == situacao)
```

Cada parêntese deixa passar tudo quando o filtro está em "Todas" (`''`). O `and` exige que a ocorrência passe nos dois.

**Atualização** (`atualizar_situacao`): se o código não existe, avisa e não muda nada. Se a mudança não é permitida pela regra de andamento (`pode_mudar_situacao`), avisa qual mudança foi recusada. Se passou, troca a situação e empilha o evento no histórico.

Regra de andamento: a ocorrência só anda para frente, um passo por vez. **Aberta** só pode ir para **Em análise**, e **Em análise** só pode ir para **Concluída**. Concluída é final: não reabre, porque um pedido não deve ser dado como resolvido sem ter passado por análise. Se o problema voltar, o certo é registrar uma ocorrência nova.

**Fila** (`mudar_situacao`): `oc['id'] in fila and nova != 'aberta'` tira da fila quem deixou de estar aberta.

## Indicadores

Opção 9 do menu. Com os dados iniciais:

| Indicador | Regra | Resultado |
|-----------|-------|-----------|
| Total por categoria | soma da linha da matriz | Iluminação 4, Acessibilidade 3, Limpeza 3, Conservação 2 |
| Proporção por categoria | quantidade / total * 100 | 33,3%, 25,0%, 25,0%, 16,7% |
| Total por situação | soma da coluna da matriz | Aberta 5, Em análise 4, Concluída 3 |
| Pendências | situação diferente de concluída | 9 de 12 (75%) |
| Atrasadas | pendente há mais de 15 dias | 5 |
| Tempo médio até a conclusão | soma(dia da conclusão - dia da abertura) / concluídas | (5 + 7 + 12) / 3 = 8,0 dias |

O que os números sugerem: iluminação é o pedido mais comum e três de cada quatro pedidos ainda esperam solução. Os pedidos mais antigos sem conclusão são de acessibilidade e iluminação. Como os dados são inventados, isso serve para mostrar o painel funcionando, não para tirar conclusão sobre um bairro real.

## Exemplo de uso

Cadastro (opção 2):

```
Bairro: vila aurora
Número da opção: 1
Descrição breve: Luz queimada na viela
Local genérico: Viela do Sol
Dia da abertura (1 a 30): 28

Ocorrência OC015 cadastrada como Aberta e colocada no fim da fila.
```

Consulta (opção 4, Iluminação + Aberta):

```
Código  Categoria       Bairro            Local                     Dia  Situação
OC009   Iluminação      Vila Aurora       Rua da Escola              15  Aberta
OC012   Iluminação      Parque das Águas  Rua das Palmeiras          24  Aberta
Total: 2 ocorrência(s).
```

Alteração de situação (opção 6, próxima da fila):

```
Na fila, por ordem de registro: OC006, OC008, OC009, OC011, OC012
Próxima: OC006 - Acessibilidade - Piso tátil danificado (Ponto de ônibus da praça)
Colocar esta ocorrência em análise? (s/n): s
Dia da alteração (8 a 30): 20
OC006 agora está Em análise. Restam 4 na fila.
```

Entrada inválida:

```
Código (exemplo: 14 ou OC014): 99
Ocorrência OC099 não encontrada.
```

## Acessibilidade, inclusão e privacidade

- Tudo é texto simples, sem cor e sem desenho, então funciona com leitor de tela.
- As escolhas são por número, o que evita erro de digitação e de acento.
- A situação aparece escrita por extenso ("Em análise"), nunca só por símbolo.
- As mensagens de erro dizem o que aconteceu e o que digitar.
- O local é genérico (praça, rua), sem número de casa.
- O sistema não pede nome de quem registra e recusa texto com e-mail ou número longo.

## Vídeo

https://youtu.be/PmSyZj9s6i0 (não listado)

## Conclusões, limitações e aprendizados

- O que foi cadastrado durante o uso fica só na memória: ao fechar o programa, volta ao conteúdo dos arquivos CSV.
- Os dias são números de 1 a 30, não datas reais.
- A checagem de dado pessoal é simples e pode deixar passar um nome escrito na descrição.
- O painel não fala com nenhum órgão público. Ele organiza os pedidos, não resolve.
- Aprendizados: PREENCHER.

O uso de IA neste trabalho está descrito em `docs/uso_ia.md`.
